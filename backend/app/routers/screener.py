from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database.db import SessionLocal, get_db
from app.database.models import MarketAlert, PortfolioHolding
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator
from app.services.market_scanner import MarketScanner

router = APIRouter(prefix="/api/screener", tags=["Screener"])


@router.get("")
def get_screener_results(
    basket: str = Query("all", description="all, us_quality, sp500_value, dividend_aristocrats"),
    min_score: int = Query(0, description="Minimalny Buffett Score"),
    undervalued_only: bool = Query(False, description="Tylko z dodatnim marginesem bezpieczeństwa"),
    buffett_picks_only: bool = Query(False, description="Tylko spółki wybrane wg planu Buffetta (BUY/STRONG_BUY)"),
    provider_name: Optional[str] = Query(None, description="yfinance, fmp, mock"),
    db: Session = Depends(get_db),
):
    return MarketScanner.get_screener_payload(
        db=db,
        basket=basket,
        min_score=min_score,
        undervalued_only=undervalued_only,
        buffett_picks_only=buffett_picks_only,
        provider_name=provider_name,
    )


def _run_eod_bg(provider_name: Optional[str]):
    db = SessionLocal()
    try:
        MarketScanner.run_market_scan(
            db=db,
            provider_name=provider_name,
            scan_type="MANUAL",
            bypass_cache=True,
        )
    finally:
        db.close()


@router.post("/run-eod")
def trigger_eod_scan(
    background_tasks: BackgroundTasks,
    provider_name: Optional[str] = Query(None),
    sync: bool = Query(False, description="Czy czekać na zakończenie skanu synchronicznie"),
    db: Session = Depends(get_db),
):
    if MarketScanner._scan_in_progress:
        return {"status": "ALREADY_RUNNING", "message": "Skanowanie rynku już trwa w tle."}

    if sync:
        return MarketScanner.run_market_scan(
            db=db,
            provider_name=provider_name,
            scan_type="MANUAL",
            bypass_cache=True,
        )

    background_tasks.add_task(_run_eod_bg, provider_name)
    return {
        "status": "STARTED",
        "message": "Rozpoczęto pełny skan koszyków rynkowych (US Quality, S&P 500 Value, Dywidendowi Arystokraci).",
    }


@router.get("/alerts")
def get_intraday_alerts(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return {
        "market_session": MarketScanner.get_market_session_info(),
        "alerts": MarketScanner.get_recent_alerts(db, limit=limit),
    }


@router.post("/alerts/check")
def run_intraday_alert_check(db: Session = Depends(get_db)):
    alerts = MarketScanner.check_intraday_alerts(db)
    return {
        "status": "OK",
        "market_session": MarketScanner.get_market_session_info(),
        "alerts": alerts,
    }


@router.post("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(MarketAlert).filter(MarketAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Nie znaleziono alertu")
    alert.is_read = True
    db.commit()
    return {"status": "OK"}


@router.get("/scan/{ticker}")
def scan_single_ticker(
    ticker: str,
    provider_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    provider = get_market_provider(provider_name)
    fund_data = provider.get_ticker_data(ticker)
    if not fund_data:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono danych dla symbolu {ticker.upper()}")

    eval_res = BuffettCalculator.evaluate(fund_data)
    in_paper = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.ticker == fund_data.ticker)
        .first()
        is not None
    )
    return {
        "ticker": fund_data.ticker,
        "company_name": fund_data.company_name,
        "sector": fund_data.sector,
        "current_price": fund_data.current_price,
        "intrinsic_value": eval_res["intrinsic_value"],
        "margin_of_safety_pct": eval_res["margin_of_safety_pct"],
        "buffett_score": eval_res["buffett_score"],
        "recommendation": eval_res["recommendation"],
        "in_paper_trading": in_paper,
        "details": eval_res,
    }
