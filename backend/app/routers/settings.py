from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class UpdateSettingsPayload(BaseModel):
    data_provider: Optional[str] = None
    fmp_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

@router.get("")
def get_current_settings():
    return {
        "project_name": settings.PROJECT_NAME,
        "motto": settings.PROJECT_MOTTO,
        "version": settings.VERSION,
        "active_data_provider": settings.DATA_PROVIDER,
        "has_fmp_key": bool(settings.FMP_API_KEY),
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "available_providers": [
            {
                "id": "mock",
                "name": "Wbudowane dane demonstracyjne (Mock)",
                "cost": "0 zł",
                "desc": "Błyskawiczne, zweryfikowane dane fundamentalne 10 spółek w stylu Buffetta"
            },
            {
                "id": "yfinance",
                "name": "Yahoo Finance (Free/Open API)",
                "cost": "0 zł",
                "desc": "Darmowe dane dla dowolnego tickera z giełd światowych (S&P500, GPW)"
            },
            {
                "id": "fmp",
                "name": "Financial Modeling Prep (FMP)",
                "cost": "~$19-29 / mc",
                "desc": "Znormalizowane sprawozdania finansowe za 30 lat, transkrypty z zarządem"
            }
        ]
    }

@router.post("")
def update_settings(payload: UpdateSettingsPayload):
    if payload.data_provider:
        settings.DATA_PROVIDER = payload.data_provider
    if payload.fmp_api_key is not None:
        settings.FMP_API_KEY = payload.fmp_api_key
    if payload.gemini_api_key is not None:
        settings.GEMINI_API_KEY = payload.gemini_api_key
    return {"status": "SUCCESS", "active_data_provider": settings.DATA_PROVIDER}
