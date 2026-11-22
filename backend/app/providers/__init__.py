from app.config import settings
from app.providers.base import BaseMarketDataProvider
from app.providers.mock_provider import MockDataProvider
from app.providers.yfinance_provider import YFinanceDataProvider
from app.providers.fmp_provider import FMPDataProvider

def get_market_provider(provider_name: str = None) -> BaseMarketDataProvider:
    name = provider_name or settings.DATA_PROVIDER
    if name == "yfinance":
        return YFinanceDataProvider()
    elif name == "fmp":
        return FMPDataProvider()
    else:
        return MockDataProvider()
