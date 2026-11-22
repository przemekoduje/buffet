from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database.db import get_db
from app.database.models import Signal, PortfolioHolding
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator
from app.services.ai_analyzer import AIAnalyzer

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

@router.get("/{ticker}")
async def get_deep_analysis(ticker: str, provider_name: Optional[str] = None):
    provider = get_market_provider(provider_name)
    fund_data = provider.get_ticker_data(ticker)
    if not fund_data:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono spółki {ticker.upper()}")

    eval_res = BuffettCalculator.evaluate(fund_data)
    ai_memo = await AIAnalyzer.analyze_company(fund_data, eval_res)

    return {
        "fundamental": fund_data,
        "valuation": eval_res,
        "ai_memo": ai_memo,
        "buffett_principles": [
            {
                "rule": "1. Trwała fosa ekonomiczna (Moat)",
                "satisfied": fund_data.gross_margin_pct >= 40 and fund_data.roic_pct >= 12,
                "detail": f"Marża brutto {fund_data.gross_margin_pct}%, ROIC {fund_data.roic_pct}%"
            },
            {
                "rule": "2. Bezpieczny bilans (Reguła 1: Nie trać)",
                "satisfied": fund_data.net_debt_to_fcf <= 3.0,
                "detail": f"Dług netto spłacany w {fund_data.net_debt_to_fcf} lat FCF"
            },
            {
                "rule": "3. Uczciwy i kompetentny zarząd",
                "satisfied": fund_data.roe_pct >= 15,
                "detail": f"Wysoki zwrot z kapitału własnego ROE {fund_data.roe_pct}%"
            },
            {
                "rule": "4. Margines Bezpieczeństwa (>15%)",
                "satisfied": eval_res["margin_of_safety_pct"] >= 15,
                "detail": f"Margines: {eval_res['margin_of_safety_pct']}% względem wyceny ${eval_res['intrinsic_value']}"
            }
        ]
    }

@router.post("/{ticker}/add-to-demo")
async def add_to_demo_portfolio(ticker: str, db: Session = Depends(get_db)):
    # Sprawdź czy już istnieje
    existing = db.query(PortfolioHolding).filter(PortfolioHolding.ticker == ticker.upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Spółka znajduje się już w portfelu demonstracyjnym")

    provider = get_market_provider()
    fund_data = provider.get_ticker_data(ticker)
    if not fund_data:
        raise HTTPException(status_code=404, detail="Brak danych dla symbolu")

    eval_res = BuffettCalculator.evaluate(fund_data)
    ai_memo = await AIAnalyzer.analyze_company(fund_data, eval_res)
    sp500_level = provider.get_sp500_current()

    new_holding = PortfolioHolding(
        ticker=fund_data.ticker,
        company_name=fund_data.company_name,
        shares=10.0,
        entry_price=fund_data.current_price,
        current_price=fund_data.current_price,
        target_price=eval_res["intrinsic_value"],
        intrinsic_value=eval_res["intrinsic_value"],
        pnl_pct=0.0,
        pnl_cash=0.0,
        weight_pct=15.0,
        benchmark_sp500_entry=sp500_level,
        benchmark_sp500_current=sp500_level,
        benchmark_pnl_pct=0.0,
        status="ACTIVE"
    )
    db.add(new_holding)

    # Rejestrujemy także audytowany sygnał
    new_signal = Signal(
        ticker=fund_data.ticker,
        company_name=fund_data.company_name,
        sector=fund_data.sector,
        entry_price=fund_data.current_price,
        intrinsic_value=eval_res["intrinsic_value"],
        margin_of_safety_pct=eval_res["margin_of_safety_pct"],
        recommendation=eval_res["recommendation"],
        buffett_score=eval_res["buffett_score"],
        rule_number_one_risk=eval_res["rule_number_one_risk"],
        roic_pct=fund_data.roic_pct,
        roe_pct=fund_data.roe_pct,
        gross_margin_pct=fund_data.gross_margin_pct,
        net_debt_to_fcf=fund_data.net_debt_to_fcf,
        pe_ratio=fund_data.pe_ratio,
        owner_earnings_yield_pct=round((eval_res["owner_earnings_ttm"] * 1e6 / fund_data.market_cap) * 100, 2),
        ai_thesis=ai_memo.get("thesis"),
        ai_moat_analysis=ai_memo.get("moat"),
        ai_risks=ai_memo.get("rule_1_risks")
    )
    db.add(new_signal)
    db.commit()

    return {"status": "SUCCESS", "message": f"Spółka {fund_data.ticker} dodana do 1-rocznego portfela audytowego"}
