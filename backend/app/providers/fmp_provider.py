import math
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import requests

from app.config import settings
from app.providers.base import BaseMarketDataProvider, FundamentalData

_FMP_CACHE: Dict[str, Tuple[float, FundamentalData]] = {}
_FMP_NEWS_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_FMP_SP500_CACHE: Tuple[float, float] = (0.0, 0.0)

FMP_TTL_SEC = 900       # 15 minut
FMP_PRICE_TTL_SEC = 300 # 5 minut


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _to_fmp_symbol(ticker: str) -> str:
    t = ticker.strip().upper()
    parts = t.split(".")
    if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isalpha():
        return f"{parts[0]}-{parts[1]}"
    return t


class FMPDataProvider(BaseMarketDataProvider):
    """
    Dostawca danych Financial Modeling Prep (FMP):
    - Obsługuje nowoczesne endpointy /stable/... (dla nowych kluczy FMP) z fallbackiem do /api/v3/...
    - Pobiera znormalizowane sprawozdania finansowe (5 lat FCF, przychodów, bilansu), newsy i ceny historyczne.
    - W razie przekroczenia dziennego limitu free-tier (250 req/dzień) lub braku danych dla tickera
      automatycznie wspomaga się YFinanceDataProvider, aby analiza nigdy nie przerywała pracy.
    """

    def __init__(self, api_key: Optional[str] = None, allow_yf_fallback: bool = True):
        self.api_key = (api_key if api_key is not None else settings.FMP_API_KEY or "").strip()
        self.stable_url = "https://financialmodelingprep.com/stable"
        self.v3_url = "https://financialmodelingprep.com/api/v3"
        self.allow_yf_fallback = allow_yf_fallback

    def _get_json(self, path_stable: str, path_v3: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.api_key:
            return None
        p = dict(params or {})
        p["apikey"] = self.api_key

        # 1. Spróbuj /stable/
        try:
            r = requests.get(f"{self.stable_url}/{path_stable}", params=p, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    return data
                if isinstance(data, dict) and data and "Error Message" not in data:
                    return data
        except Exception:
            pass

        # 2. Fallback /api/v3/ (dla starszych planów FMP)
        if path_v3:
            try:
                r2 = requests.get(f"{self.v3_url}/{path_v3}", params=p, timeout=10)
                if r2.status_code == 200:
                    data2 = r2.json()
                    if isinstance(data2, list) and len(data2) > 0:
                        return data2
                    if isinstance(data2, dict) and data2 and "Error Message" not in data2:
                        return data2
            except Exception:
                pass

        return None

    def test_connection(self) -> Dict[str, Any]:
        """Szybki test poprawności klucza FMP API (1 zapytanie o AAPL)."""
        if not self.api_key:
            return {"ok": False, "detail": "Brak klucza FMP_API_KEY."}
        data = self._get_json("quote", "quote/AAPL", params={"symbol": "AAPL"})
        if isinstance(data, list) and data and _safe_float(data[0].get("price"), 0.0) > 0:
            return {
                "ok": True,
                "detail": f"Połączono z FMP API (AAPL = ${_safe_float(data[0].get('price')):.2f})",
            }
        return {
            "ok": False,
            "detail": "FMP API odrzuciło klucz lub wyczerpano dzienny limit zapytań.",
        }

    def get_ticker_data(self, ticker: str, bypass_cache: bool = False) -> Optional[FundamentalData]:
        canonical = ticker.strip().upper()
        fmp_sym = _to_fmp_symbol(canonical)

        now = time.time()
        if not bypass_cache and canonical in _FMP_CACHE:
            ts, cached = _FMP_CACHE[canonical]
            if now - ts < FMP_TTL_SEC:
                return cached

        if not self.api_key:
            return self._fallback_yfinance(canonical, bypass_cache=bypass_cache)

        try:
            # 1. Profile + Quote
            profile_list = self._get_json("profile", f"profile/{fmp_sym}", params={"symbol": fmp_sym})
            quote_list = self._get_json("quote", f"quote/{fmp_sym}", params={"symbol": fmp_sym})

            prof = profile_list[0] if isinstance(profile_list, list) and profile_list else {}
            q = quote_list[0] if isinstance(quote_list, list) and quote_list else {}

            price = _safe_float(q.get("price") or prof.get("price"), 0.0)
            if price <= 0:
                return self._fallback_yfinance(canonical, bypass_cache=bypass_cache)

            mcap = _safe_float(q.get("marketCap") or prof.get("mktCap") or prof.get("marketCap"), 0.0)
            if mcap > 0 and price > 0:
                shares = mcap / price
            else:
                shares = _safe_float(q.get("sharesOutstanding"), 0.0)
                if mcap <= 0 and shares > 0:
                    mcap = shares * price

            # 2. Key Metrics & Ratios TTM
            km_list = self._get_json("key-metrics-ttm", f"key-metrics-ttm/{fmp_sym}", params={"symbol": fmp_sym})
            rat_list = self._get_json("ratios-ttm", f"ratios-ttm/{fmp_sym}", params={"symbol": fmp_sym})
            km = km_list[0] if isinstance(km_list, list) and km_list else {}
            rat = rat_list[0] if isinstance(rat_list, list) and rat_list else {}

            # 3. 5-letnie sprawozdania: Cash Flow + Income + Balance Sheet
            cf_list = self._get_json(
                "cash-flow-statement",
                f"cash-flow-statement/{fmp_sym}",
                params={"symbol": fmp_sym, "period": "annual", "limit": 5},
            ) or []
            inc_list = self._get_json(
                "income-statement",
                f"income-statement/{fmp_sym}",
                params={"symbol": fmp_sym, "period": "annual", "limit": 5},
            ) or []
            bs_list = self._get_json(
                "balance-sheet-statement",
                f"balance-sheet-statement/{fmp_sym}",
                params={"symbol": fmp_sym, "period": "annual", "limit": 2},
            ) or []

            # Chronologiczna historia FCF (najstarsze -> najnowsze)
            fcf_hist = [
                round(_safe_float(item.get("freeCashFlow"), 0.0), 2)
                for item in reversed(cf_list)
                if item.get("freeCashFlow") is not None
            ]
            fcf_ttm = _safe_float(km.get("freeCashFlowPerShareTTM"), 0.0) * shares if km.get("freeCashFlowPerShareTTM") is not None else 0.0
            if fcf_ttm == 0.0 and fcf_hist:
                fcf_ttm = fcf_hist[-1]

            capex_ttm = abs(_safe_float(cf_list[0].get("capitalExpenditure"), 0.0)) if cf_list else 0.0
            net_income_ttm = _safe_float(inc_list[0].get("netIncome"), 0.0) if inc_list else (
                _safe_float(km.get("netIncomePerShareTTM"), 0.0) * shares
            )

            # Bilans (signed net_debt: < 0 = gotówka netto)
            bs0 = bs_list[0] if bs_list else {}
            total_debt = _safe_float(bs0.get("totalDebt"), 0.0)
            total_cash = _safe_float(
                bs0.get("cashAndShortTermInvestments") or bs0.get("cashAndCashEquivalents"),
                0.0,
            )
            net_debt = total_debt - total_cash
            if net_debt <= 0:
                net_debt_to_fcf = 0.0
            elif fcf_ttm > 0:
                net_debt_to_fcf = round(net_debt / fcf_ttm, 2)
            else:
                net_debt_to_fcf = 99.0

            # Rentowność & Marże
            roe = _safe_float(km.get("returnOnEquityTTM") or km.get("roeTTM") or rat.get("returnOnEquityTTM"), 0.0) * 100.0
            roic = _safe_float(km.get("returnOnInvestedCapitalTTM") or km.get("roicTTM"), 0.0) * 100.0
            gross_margin = _safe_float(rat.get("grossProfitMarginTTM") or km.get("grossProfitMarginTTM"), 0.0) * 100.0
            op_margin = _safe_float(rat.get("operatingProfitMarginTTM") or km.get("operatingProfitMarginTTM"), 0.0) * 100.0

            if gross_margin == 0.0 and inc_list:
                rev0 = _safe_float(inc_list[0].get("revenue"), 0.0)
                gp0 = _safe_float(inc_list[0].get("grossProfit"), 0.0)
                oi0 = _safe_float(inc_list[0].get("operatingIncome"), 0.0)
                if rev0 > 0:
                    gross_margin = (gp0 / rev0) * 100.0
                    op_margin = (oi0 / rev0) * 100.0

            # Wieloletni CAGR przychodów
            rev_cagr = 0.0
            revs = [_safe_float(x.get("revenue"), 0.0) for x in reversed(inc_list) if _safe_float(x.get("revenue"), 0.0) > 0]
            if len(revs) >= 2 and revs[0] > 0:
                rev_cagr = (((revs[-1] / revs[0]) ** (1.0 / (len(revs) - 1))) - 1.0) * 100.0

            # Current Ratio & Altman Z-Score
            current_ratio = _safe_float(km.get("currentRatioTTM") or rat.get("currentRatioTTM"), 0.0)
            if current_ratio == 0.0 and bs0:
                ca = _safe_float(bs0.get("totalCurrentAssets"), 0.0)
                cl = _safe_float(bs0.get("totalCurrentLiabilities"), 0.0)
                current_ratio = round(ca / cl, 2) if cl > 0 else 1.0

            altman_z = None
            if bs0 and inc_list and mcap > 0:
                ta = _safe_float(bs0.get("totalAssets"), 0.0)
                tl = _safe_float(bs0.get("totalLiabilities"), 0.0)
                ca = _safe_float(bs0.get("totalCurrentAssets"), 0.0)
                cl = _safe_float(bs0.get("totalCurrentLiabilities"), 0.0)
                re = _safe_float(bs0.get("retainedEarnings"), 0.0)
                ebit = _safe_float(inc_list[0].get("operatingIncome"), 0.0)
                rev0 = _safe_float(inc_list[0].get("revenue"), 0.0)
                if ta > 0 and tl > 0:
                    z = 1.2 * ((ca - cl) / ta) + 1.4 * (re / ta) + 3.3 * (ebit / ta) + 0.6 * (mcap / tl) + 1.0 * (rev0 / ta)
                    altman_z = round(z, 2)

            pe_ratio = _safe_float(q.get("pe") or rat.get("priceToEarningsRatioTTM") or km.get("peRatioTTM"), 0.0)
            if pe_ratio == 0.0 and net_income_ttm > 0 and mcap > 0:
                pe_ratio = round(mcap / net_income_ttm, 2)

            div_yield = _safe_float(rat.get("dividendYieldTTM") or km.get("dividendYieldTTM"), 0.0) * 100.0
            if div_yield == 0.0 and prof.get("lastDividend") and price > 0:
                div_yield = (_safe_float(prof.get("lastDividend"), 0.0) / price) * 100.0

            result = FundamentalData(
                ticker=canonical,
                company_name=prof.get("companyName") or q.get("name") or canonical,
                sector=prof.get("sector") or "General",
                industry=prof.get("industry") or "General",
                current_price=round(price, 2),
                market_cap=mcap,
                roe_pct=round(roe, 1),
                roic_pct=round(roic, 1),
                gross_margin_pct=round(gross_margin, 1),
                operating_margin_pct=round(op_margin, 1),
                fcf_history_5y=fcf_hist,
                revenue_growth_5y_cagr=round(rev_cagr, 1),
                net_debt=net_debt,
                total_cash=total_cash,
                net_debt_to_fcf=net_debt_to_fcf,
                current_ratio=round(current_ratio, 2),
                altman_z_score=altman_z,
                pe_ratio=round(pe_ratio, 2),
                shares_outstanding=shares,
                free_cash_flow_ttm=fcf_ttm,
                capex_ttm=capex_ttm,
                net_income_ttm=net_income_ttm,
                beta=round(_safe_float(prof.get("beta"), 1.0), 2),
                dividend_yield_pct=round(div_yield, 2),
                source="fmp",
            )
            _FMP_CACHE[canonical] = (now, result)
            return result
        except Exception as e:
            print(f"[FMP Error] {canonical}: {e}")
            return self._fallback_yfinance(canonical, bypass_cache=bypass_cache)

    def _fallback_yfinance(self, ticker: str, bypass_cache: bool = False) -> Optional[FundamentalData]:
        if not self.allow_yf_fallback:
            return None
        from app.providers.yfinance_provider import YFinanceDataProvider
        return YFinanceDataProvider().get_ticker_data(ticker, bypass_cache=bypass_cache)

    def screen_us_stocks(
        self,
        max_price: Optional[float] = None,
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
        sector: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Korzysta z serwerowego FMP Company Screener (/stable/company-screener) do odkrywania
        amerykańskich spółek (w tym małych / tanich walorów NYSE/NASDAQ).
        """
        if not self.api_key:
            return []
        params: Dict[str, Any] = {
            "country": "US",
            "isActivelyTrading": "true",
            "isEtf": "false",
            "isFund": "false",
            "limit": limit,
        }
        if max_price is not None:
            params["priceLowerThan"] = max_price
        if min_market_cap is not None:
            params["marketCapMoreThan"] = int(min_market_cap)
        if max_market_cap is not None:
            params["marketCapLowerThan"] = int(max_market_cap)
        if sector:
            params["sector"] = sector

        res = self._get_json("company-screener", "stock-screener", params=params)
        if not isinstance(res, list):
            return []
        return res

    def search_screener_candidates(self) -> List[str]:
        return [
            "BRK.B", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "V", "KO", "COST",
            "SOFI", "PLTR", "HOOD", "RKLB", "CROX", "DUOL", "ELF", "CELH",
        ]

    def get_sp500_current(self) -> float:
        global _FMP_SP500_CACHE
        now = time.time()
        if now - _FMP_SP500_CACHE[0] < FMP_PRICE_TTL_SEC and _FMP_SP500_CACHE[1] > 0:
            return _FMP_SP500_CACHE[1]

        if self.api_key:
            data = self._get_json("quote", "quote/^GSPC", params={"symbol": "^GSPC"})
            if isinstance(data, list) and data:
                val = round(_safe_float(data[0].get("price"), 0.0), 2)
                if val > 0:
                    _FMP_SP500_CACHE = (now, val)
                    return val

        from app.providers.yfinance_provider import YFinanceDataProvider
        return YFinanceDataProvider().get_sp500_current()

    def get_historical_prices(self, tickers: List[str], days: int = 95) -> Dict[str, List[Dict[str, Any]]]:
        from app.providers.yfinance_provider import YFinanceDataProvider
        return YFinanceDataProvider().get_historical_prices(tickers, days=days)

    def get_ticker_news(self, ticker: str, limit: int = 8) -> List[Dict[str, Any]]:
        canonical = ticker.strip().upper()
        now = time.time()
        if canonical in _FMP_NEWS_CACHE and now - _FMP_NEWS_CACHE[canonical][0] < FMP_TTL_SEC:
            return _FMP_NEWS_CACHE[canonical][1][:limit]

        if self.api_key:
            fmp_sym = _to_fmp_symbol(canonical)
            raw = self._get_json(
                "news/stock",
                "stock_news",
                params={"symbols": fmp_sym, "tickers": fmp_sym, "limit": limit},
            )
            if isinstance(raw, list) and raw:
                items = []
                for item in raw[:limit]:
                    title = (item.get("title") or "").strip()
                    if not title:
                        continue
                    items.append({
                        "title": title,
                        "publisher": item.get("site") or item.get("publisher") or "FMP News",
                        "link": item.get("url") or "",
                        "published_at": str(item.get("publishedDate") or "")[:16],
                        "summary": (item.get("text") or "")[:240],
                    })
                if items:
                    _FMP_NEWS_CACHE[canonical] = (now, items)
                    return items

        from app.providers.yfinance_provider import YFinanceDataProvider
        return YFinanceDataProvider().get_ticker_news(canonical, limit=limit)
