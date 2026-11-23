from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class FundamentalData(BaseModel):
    ticker: str
    company_name: str
    sector: str
    industry: str
    current_price: float
    market_cap: float

    # Rentowność & Fosa
    roe_pct: float              # Zwrot z kapitału własnego
    roic_pct: float             # Zwrot z zainwestowanego kapitału
    gross_margin_pct: float     # Marża brutto (pricing power)
    operating_margin_pct: float
    fcf_history_5y: List[float] # Free cash flow za ostatnie lata (chronologicznie)
    revenue_growth_5y_cagr: float

    # Bezpieczeństwo i Zadłużenie (Reguła nr 1)
    net_debt: float
    total_cash: float
    net_debt_to_fcf: float
    current_ratio: float
    altman_z_score: Optional[float] = None

    # Wycena
    pe_ratio: float
    shares_outstanding: float
    free_cash_flow_ttm: float
    capex_ttm: float
    net_income_ttm: float
    beta: float = 1.0
    dividend_yield_pct: float = 0.0

    # Źródło danych
    source: str = "base"


class BaseMarketDataProvider(ABC):
    """Uniwersalny interfejs dostawcy danych rynkowych."""

    @abstractmethod
    def get_ticker_data(self, ticker: str) -> Optional[FundamentalData]:
        """Pobiera kompletne dane fundamentalne dla spółki."""
        pass

    @abstractmethod
    def search_screener_candidates(self) -> List[str]:
        """Zwraca listę tickerów do przeskanowania (np. S&P500 / wybrane spółki value)."""
        pass

    @abstractmethod
    def get_sp500_current(self) -> float:
        """Pobiera aktualny poziom indeksu S&P 500 jako benchmark."""
        pass

    def get_historical_prices(self, tickers: List[str], days: int = 95) -> Dict[str, List[Dict[str, Any]]]:
        """Pobiera historyczne ceny zamknięcia (domyślnie puste, implementowane przez realnych dostawców)."""
        return {}

    def get_ticker_news(self, ticker: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Pobiera ostatnie newsy rynkowe dla spółki (domyślnie puste)."""
        return []
