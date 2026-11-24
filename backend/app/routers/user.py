from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import PortfolioHolding, PaperAccountConfig, PaperTrade, PortfolioSnapshot
from app.services.firebase_service import FirebaseService
from app.services.portfolio_tracker import PortfolioTracker

router = APIRouter(prefix="/api/user", tags=["User & Firebase"])


class UserSyncPayload(BaseModel):
    uid: str
    email: Optional[str] = None
    displayName: Optional[str] = None
    portfolio: Optional[Dict[str, Any]] = None
    mm_config: Optional[Dict[str, Any]] = None
    trades: Optional[List[Dict[str, Any]]] = None
    watchlist: Optional[List[str]] = None


class WatchlistPayload(BaseModel):
    uid: str
    watchlist: List[str]


def _parse_dt(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val.strip():
        s = val.strip()
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s[:19], fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.utcnow()


@router.get("/status")
def get_firebase_status():
    available = FirebaseService.is_available()
    return {
        "firebase_admin_connected": available,
        "collection": "buffet_users",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/sync")
def sync_user_data(payload: UserSyncPayload, authorization: Optional[str] = Header(None)):
    uid = payload.uid
    if not uid:
        raise HTTPException(status_code=400, detail="Brak identyfikatora UID użytkownika")

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        verified = FirebaseService.verify_token(token)
        if verified and verified.get("uid") != uid:
            raise HTTPException(status_code=403, detail="Identyfikator UID nie zgadza się z tokenem")

    data = {
        "uid": uid,
        "email": payload.email,
        "displayName": payload.displayName,
        "portfolio": payload.portfolio,
        "mm_config": payload.mm_config,
        "trades": payload.trades,
        "watchlist": payload.watchlist,
        "updatedAtServer": datetime.utcnow().isoformat()
    }

    saved = FirebaseService.save_user_data(uid, data)
    return {
        "success": True,
        "saved_to_firestore": saved,
        "uid": uid,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/restore")
def restore_user_data_to_local(payload: UserSyncPayload, db: Session = Depends(get_db)):
    """
    Odtwarza stan portfela Paper Trading, konfiguracji Money Management oraz historii zleceń
    pobrany z Google Cloud Firestore do lokalnej bazy SQLite.
    """
    if not payload.uid:
        raise HTTPException(status_code=400, detail="Brak identyfikatora UID użytkownika")

    portfolio = payload.portfolio or {}
    holdings_in = portfolio.get("holdings") or []
    mm_in = payload.mm_config or {}
    trades_in = payload.trades or []

    # 1. Konfiguracja konta i MM
    acc = PortfolioTracker.get_or_create_account(db)
    initial_cap = float(
        mm_in.get("initial_capital")
        or portfolio.get("initial_capital")
        or acc.initial_capital
        or 100000.0
    )
    acc.initial_capital = initial_cap
    if "default_position_pct" in mm_in:
        acc.default_position_pct = float(mm_in["default_position_pct"])
    if "max_position_pct" in mm_in:
        acc.max_position_pct = float(mm_in["max_position_pct"])
    if "max_positions" in mm_in:
        acc.max_positions = int(mm_in["max_positions"])
    if "min_cash_reserve_pct" in mm_in:
        acc.min_cash_reserve_pct = float(mm_in["min_cash_reserve_pct"])
    if "default_stop_loss_pct" in mm_in:
        acc.default_stop_loss_pct = float(mm_in["default_stop_loss_pct"])
    if "default_take_profit_pct" in mm_in:
        acc.default_take_profit_pct = float(mm_in["default_take_profit_pct"])
    if "commission_pct" in mm_in:
        acc.commission_pct = float(mm_in["commission_pct"])
    if "allow_fractional_shares" in mm_in:
        acc.allow_fractional_shares = bool(mm_in["allow_fractional_shares"])

    # 2. Odtwórz pozycje portfela (holdings)
    db.query(PortfolioHolding).delete()
    db.query(PortfolioSnapshot).delete()

    total_invested_calc = 0.0
    restored_count = 0
    for h in holdings_in:
        ticker = (h.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        shares = float(h.get("shares") or 0.0)
        entry_price = float(h.get("entry_price") or 0.0)
        current_price = float(h.get("current_price") or entry_price)
        intrinsic_value = float(h.get("intrinsic_value") or current_price)
        target_price = float(h.get("target_price") or intrinsic_value)
        total_invested_calc += shares * entry_price

        holding = PortfolioHolding(
            ticker=ticker,
            company_name=h.get("company_name") or ticker,
            shares=shares,
            entry_date=_parse_dt(h.get("entry_date")),
            entry_price=entry_price,
            current_price=current_price,
            target_price=target_price,
            intrinsic_value=intrinsic_value,
            pnl_pct=float(h.get("pnl_pct") or 0.0),
            pnl_cash=float(h.get("pnl_cash") or 0.0),
            weight_pct=float(h.get("weight_pct") or 0.0),
            benchmark_sp500_entry=float(h.get("benchmark_sp500_entry") or 5800.0),
            benchmark_sp500_current=float(h.get("benchmark_sp500_current") or 5800.0),
            benchmark_pnl_pct=float(h.get("benchmark_pnl_pct") or 0.0),
            stop_loss_price=float(h["stop_loss_price"]) if h.get("stop_loss_price") is not None else None,
            take_profit_price=float(h["take_profit_price"]) if h.get("take_profit_price") is not None else None,
            status=h.get("status") or "ACTIVE",
        )
        db.add(holding)
        restored_count += 1

    # 3. Wylicz lub odtwórz saldo gotówki i zrealizowany P&L
    realized_pnl = float(portfolio.get("realized_pnl_cash") or 0.0)
    acc.realized_pnl = realized_pnl
    if portfolio.get("cash_balance") is not None:
        acc.cash_balance = round(float(portfolio["cash_balance"]), 2)
    else:
        acc.cash_balance = round(max(initial_cap + realized_pnl - total_invested_calc, 0.0), 2)
    acc.updated_at = datetime.utcnow()

    # 4. Odtwórz historię zleceń (trades)
    if trades_in:
        db.query(PaperTrade).delete()
        for t in trades_in:
            if not t.get("ticker"):
                continue
            db.add(PaperTrade(
                ticker=str(t["ticker"]).upper(),
                company_name=t.get("company_name") or str(t["ticker"]).upper(),
                side=t.get("side") or "BUY",
                shares=float(t.get("shares") or 0.0),
                price=float(t.get("price") or 0.0),
                gross_value=float(t.get("gross_value") or 0.0),
                commission=float(t.get("commission") or 0.0),
                realized_pnl=float(t["realized_pnl"]) if t.get("realized_pnl") is not None else None,
                realized_pnl_pct=float(t["realized_pnl_pct"]) if t.get("realized_pnl_pct") is not None else None,
                note=t.get("note") or "",
                executed_at=_parse_dt(t.get("executed_at")),
            ))

    db.commit()

    # 5. Odśwież kursy rynkowe i zwróć pełne podsumowanie portfela
    summary = PortfolioTracker.get_portfolio_summary(db, force_refresh=True)
    return {
        "success": True,
        "restored_holdings": restored_count,
        "summary": summary,
    }


@router.post("/load/{uid}")
def load_and_restore_from_firestore(uid: str, db: Session = Depends(get_db)):
    """
    Pobiera dane użytkownika bezpośrednio z Firestore (przez Admin SDK)
    i odtwarza je do lokalnej bazy SQLite w jednym kroku.
    """
    if not uid:
        raise HTTPException(status_code=400, detail="Brak UID")

    cloud_data = FirebaseService.load_user_data(uid)
    if not cloud_data or not cloud_data.get("portfolio"):
        return {"found": False, "uid": uid, "summary": None}

    payload = UserSyncPayload(
        uid=uid,
        email=cloud_data.get("email"),
        displayName=cloud_data.get("displayName"),
        portfolio=cloud_data.get("portfolio"),
        mm_config=cloud_data.get("mm_config"),
        trades=cloud_data.get("trades"),
        watchlist=cloud_data.get("watchlist"),
    )
    restored = restore_user_data_to_local(payload, db)
    return {
        "found": True,
        "uid": uid,
        "restored_holdings": restored["restored_holdings"],
        "summary": restored["summary"],
    }


@router.get("/sync/{uid}")
def load_user_data(uid: str):
    if not uid:
        raise HTTPException(status_code=400, detail="Brak UID")

    data = FirebaseService.load_user_data(uid)
    if not data:
        return {"found": False, "uid": uid, "data": None}

    return {"found": True, "uid": uid, "data": data}


@router.post("/watchlist")
def update_user_watchlist(payload: WatchlistPayload):
    saved = FirebaseService.save_user_data(payload.uid, {"watchlist": payload.watchlist})
    return {"success": saved, "watchlist": payload.watchlist}
