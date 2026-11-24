from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class UpdateSettingsPayload(BaseModel):
    data_provider: Optional[str] = None
    fmp_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None


@router.get("")
def get_current_settings():
    return {
        "project_name": settings.PROJECT_NAME,
        "motto": settings.PROJECT_MOTTO,
        "version": settings.VERSION,
        "active_data_provider": settings.DATA_PROVIDER,
        "has_fmp_key": bool(settings.FMP_API_KEY),
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "gemini_model": settings.GEMINI_MODEL,
        "ai_engine": f"Gemini ({settings.GEMINI_MODEL})" if settings.GEMINI_API_KEY else "Heurystyka Buffetta (brak klucza Gemini)",
        "available_providers": [
            {
                "id": "yfinance",
                "name": "Yahoo Finance (Realne dane Live)",
                "cost": "0 zł",
                "desc": "Realne kursy, sprawozdania finansowe, historia FCF i indeks S&P 500 dla giełd światowych (US, GPW)",
            },
            {
                "id": "fmp",
                "name": "Financial Modeling Prep (FMP + Auto-Fallback)",
                "cost": "Free 250/dz. / $19+",
                "desc": "Znormalizowane sprawozdania USA (5-30 lat), serwerowy screener tanich spółek i newsy (z płynnym fallbackiem do Yahoo Finance)",
            },
            {
                "id": "mock",
                "name": "Dane demonstracyjne (Offline Mock)",
                "cost": "0 zł",
                "desc": "Tryb awaryjny offline — statyczne dane 10 spółek bez połączenia z giełdą",
            },
        ],
    }


@router.post("")
def update_settings(payload: UpdateSettingsPayload):
    env_updates = {}
    if payload.data_provider:
        settings.DATA_PROVIDER = payload.data_provider
        env_updates["DATA_PROVIDER"] = payload.data_provider
    if payload.fmp_api_key is not None and payload.fmp_api_key.strip() != "":
        settings.FMP_API_KEY = payload.fmp_api_key.strip()
        env_updates["FMP_API_KEY"] = settings.FMP_API_KEY
    if payload.gemini_api_key is not None and payload.gemini_api_key.strip() != "":
        settings.GEMINI_API_KEY = payload.gemini_api_key.strip()
        env_updates["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
    if payload.gemini_model is not None and payload.gemini_model.strip() != "":
        settings.GEMINI_MODEL = payload.gemini_model.strip()
        env_updates["GEMINI_MODEL"] = settings.GEMINI_MODEL

    if env_updates:
        settings.persist_env(env_updates)

    return {
        "status": "SUCCESS",
        "active_data_provider": settings.DATA_PROVIDER,
        "has_fmp_key": bool(settings.FMP_API_KEY),
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "gemini_model": settings.GEMINI_MODEL,
    }


@router.get("/test-fmp")
def test_fmp_connection():
    from app.providers.fmp_provider import FMPDataProvider
    return FMPDataProvider().test_connection()
