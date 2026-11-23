from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import Signal
from app.services.portfolio_tracker import PortfolioTracker

router = APIRouter(prefix="/api/portfolio", tags=["Paper Trading & MM"])


class MMSettingsPayload(BaseModel):
    initial_capital: Optional[float] = None
    default_position_pct: Optional[float] = None
    max_position_pct: Optional[float] = None
    max_positions: Optional[int] = None
    min_cash_reserve_pct: Optional[float] = None
    default_stop_loss_pct: Optional[float] = None
    default_take_profit_pct: Optional[float] = None
    commission_pct: Optional[float] = None
    allow_fractional_shares: Optional[bool] = None


class BuyOrderPayload(BaseModel):
    ticker: str
    amount_usd: Optional[float] = None
    shares: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    provider_name: Optional[str] = None
    note: str = ""


class SellOrderPayload(BaseModel):
    shares: Optional[float] = None
    note: str = ""


class ResetAccountPayload(BaseModel):
    initial_capital: Optional[float] = None


@router.get("")
def get_portfolio_overview(
    force_refresh: bool = Query(False, description="Wymuś odświeżenie kursów rynkowych"),
    db: Session = Depends(get_db),
):
    return PortfolioTracker.get_portfolio_summary(db, force_refresh=force_refresh)


@router.post("/refresh")
def refresh_portfolio_prices(db: Session = Depends(get_db)):
    return PortfolioTracker.get_portfolio_summary(db, force_refresh=True)


@router.get("/mm")
def get_mm_settings(db: Session = Depends(get_db)):
    summary = PortfolioTracker.get_portfolio_summary(db, force_refresh=False)
    return {
        "mm_config": summary["mm_config"],
        "cash_balance": summary["cash_balance"],
        "total_portfolio_value": summary["total_portfolio_value"],
        "positions_count": summary["positions_count"],
    }


@router.post("/mm")
def update_mm_settings(payload: MMSettingsPayload, db: Session = Depends(get_db)):
    PortfolioTracker.update_mm_settings(db, payload.model_dump(exclude_none=True))
    return PortfolioTracker.get_portfolio_summary(db, force_refresh=False)


@router.post("/buy")
def execute_buy_order(payload: BuyOrderPayload, db: Session = Depends(get_db)):
    try:
        res = PortfolioTracker.buy_position(
            db=db,
            ticker=payload.ticker,
            amount_usd=payload.amount_usd,
            shares=payload.shares,
            stop_loss_pct=payload.stop_loss_pct,
            take_profit_pct=payload.take_profit_pct,
            provider_name=payload.provider_name,
            note=payload.note,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sell/{holding_id}")
def execute_sell_order(
    holding_id: int,
    payload: Optional[SellOrderPayload] = None,
    db: Session = Depends(get_db),
):
    try:
        return PortfolioTracker.sell_position(
            db=db,
            holding_id=holding_id,
            shares=payload.shares if payload else None,
            note=payload.note if payload else "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
def reset_paper_account(
    payload: Optional[ResetAccountPayload] = None,
    db: Session = Depends(get_db),
):
    cap = payload.initial_capital if payload else None
    PortfolioTracker.reset_account(db, initial_capital=cap)
    return PortfolioTracker.get_portfolio_summary(db, force_refresh=False)


@router.post("/reseed")
def reseed_real_portfolio(db: Session = Depends(get_db)):
    PortfolioTracker.seed_initial_demo_portfolio(db, force=True)
    return PortfolioTracker.get_portfolio_summary(db, force_refresh=True)


@router.get("/signals")
def get_signals_log(db: Session = Depends(get_db)):
    signals = db.query(Signal).order_by(Signal.created_at.desc()).all()
    return {"signals": signals}


@router.delete("/{holding_id}")
def remove_holding(holding_id: int, db: Session = Depends(get_db)):
    """Zamyka pozycję przez realną sprzedaż (zwraca gotówkę i księguje zrealizowany P&L)."""
    try:
        return PortfolioTracker.sell_position(db=db, holding_id=holding_id, note="Zamknięcie pozycji z tabeli portfela")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
