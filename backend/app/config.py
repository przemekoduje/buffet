import os
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)


class Settings:
    PROJECT_NAME: str = "Buffet - Value Investing & AI Screener"
    PROJECT_MOTTO: str = "Reguła nr 1: Nigdy nie trać pieniędzy. Reguła nr 2: Nigdy nie zapominaj o regule nr 1."
    VERSION: str = "2.0.0"
    DATA_PROVIDER: str = os.getenv("DATA_PROVIDER", "yfinance")  # 'yfinance', 'fmp', 'mock'
    FMP_API_KEY: str = os.getenv("FMP_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/buffet.db")
    ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "buffet-admin-2026")

    def persist_env(self, updates: Dict[str, str]) -> None:
        """Zapisuje zaktualizowane zmienne środowiskowe do pliku backend/.env."""
        existing: Dict[str, str] = {}
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                k, v = stripped.split("=", 1)
                existing[k.strip()] = v.strip()

        for k, v in updates.items():
            if v is not None:
                existing[k] = v

        lines = [f"{k}={v}" for k, v in existing.items()]
        ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


settings = Settings()
