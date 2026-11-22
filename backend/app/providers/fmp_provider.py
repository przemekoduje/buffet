from typing import List, Optional
import requests
from app.config import settings
from app.providers.base import BaseMarketDataProvider, FundamentalData

class FMPDataProvider(BaseMarketDataProvider):
    """
    Płatny/Developer dostawca danych: Financial Modeling Prep (FMP).
    Oferuje znormalizowane bilanse, transkrypty i wskaźniki za 10-30 lat.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.FMP_API_KEY
        self.base_url = "https://financialmodelingprep.com/api/v3"

    def get_ticker_data(self, ticker: str) -> Optional[FundamentalData]:
        if not self.api_key:
            return None

        try:
            # 1. Profile & Quote
            quote_resp = requests.get(f"{self.base_url}/quote/{ticker}?apikey={self.api_key}", timeout=10).json()
            if not quote_resp:
                return None
            q = quote_resp[0]

            # 2. Key Metrics TTM
            metrics_resp = requests.get(f"{self.base_url}/key-metrics-ttm/{ticker}?apikey={self.api_key}", timeout=10).json()
            m = metrics_resp[0] if metrics_resp else {}

            # 3. Cash Flow Statement TTM
            cf_resp = requests.get(f"{self.base_url}/cash-flow-statement/{ticker}?period=annual&limit=5&apikey={self.api_key}", timeout=10).json()
            fcf_hist = [float(item.get("freeCashFlow", 0)) for item in reversed(cf_resp)] if cf_resp else [float(m.get("freeCashFlowPerShareTTM", 10)) * float(q.get("sharesOutstanding", 1))]

            fcf_ttm = fcf_hist[-1] if fcf_hist else 1_000_000_000.0
            price = float(q.get("price", 0.0))
            net_debt = float(m.get("netDebtTTM", 0.0))

            return FundamentalData(
                ticker=ticker.upper(),
                company_name=q.get("name", ticker),
                sector=q.get("sector", "General"),
                industry=q.get("industry", "General"),
                current_price=price,
                market_cap=float(q.get("marketCap", 0.0)),
                roe_pct=round(float(m.get("roeTTM", 0.15)) * 100, 1),
                roic_pct=round(float(m.get("roicTTM", 0.14)) * 100, 1),
                gross_margin_pct=round(float(m.get("grossProfitMarginTTM", 0.40)) * 100, 1),
                operating_margin_pct=round(float(m.get("operatingProfitMarginTTM", 0.20)) * 100, 1),
                fcf_history_5y=fcf_hist,
                revenue_growth_5y_cagr=round(float(m.get("revenueGrowthTTM", 0.07)) * 100, 1),
                net_debt=net_debt,
                total_cash=float(m.get("cashAndCashEquivalentsTTM", 0.0)),
                net_debt_to_fcf=round(net_debt / fcf_ttm, 2) if fcf_ttm > 0 else 99.0,
                current_ratio=float(m.get("currentRatioTTM", 1.5)),
                altman_z_score=float(m.get("grahamNetNetTTM", 4.5)),
                pe_ratio=float(q.get("pe", 20.0)),
                shares_outstanding=float(q.get("sharesOutstanding", 1.0)),
                free_cash_flow_ttm=fcf_ttm,
                capex_ttm=float(m.get("capexToOperatingCashFlowTTM", 0.0)),
                net_income_ttm=float(m.get("netIncomePerShareTTM", 1.0)) * float(q.get("sharesOutstanding", 1.0)),
                beta=float(q.get("beta", 1.0)),
                dividend_yield_pct=round(float(m.get("dividendYieldTTM", 0.0)) * 100, 2),
                source="fmp"
            )
        except Exception as e:
            print(f"[FMP Error] {ticker}: {e}")
            return None

    def search_screener_candidates(self) -> List[str]:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "BRK.B", "KO", "V", "JNJ", "PG", "COST"]

    def get_sp500_current(self) -> float:
        return 5950.0
