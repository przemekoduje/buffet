import math
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import yfinance as yf
from app.providers.base import BaseMarketDataProvider, FundamentalData

# Prosty cache TTL w pamięci (chroni przed limitami Yahoo Finance i przyspiesza screener)
_FUNDAMENTAL_CACHE: Dict[str, Tuple[float, FundamentalData]] = {}
_SP500_CACHE: Tuple[float, float] = (0.0, 0.0)
_HISTORY_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_NEWS_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}

FUNDAMENTAL_TTL_SEC = 900  # 15 minut
PRICE_TTL_SEC = 300        # 5 minut


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


def _to_yf_symbol(ticker: str) -> str:
    """Konwertuje tickery z klasą akcji z kropką (np. BRK.B -> BRK-B) na format Yahoo Finance."""
    t = ticker.strip().upper()
    parts = t.split(".")
    if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isalpha():
        return f"{parts[0]}-{parts[1]}"
    return t


def _extract_row_series(df: Any, candidates: List[str]) -> List[Tuple[Any, float]]:
    """Wyciąga chronologiczną serię (data, wartość) dla pierwszego pasującego wiersza sprawozdania."""
    if df is None or getattr(df, "empty", True):
        return []
    for name in candidates:
        if name in df.index:
            row = df.loc[name]
            items = []
            for col, val in row.items():
                num = _safe_float(val, float("nan"))
                if not math.isnan(num):
                    items.append((col, num))
            if items:
                items.sort(key=lambda x: str(x[0]))
                return items
    return []


