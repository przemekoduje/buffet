from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database.db import get_db
from app.database.models import Signal, PortfolioHolding
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator
from app.services.ai_analyzer import AIAnalyzer
from app.services.portfolio_tracker import PortfolioTracker

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/{ticker}")
async def get_deep_analysis(
    ticker: str,
    provider_name: Optional[str] = None,
    refresh_ai: bool = Query(False, description="Wymuś ponowne wygenerowanie analizy AI"),
):
    provider = get_market_provider(provider_name)
    fund_data = provider.get_ticker_data(ticker)
    if not fund_data:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono spółki {ticker.upper()}")

    eval_res = BuffettCalculator.evaluate(fund_data)
    news = provider.get_ticker_news(ticker, limit=8)
    ai_memo = await AIAnalyzer.analyze_company(fund_data, eval_res, force_refresh=refresh_ai, news=news)

    return {
        "fundamental": fund_data,
        "valuation": eval_res,
        "ai_memo": ai_memo,
        "news": news,
        "buffett_principles": [
            {
                "rule": "1. Trwała fosa ekonomiczna (Moat)",
                "satisfied": fund_data.gross_margin_pct >= 40 and fund_data.roic_pct >= 12,
                "detail": f"Marża brutto {fund_data.gross_margin_pct}%, ROIC {fund_data.roic_pct}%",
            },
            {
                "rule": "2. Bezpieczny bilans (Reguła 1: Nie trać)",
                "satisfied": fund_data.net_debt_to_fcf <= 3.0,
                "detail": f"Dług netto spłacany w {fund_data.net_debt_to_fcf} lat FCF",
            },
            {
                "rule": "3. Uczciwy i kompetentny zarząd",
                "satisfied": fund_data.roe_pct >= 15,
                "detail": f"Zwrot z kapitału własnego ROE {fund_data.roe_pct}%",
            },
            {
                "rule": "4. Margines Bezpieczeństwa (>15%)",
                "satisfied": eval_res["margin_of_safety_pct"] >= 15,
                "detail": f"Margines: {eval_res['margin_of_safety_pct']}% względem wyceny ${eval_res['intrinsic_value']}",
            },
        ],
    }


@router.post("/{ticker}/add-to-demo")
async def add_to_demo_portfolio(
    ticker: str,
    provider_name: Optional[str] = None,
    amount_usd: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        return PortfolioTracker.buy_position(
            db=db,
            ticker=ticker,
            amount_usd=amount_usd,
            provider_name=provider_name,
            note="Zlecenie z widoku Deep Dive",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
