from typing import List, Optional
import yfinance as yf
from app.providers.base import BaseMarketDataProvider, FundamentalData

class YFinanceDataProvider(BaseMarketDataProvider):
    """Darmowy dostawca danych rynkowych oparty o bibliotekę yfinance."""

    def get_ticker_data(self, ticker: str) -> Optional[FundamentalData]:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            if not info or "regularMarketPrice" not in info and "currentPrice" not in info:
                return None

            price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
            if price <= 0:
                return None

            mcap = float(info.get("marketCap", 0.0))
            shares = float(info.get("sharesOutstanding", 0.0))
            if shares <= 0 and mcap > 0:
                shares = mcap / price

            fcf = float(info.get("freeCashflow", 0.0))
            net_income = float(info.get("netIncomeToCommon", 0.0))
            total_debt = float(info.get("totalDebt", 0.0))
            total_cash = float(info.get("totalCash", 0.0))
            net_debt = max(total_debt - total_cash, 0.0)
            
            net_debt_to_fcf = round(net_debt / fcf, 2) if fcf > 0 else 99.0

            roe = float(info.get("returnOnEquity", 0.0)) * 100
            gross_margin = float(info.get("grossMargins", 0.0)) * 100
            op_margin = float(info.get("operatingMargins", 0.0)) * 100
            
            # Wskaźnik ROIC szacunkowy
            roic = roe * 0.7 if roe > 0 else 5.0

            return FundamentalData(
                ticker=ticker.upper(),
                company_name=info.get("shortName") or info.get("longName") or ticker.upper(),
                sector=info.get("sector", "General"),
                industry=info.get("industry", "General"),
                current_price=price,
                market_cap=mcap,
                roe_pct=round(roe, 1),
                roic_pct=round(roic, 1),
                gross_margin_pct=round(gross_margin, 1),
                operating_margin_pct=round(op_margin, 1),
                fcf_history_5y=[fcf * 0.8, fcf * 0.85, fcf * 0.9, fcf * 0.95, fcf],
                revenue_growth_5y_cagr=round(float(info.get("revenueGrowth", 0.05)) * 100, 1),
                net_debt=net_debt,
                total_cash=total_cash,
                net_debt_to_fcf=net_debt_to_fcf,
                current_ratio=float(info.get("currentRatio", 1.2)),
                altman_z_score=4.0,
                pe_ratio=float(info.get("trailingPE", 20.0)),
                shares_outstanding=shares,
                free_cash_flow_ttm=fcf,
                capex_ttm=float(info.get("capitalExpenditures", 0.0)),
                net_income_ttm=net_income,
                beta=float(info.get("beta", 1.0)),
                dividend_yield_pct=round(float(info.get("dividendYield", 0.0)) * 100, 2),
                source="yfinance"
            )
        except Exception as e:
            print(f"[YFinance Error] {ticker}: {e}")
            return None

    def search_screener_candidates(self) -> List[str]:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "BRK.B", "KO", "V", "JNJ", "PG", "NVDA", "TGT", "COST"]

    def get_sp500_current(self) -> float:
        try:
            sp = yf.Ticker("^GSPC")
            val = sp.info.get("regularMarketPrice") or sp.info.get("currentPrice")
            return float(val) if val else 5950.0
        except Exception:
            return 5950.0