class YFinanceDataProvider(BaseMarketDataProvider):
    """Realny dostawca danych rynkowych i sprawozdań finansowych oparty o Yahoo Finance."""

    def get_ticker_data(self, ticker: str, bypass_cache: bool = False) -> Optional[FundamentalData]:
        canonical = ticker.strip().upper()
        yf_symbol = _to_yf_symbol(canonical)

        now = time.time()
        if not bypass_cache and canonical in _FUNDAMENTAL_CACHE:
            ts, cached = _FUNDAMENTAL_CACHE[canonical]
            if now - ts < FUNDAMENTAL_TTL_SEC:
                return cached

        try:
            t = yf.Ticker(yf_symbol)
            info = t.info or {}

            price = _safe_float(
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose"),
                0.0,
            )
            if price <= 0:
                hist = t.history(period="5d")
                if hist is not None and not hist.empty:
                    price = _safe_float(hist["Close"].iloc[-1], 0.0)
            if price <= 0:
                return None

            mcap = _safe_float(info.get("marketCap"), 0.0)
            raw_shares = _safe_float(info.get("sharesOutstanding"), 0.0)
            # Dla spółek wieloklasowych (np. BRK.B, GOOGL, V) Yahoo zwraca w sharesOutstanding
            # tylko jedną klasę akcji. Implikowana liczba akcji (marketCap / price) obejmuje wszystkie klasy.
            if mcap > 0 and price > 0:
                shares = mcap / price
            else:
                shares = raw_shares
                if mcap <= 0 and shares > 0:
                    mcap = shares * price

            # Sprawozdania finansowe (realne dane historyczne)
            cashflow = None
            income_stmt = None
            balance_sheet = None
            try:
                cashflow = t.cashflow
            except Exception:
                pass
            try:
                income_stmt = t.income_stmt
            except Exception:
                pass
            try:
                balance_sheet = t.balance_sheet
            except Exception:
                pass

            # 1. Realna historia Free Cash Flow (ostatnie dostępne lata z cashflow)
            fcf_series = _extract_row_series(cashflow, ["Free Cash Flow"])
            ocf_series = _extract_row_series(cashflow, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
            capex_series = _extract_row_series(cashflow, ["Capital Expenditure", "Purchase Of PPE"])

            if fcf_series:
                fcf_history = [round(v, 2) for _, v in fcf_series[-5:]]
            elif ocf_series and capex_series:
                capex_map = {str(d): abs(v) for d, v in capex_series}
                fcf_history = [
                    round(v - capex_map.get(str(d), 0.0), 2)
                    for d, v in ocf_series[-5:]
                ]
            else:
                fcf_history = []

            fcf_ttm = _safe_float(info.get("freeCashflow"), 0.0)
            if fcf_ttm == 0.0 and fcf_history:
                fcf_ttm = fcf_history[-1]
            if not fcf_history and fcf_ttm != 0.0:
                fcf_history = [round(fcf_ttm, 2)]

            capex_ttm = abs(_safe_float(info.get("capitalExpenditures"), 0.0))
            if capex_ttm == 0.0 and capex_series:
                capex_ttm = abs(capex_series[-1][1])

            net_income = _safe_float(info.get("netIncomeToCommon"), 0.0)
            if net_income == 0.0:
                ni_series = _extract_row_series(income_stmt, ["Net Income", "Net Income Common Stockholders"])
                if ni_series:
                    net_income = ni_series[-1][1]

            # 2. Bilans i zadłużenie
            total_debt = _safe_float(info.get("totalDebt"), 0.0)
            total_cash = _safe_float(info.get("totalCash"), 0.0)
            if total_debt == 0.0:
                td_series = _extract_row_series(balance_sheet, ["Total Debt"])
                if td_series:
                    total_debt = td_series[-1][1]
            if total_cash == 0.0:
                tc_series = _extract_row_series(
                    balance_sheet,
                    ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"],
                )
                if tc_series:
                    total_cash = tc_series[-1][1]

            # Signed net_debt: wartość ujemna oznacza gotówkę netto (Cash > Debt)
            net_debt = total_debt - total_cash
            if net_debt <= 0:
                net_debt_to_fcf = 0.0
            elif fcf_ttm > 0:
                net_debt_to_fcf = round(net_debt / fcf_ttm, 2)
            else:
                net_debt_to_fcf = 99.0

            # 3. Rentowność (ROE, Marże, realny ROIC)
            roe = _safe_float(info.get("returnOnEquity"), 0.0) * 100
            gross_margin = _safe_float(info.get("grossMargins"), 0.0) * 100
            op_margin = _safe_float(info.get("operatingMargins"), 0.0) * 100

            roic = self._compute_real_roic(income_stmt, balance_sheet, total_debt, total_cash, roe)

            # 4. Realny wieloletni CAGR przychodów
            rev_cagr = self._compute_revenue_cagr(income_stmt, info)

            # 5. Realny Altman Z-Score (jeśli dane bilansowe dostępne)
            altman_z = self._compute_altman_z(balance_sheet, income_stmt, mcap)

            # 6. Płynność bieżąca, P/E, Beta, Dywidenda
            current_ratio = _safe_float(info.get("currentRatio"), 0.0)
            if current_ratio == 0.0:
                ca_s = _extract_row_series(balance_sheet, ["Current Assets"])
                cl_s = _extract_row_series(balance_sheet, ["Current Liabilities"])
                if ca_s and cl_s and cl_s[-1][1] > 0:
                    current_ratio = round(ca_s[-1][1] / cl_s[-1][1], 2)
                else:
                    current_ratio = 1.0

            pe_ratio = _safe_float(info.get("trailingPE") or info.get("forwardPE"), 0.0)
            if pe_ratio == 0.0 and net_income > 0 and mcap > 0:
                pe_ratio = round(mcap / net_income, 2)

            beta = _safe_float(info.get("beta"), 1.0)

            # Yahoo Finance: trailingAnnualDividendYield jest ułamkiem (np. 0.0045 -> 0.45%),
            # natomiast dividendYield w nowszych wersjach yfinance bywa już w % (np. 0.45 -> 0.45%).
            trailing_div = info.get("trailingAnnualDividendYield")
            if trailing_div is not None:
                div_yield_pct = round(_safe_float(trailing_div, 0.0) * 100, 2)
            else:
                raw_div = _safe_float(info.get("dividendYield"), 0.0)
                div_yield_pct = round(raw_div if raw_div > 0.2 else raw_div * 100, 2)

            result = FundamentalData(
                ticker=canonical,
                company_name=info.get("shortName") or info.get("longName") or canonical,
                sector=info.get("sector") or "General",
                industry=info.get("industry") or "General",
                current_price=round(price, 2),
                market_cap=mcap,
                roe_pct=round(roe, 1),
                roic_pct=round(roic, 1),
                gross_margin_pct=round(gross_margin, 1),
                operating_margin_pct=round(op_margin, 1),
                fcf_history_5y=fcf_history,
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
                net_income_ttm=net_income,
                beta=round(beta, 2),
                dividend_yield_pct=div_yield_pct,
                source="yfinance",
            )
            _FUNDAMENTAL_CACHE[canonical] = (now, result)
            return result
        except Exception as e:
            print(f"[YFinance Error] {canonical} ({yf_symbol}): {e}")
            return None

    @staticmethod
    def _compute_real_roic(
        income_stmt: Any,
        balance_sheet: Any,
        total_debt: float,
        total_cash: float,
        roe_fallback: float,
    ) -> float:
        ebit_s = _extract_row_series(income_stmt, ["EBIT", "Operating Income"])
        tax_s = _extract_row_series(income_stmt, ["Tax Provision"])
        pretax_s = _extract_row_series(income_stmt, ["Pretax Income"])
        equity_s = _extract_row_series(
            balance_sheet,
            ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"],
        )

        if ebit_s and equity_s:
            ebit = ebit_s[-1][1]
            equity = equity_s[-1][1]
            tax_rate = 0.21
            if tax_s and pretax_s and pretax_s[-1][1] > 0:
                tax_rate = min(max(tax_s[-1][1] / pretax_s[-1][1], 0.0), 0.35)
            nopat = ebit * (1.0 - tax_rate)
            invested_capital = total_debt + equity - total_cash
            if invested_capital > 0:
                return (nopat / invested_capital) * 100.0

        return max(roe_fallback * 0.7, 0.0)

    @staticmethod
    def _compute_revenue_cagr(income_stmt: Any, info: Dict[str, Any]) -> float:
        rev_s = _extract_row_series(income_stmt, ["Total Revenue", "Operating Revenue"])
        if len(rev_s) >= 2:
            oldest = rev_s[0][1]
            latest = rev_s[-1][1]
            years = len(rev_s) - 1
            if oldest > 0 and latest > 0 and years > 0:
                return (((latest / oldest) ** (1.0 / years)) - 1.0) * 100.0
        return _safe_float(info.get("revenueGrowth"), 0.0) * 100.0

    @staticmethod
    def _compute_altman_z(balance_sheet: Any, income_stmt: Any, mcap: float) -> Optional[float]:
        ta_s = _extract_row_series(balance_sheet, ["Total Assets"])
        tl_s = _extract_row_series(balance_sheet, ["Total Liabilities Net Minority Interest"])
        ca_s = _extract_row_series(balance_sheet, ["Current Assets"])
        cl_s = _extract_row_series(balance_sheet, ["Current Liabilities"])
        re_s = _extract_row_series(balance_sheet, ["Retained Earnings"])
        ebit_s = _extract_row_series(income_stmt, ["EBIT", "Operating Income"])
        rev_s = _extract_row_series(income_stmt, ["Total Revenue", "Operating Revenue"])

        if not (ta_s and tl_s and ca_s and cl_s and re_s and ebit_s and rev_s and mcap > 0):
            return None

        ta = ta_s[-1][1]
        tl = tl_s[-1][1]
        if ta <= 0 or tl <= 0:
            return None

        x1 = (ca_s[-1][1] - cl_s[-1][1]) / ta
        x2 = re_s[-1][1] / ta
        x3 = ebit_s[-1][1] / ta
        x4 = mcap / tl
        x5 = rev_s[-1][1] / ta
        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
        return round(z, 2)

    def search_screener_candidates(self) -> List[str]:
        return ["BRK.B", "AAPL", "MSFT", "GOOGL", "AMZN", "KO", "V", "JNJ", "PG", "NVDA", "TGT", "COST"]

    def get_sp500_current(self) -> float:
        global _SP500_CACHE
        now = time.time()
        if now - _SP500_CACHE[0] < PRICE_TTL_SEC and _SP500_CACHE[1] > 0:
            return _SP500_CACHE[1]
        try:
            sp = yf.Ticker("^GSPC")
            hist = sp.history(period="5d")
            if hist is not None and not hist.empty:
                val = round(_safe_float(hist["Close"].iloc[-1], 0.0), 2)
                if val > 0:
                    _SP500_CACHE = (now, val)
                    return val
            val = _safe_float(sp.info.get("regularMarketPrice") or sp.info.get("currentPrice"), 0.0)
            if val > 0:
                _SP500_CACHE = (now, round(val, 2))
                return round(val, 2)
        except Exception as e:
            print(f"[YFinance S&P500 Error] {e}")
        return _SP500_CACHE[1] if _SP500_CACHE[1] > 0 else 0.0

    def get_historical_prices(self, tickers: List[str], days: int = 95) -> Dict[str, List[Dict[str, Any]]]:
        """Pobiera realne dzienne ceny zamknięcia z Yahoo Finance dla listy tickerów."""
        now = time.time()
        result: Dict[str, List[Dict[str, Any]]] = {}
        start_dt = (datetime.utcnow() - timedelta(days=days + 15)).strftime("%Y-%m-%d")

        for ticker in tickers:
            canonical = ticker.strip().upper()
            cache_key = f"{canonical}:{days}"
            if cache_key in _HISTORY_CACHE and now - _HISTORY_CACHE[cache_key][0] < PRICE_TTL_SEC:
                result[canonical] = _HISTORY_CACHE[cache_key][1]
                continue

            yf_symbol = _to_yf_symbol(canonical) if not canonical.startswith("^") else canonical
            try:
                hist = yf.Ticker(yf_symbol).history(start=start_dt, auto_adjust=True)
                series: List[Dict[str, Any]] = []
                if hist is not None and not hist.empty:
                    for idx, row in hist.iterrows():
                        close_val = _safe_float(row.get("Close"), 0.0)
                        if close_val > 0:
                            series.append({
                                "date": idx.strftime("%Y-%m-%d"),
                                "close": round(close_val, 2),
                            })
                if series:
                    _HISTORY_CACHE[cache_key] = (now, series)
                    result[canonical] = series
            except Exception as e:
                print(f"[YFinance History Error] {canonical}: {e}")

        return result

    def get_ticker_news(self, ticker: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Pobiera najnowsze newsy rynkowe dla spółki z Yahoo Finance (z cache 15 min)."""
        canonical = ticker.strip().upper()
        now = time.time()
        if canonical in _NEWS_CACHE and now - _NEWS_CACHE[canonical][0] < FUNDAMENTAL_TTL_SEC:
            return _NEWS_CACHE[canonical][1][:limit]

        yf_symbol = _to_yf_symbol(canonical)
        items: List[Dict[str, Any]] = []
        try:
            raw_news = yf.Ticker(yf_symbol).news or []
            for entry in raw_news[: max(limit, 8)]:
                content = entry.get("content") if isinstance(entry.get("content"), dict) else entry
                title = (content.get("title") or "").strip()
                if not title:
                    continue
                summary = (content.get("summary") or content.get("description") or "").strip()
                provider_obj = content.get("provider")
                publisher = (
                    provider_obj.get("displayName")
                    if isinstance(provider_obj, dict)
                    else (content.get("publisher") or "Yahoo Finance")
                )
                pub_date = content.get("pubDate") or content.get("displayTime") or ""
                if not pub_date and content.get("providerPublishTime"):
                    try:
                        pub_date = datetime.utcfromtimestamp(int(content["providerPublishTime"])).strftime("%Y-%m-%d %H:%M UTC")
                    except Exception:
                        pub_date = ""
                elif pub_date and "T" in pub_date:
                    pub_date = pub_date.replace("T", " ").replace("Z", " UTC")[:16] + " UTC"

                url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl")
                url = (
                    url_obj.get("url")
                    if isinstance(url_obj, dict)
                    else (content.get("link") or "")
                )

                items.append({
                    "title": title,
                    "summary": summary[:260],
                    "publisher": publisher or "Yahoo Finance",
                    "published_at": pub_date,
                    "url": url or "",
                })
            _NEWS_CACHE[canonical] = (now, items)
        except Exception as e:
            print(f"[YFinance News Error] {canonical}: {e}")

        return items[:limit]
