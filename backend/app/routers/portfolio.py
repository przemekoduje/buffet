from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import PortfolioHolding, Signal
from app.services.portfolio_tracker import PortfolioTracker

router = APIRouter(prefix="/api/portfolio", tags=["Demo Portfolio"])

@router.get("")
def get_portfolio_overview(db: Session = Depends(get_db)):
    return PortfolioTracker.get_portfolio_summary(db)

@router.get("/signals")
def get_signals_log(db: Session = Depends(get_db)):
    signals = db.query(Signal).order_by(Signal.created_at.desc()).all()
    return {"signals": signals}

@router.delete("/{holding_id}")
def remove_holding(holding_id: int, db: Session = Depends(get_db)):
    holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Pozycja nie znaleziona")
    db.delete(holding)
    db.commit()
    return {"status": "DELETED", "message": f"Usunięto pozycję {holding.ticker}"}
