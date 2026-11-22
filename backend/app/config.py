import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Buffet - Value Investing & AI Screener"
    PROJECT_MOTTO: str = "Reguła nr 1: Nigdy nie trać pieniędzy. Reguła nr 2: Nigdy nie zapominaj o regule nr 1."
    VERSION: str = "1.0.0"
    DATA_PROVIDER: str = os.getenv("DATA_PROVIDER", "mock")  # 'mock', 'yfinance', 'fmp'
    FMP_API_KEY: str = os.getenv("FMP_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/buffet.db")
    ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "buffet-admin-2026")

settings = Settings()
