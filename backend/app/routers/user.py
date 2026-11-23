from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.services.firebase_service import FirebaseService

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

    # Weryfikacja tokenu jeśli przesłano nagłówek Authorization
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
