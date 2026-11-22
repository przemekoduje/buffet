from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.db import get_db
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator

router = APIRouter(prefix="/api/screener", tags=["Screener"])

@router.get("")
def get_screener_results(
    min_score: int = Query(0, description="Minimalny Buffett Score"),
    undervalued_only: bool = Query(False, description="Tylko z dodatnim marginesem bezpieczeństwa"),
    provider_name: Optional[str] = Query(None, description="mock, yfinance, fmp")
):
    provider = get_market_provider(provider_name)
    tickers = provider.search_screener_candidates()
    
    results = []
    for ticker in tickers:
        fund_data = provider.get_ticker_data(ticker)
        if not fund_data:
            continue
        
        eval_res = BuffettCalculator.evaluate(fund_data)
        
        if eval_res["buffett_score"] < min_score:
            continue
        if undervalued_only and eval_res["margin_of_safety_pct"] <= 0:
            continue

        results.append({
            "ticker": fund_data.ticker,
            "company_name": fund_data.company_name,
            "sector": fund_data.sector,
            "industry": fund_data.industry,
            "current_price": fund_data.current_price,
            "intrinsic_value": eval_res["intrinsic_value"],
            "margin_of_safety_pct": eval_res["margin_of_safety_pct"],
            "buffett_score": eval_res["buffett_score"],
            "recommendation": eval_res["recommendation"],
            "rule_number_one_risk": eval_res["rule_number_one_risk"],
            "roic_pct": fund_data.roic_pct,
            "roe_pct": fund_data.roe_pct,
            "gross_margin_pct": fund_data.gross_margin_pct,
            "net_debt_to_fcf": fund_data.net_debt_to_fcf,
            "pe_ratio": fund_data.pe_ratio,
            "source": fund_data.source
        })

    # Sortuj wg najwyższego Buffett Score
    results.sort(key=lambda x: x["buffett_score"], reverse=True)
    return {"total": len(results), "items": results}

@router.get("/scan/{ticker}")
def scan_single_ticker(ticker: str, provider_name: Optional[str] = None):
    provider = get_market_provider(provider_name)
    fund_data = provider.get_ticker_data(ticker)
    if not fund_data:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono danych dla symbolu {ticker.upper()}")
    
    eval_res = BuffettCalculator.evaluate(fund_data)
    return {
        "ticker": fund_data.ticker,
        "company_name": fund_data.company_name,
        "sector": fund_data.sector,
        "current_price": fund_data.current_price,
        "intrinsic_value": eval_res["intrinsic_value"],
        "margin_of_safety_pct": eval_res["margin_of_safety_pct"],
        "buffett_score": eval_res["buffett_score"],
        "recommendation": eval_res["recommendation"],
        "rule_number_one_risk": eval_res["rule_number_one_risk"],
        "details": eval_res
    }
