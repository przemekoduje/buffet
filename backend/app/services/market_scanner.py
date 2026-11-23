import asyncio
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import yfinance as yf
from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import MarketAlert, MarketScanResult, PortfolioHolding
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator

try:
    US_EASTERN = ZoneInfo("America/New_York")
except Exception:
    # Fallback na UTC-5 gdyby system nie miał tzdata
    US_EASTERN = timezone(timedelta(hours=-5))


BASKETS: Dict[str, Dict[str, Any]] = {
    "us_quality": {
        "id": "us_quality",
        "name": "US Quality",
        "subtitle": "Trwała fosa ekonomiczna, wysokie ROIC i dominacja rynkowa",
        "tickers": [
            "BRK.B", "AAPL", "MSFT", "GOOGL", "V", "MA", "COST",
            "NVDA", "META", "SPGI", "MCO", "INTU", "ORCL", "ADBE",
        ],
    },
    "sp500_value": {
        "id": "sp500_value",
        "name": "S&P 500 Value",
        "subtitle": "Spółki wartościowe z silnymi przepływami FCF i potencjałem dyskonta",
        "tickers": [
            "BRK.B", "JPM", "UNH", "CVS", "CMCSA", "PYPL", "DIS",
            "TGT", "GM", "BAC", "XOM", "CVX", "QCOM", "AMZN",
        ],
    },
    "dividend_aristocrats": {
        "id": "dividend_aristocrats",
        "name": "Dywidendowi Arystokraci",
        "subtitle": "Minimum 25 lat nieprzerwanego wzrostu dywidendy i odporne bilanse",
        "tickers": [
            "KO", "JNJ", "PG", "PEP", "ABT", "MCD", "WMT",
            "LOW", "CL", "CAT", "SHW", "ADP", "CB", "NEE",
        ],
    },
}


def _to_yf_symbol(ticker: str) -> str:
    t = ticker.strip().upper()
    parts = t.split(".")
    if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isalpha():
        return f"{parts[0]}-{parts[1]}"
    return t


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


class MarketScanner:
    """
    Silnik okresowego skanowania rynku (EOD po zamknięciu sesji USA) oraz alertów sesyjnych (intraday).
    - Skanuje 3 koszyki tematyczne: US Quality, S&P 500 Value, Dywidendowi Arystokraci.
    - Zapisuje wyniki w SQLite, aby widok Screenera był natychmiastowy.
    - W trakcie sesji USA (9:30–16:00 ET) okresowo sprawdza nietypowe ruchy cen/wolumenu i generuje alerty.
    """

    _scan_in_progress: bool = False
    _last_eod_date_et: Optional[str] = None
    _last_intraday_check: Optional[datetime] = None

    @classmethod
    def get_all_universe_tickers(cls) -> Dict[str, List[str]]:
        """Zwraca mapę ticker -> lista ID koszyków, do których należy."""
        ticker_baskets: Dict[str, List[str]] = {}
        for basket_id, meta in BASKETS.items():
            for t in meta["tickers"]:
                ticker_baskets.setdefault(t, []).append(basket_id)
        return ticker_baskets

    @classmethod
    def get_market_session_info(cls) -> Dict[str, Any]:
        now_et = datetime.now(US_EASTERN)
        weekday = now_et.weekday()  # 0=Mon .. 6=Sun
        hm = now_et.hour * 60 + now_et.minute

        if weekday >= 5:
            status = "WEEKEND"
            label = "Rynek USA zamknięty (weekend)"
            is_open = False
        elif 9 * 60 + 30 <= hm < 16 * 60:
            status = "OPEN"
            label = "Sesja USA OTWARTA (alerty intraday aktywne)"
            is_open = True
        elif 4 * 60 <= hm < 9 * 60 + 30:
            status = "PRE_MARKET"
            label = "Pre-market USA (przed otwarciem sesji)"
            is_open = False
        else:
            status = "AFTER_HOURS"
            label = "Po zamknięciu sesji USA (tryb EOD)"
            is_open = False

        return {
            "status": status,
            "label": label,
            "is_open": is_open,
            "ny_time": now_et.strftime("%Y-%m-%d %H:%M ET"),
            "next_eod_schedule": "Codziennie Pn–Pt o 16:15 ET (~22:15 czasu PL)",
            "scan_in_progress": cls._scan_in_progress,
            "last_intraday_check": (
                cls._last_intraday_check.strftime("%Y-%m-%d %H:%M UTC")
                if cls._last_intraday_check
                else None
            ),
        }

    @classmethod
    def run_market_scan(
        cls,
        db: Session,
        provider_name: Optional[str] = None,
        scan_type: str = "EOD",
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        """Pełny skan wszystkich koszyków z zapisem wyników do SQLite."""
        if cls._scan_in_progress:
            return {"status": "ALREADY_RUNNING", "scanned": 0}

        cls._scan_in_progress = True
        try:
            provider = get_market_provider(provider_name)
            ticker_baskets = cls.get_all_universe_tickers()
            tickers = list(ticker_baskets.keys())

            def _fetch_one(ticker: str):
                try:
                    if hasattr(provider, "get_ticker_data"):
                        try:
                            fund = provider.get_ticker_data(ticker, bypass_cache=bypass_cache)
                        except TypeError:
                            fund = provider.get_ticker_data(ticker)
                    else:
                        return None
                    if not fund:
                        return None
                    ev = BuffettCalculator.evaluate(fund)
                    return ticker, fund, ev
                except Exception as e:
                    print(f"[MarketScanner error] {ticker}: {e}")
                    return None

            scanned_count = 0
            now_utc = datetime.utcnow()

            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(_fetch_one, t) for t in tickers]
                for future in as_completed(futures):
                    res = future.result()
                    if not res:
                        continue
                    ticker, fund, ev = res
                    baskets_csv = ",".join(ticker_baskets.get(ticker, []))

                    row = (
                        db.query(MarketScanResult)
                        .filter(MarketScanResult.ticker == ticker)
                        .first()
                    )
                    if not row:
                        row = MarketScanResult(ticker=ticker)
                        db.add(row)

                    row.company_name = fund.company_name
                    row.sector = fund.sector
                    row.industry = fund.industry
                    row.baskets = baskets_csv
                    row.current_price = round(fund.current_price, 2)
                    row.intrinsic_value = round(ev["intrinsic_value"], 2)
                    row.margin_of_safety_pct = ev["margin_of_safety_pct"]
                    row.buffett_score = int(ev["buffett_score"])
                    row.recommendation = ev["recommendation"]
                    row.rule_number_one_risk = ev["rule_number_one_risk"]
                    row.roic_pct = fund.roic_pct
                    row.roe_pct = fund.roe_pct
                    row.gross_margin_pct = fund.gross_margin_pct
                    row.net_debt_to_fcf = fund.net_debt_to_fcf
                    row.pe_ratio = fund.pe_ratio
                    row.dividend_yield_pct = fund.dividend_yield_pct
                    row.source = fund.source
                    row.scan_type = scan_type
                    row.scanned_at = now_utc
                    scanned_count += 1

            db.commit()

            if scan_type == "EOD":
                cls._last_eod_date_et = datetime.now(US_EASTERN).strftime("%Y-%m-%d")

            # Po skanie od razu sprawdź też alerty na podstawie świeżych wycen
            try:
                cls.check_intraday_alerts(db)
            except Exception as e:
                print(f"[MarketScanner post-scan alerts error] {e}")

            return {
                "status": "COMPLETED",
                "scan_type": scan_type,
                "scanned": scanned_count,
                "total_universe": len(tickers),
                "scanned_at": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
            }
        finally:
            cls._scan_in_progress = False

    @classmethod
    def check_intraday_alerts(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Lekki batch-check cen i wolumenu dla całego uniwersum (~40 spółek w 1 zapytaniu yf.download).
        Wykrywa ciekawe zdarzenia sesyjne: okazje na przecenie (BUY_ZONE_DROP), silne ruchy i skoki wolumenu.
        """
        scan_rows = db.query(MarketScanResult).all()
        if not scan_rows:
            return []

        scan_map: Dict[str, MarketScanResult] = {r.ticker: r for r in scan_rows}
        yf_to_canonical = {_to_yf_symbol(t): t for t in scan_map.keys()}
        yf_symbols = list(yf_to_canonical.keys())

        try:
            df = yf.download(
                tickers=yf_symbols,
                period="5d",
                interval="1d",
                group_by="ticker",
                progress=False,
                threads=True,
                auto_adjust=False,
            )
        except Exception as e:
            print(f"[Intraday Alerts yf.download error] {e}")
            return []

        if df is None or df.empty:
            return []

        now_utc = datetime.utcnow()
        cls._last_intraday_check = now_utc
        cutoff_dedup = now_utc - timedelta(hours=6)

        created_alerts: List[MarketAlert] = []
        multi = hasattr(df.columns, "levels")

        for yf_sym, canonical in yf_to_canonical.items():
            try:
                sub = df[yf_sym] if multi and yf_sym in df.columns.get_level_values(0) else None
                if sub is None or sub.empty:
                    continue
                sub = sub.dropna(subset=["Close"])
                if len(sub) < 2:
                    continue

                prev_close = _safe_float(sub["Close"].iloc[-2], 0.0)
                last_close = _safe_float(sub["Close"].iloc[-1], 0.0)
                if prev_close <= 0 or last_close <= 0:
                    continue

                change_pct = round(((last_close - prev_close) / prev_close) * 100.0, 2)

                vols = [_safe_float(v, 0.0) for v in sub["Volume"].tolist() if _safe_float(v, 0.0) > 0]
                vol_ratio = 1.0
                if len(vols) >= 2:
                    avg_prev_vol = sum(vols[:-1]) / len(vols[:-1])
                    if avg_prev_vol > 0:
                        vol_ratio = round(vols[-1] / avg_prev_vol, 2)

                row = scan_map[canonical]
                # Przelicz aktualny margines bezpieczeństwa na bazie bieżącej ceny
                if row.intrinsic_value > 0:
                    live_mos = round(((row.intrinsic_value - last_close) / row.intrinsic_value) * 100.0, 1)
                else:
                    live_mos = row.margin_of_safety_pct

                # Zaktualizuj bieżącą cenę w tabeli skanu
                row.current_price = round(last_close, 2)
                row.margin_of_safety_pct = live_mos

                alert_spec: Optional[Tuple[str, str, str, str]] = None

                # 1. Okazja Buffetta: spadek na jakościowej spółce z dodatnim marginesem bezpieczeństwa
                if change_pct <= -2.0 and row.buffett_score >= 65 and live_mos >= 5.0:
                    alert_spec = (
                        "BUY_ZONE_DROP",
                        "HIGH",
                        f"Okazja Buffetta: {canonical} {change_pct:+.1f}% (MoS +{live_mos}%)",
                        (
                            f"{row.company_name} spada o {abs(change_pct):.1f}% do ${last_close:.2f}, "
                            f"powiększając margines bezpieczeństwa do +{live_mos}% przy Buffett Score {row.buffett_score}/100."
                        ),
                    )
                # 2. Silna przecena sesyjna
                elif change_pct <= -3.0:
                    alert_spec = (
                        "INTRADAY_PULLBACK",
                        "MEDIUM",
                        f"Silna przecena: {canonical} {change_pct:+.1f}%",
                        (
                            f"{row.company_name} traci {abs(change_pct):.1f}% na sesji (kurs ${last_close:.2f}, "
                            f"DCF ${row.intrinsic_value:.2f}, Buffett Score {row.buffett_score}/100)."
                        ),
                    )
                # 3. Silny ruch w górę
                elif change_pct >= 3.5:
                    alert_spec = (
                        "INTRADAY_SURGE",
                        "INFO",
                        f"Dynamiczny wzrost: {canonical} {change_pct:+.1f}%",
                        (
                            f"{row.company_name} rośnie o {change_pct:.1f}% do ${last_close:.2f} "
                            f"(wolumen {vol_ratio:.1f}x średniej, rekomendacja: {row.recommendation})."
                        ),
                    )
                # 4. Nietypowy skok wolumenu przy istotnym ruchu
                elif vol_ratio >= 1.75 and abs(change_pct) >= 1.5:
                    alert_spec = (
                        "VOLUME_SPIKE",
                        "MEDIUM",
                        f"Skok wolumenu ({vol_ratio:.1f}x): {canonical} {change_pct:+.1f}%",
                        (
                            f"Podwyższona aktywność na {row.company_name}: wolumen {vol_ratio:.1f}x średniej 5-dniowej "
                            f"przy ruchu {change_pct:+.1f}% (kurs ${last_close:.2f})."
                        ),
                    )

                if not alert_spec:
                    continue

                a_type, severity, title, message = alert_spec

                # Deduplikacja w oknie 6h dla tej samej spółki i typu alertu
                exists = (
                    db.query(MarketAlert)
                    .filter(
                        MarketAlert.ticker == canonical,
                        MarketAlert.alert_type == a_type,
                        MarketAlert.created_at >= cutoff_dedup,
                    )
                    .first()
                )
                if exists:
                    exists.price = round(last_close, 2)
                    exists.change_pct = change_pct
                    exists.volume_ratio = vol_ratio
                    exists.margin_of_safety_pct = live_mos
                    exists.title = title
                    exists.message = message
                    continue

                alert = MarketAlert(
                    ticker=canonical,
                    company_name=row.company_name,
                    alert_type=a_type,
                    severity=severity,
                    title=title,
                    message=message,
                    price=round(last_close, 2),
                    change_pct=change_pct,
                    volume_ratio=vol_ratio,
                    margin_of_safety_pct=live_mos,
                    buffett_score=row.buffett_score,
                    created_at=now_utc,
                    is_read=False,
                )
                db.add(alert)
                created_alerts.append(alert)
            except Exception as e:
                print(f"[Intraday Alert parse error] {canonical}: {e}")

        # Zachowaj tylko alerty z ostatnich 7 dni
        week_ago = now_utc - timedelta(days=7)
        db.query(MarketAlert).filter(MarketAlert.created_at < week_ago).delete()
        db.commit()

        return cls.get_recent_alerts(db)

    @classmethod
    def get_recent_alerts(cls, db: Session, limit: int = 20) -> List[Dict[str, Any]]:
        holdings_map = {
            h.ticker: h for h in db.query(PortfolioHolding).all()
        }
        alerts = (
            db.query(MarketAlert)
            .order_by(MarketAlert.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": a.id,
                "ticker": a.ticker,
                "company_name": a.company_name,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "price": a.price,
                "change_pct": a.change_pct,
                "volume_ratio": a.volume_ratio,
                "margin_of_safety_pct": a.margin_of_safety_pct,
                "buffett_score": a.buffett_score,
                "in_paper_trading": a.ticker in holdings_map,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                "is_read": a.is_read,
            }
            for a in alerts
        ]

    @classmethod
    def get_screener_payload(
        cls,
        db: Session,
        basket: str = "all",
        min_score: int = 0,
        undervalued_only: bool = False,
        buffett_picks_only: bool = False,
        provider_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        rows = db.query(MarketScanResult).all()

        # Jeśli tabela skanowania jest pusta (pierwsze uruchomienie), wykonaj wstępny skan
        if not rows and not cls._scan_in_progress:
            cls.run_market_scan(db, provider_name=provider_name, scan_type="EOD")
            rows = db.query(MarketScanResult).all()

        holdings_map: Dict[str, PortfolioHolding] = {
            h.ticker: h for h in db.query(PortfolioHolding).all()
        }

        basket_counts = {"all": len(rows)}
        for b_id in BASKETS.keys():
            basket_counts[b_id] = sum(
                1 for r in rows if b_id in (r.baskets or "").split(",")
            )

        items = []
        last_scan_dt: Optional[datetime] = None

        for r in rows:
            if r.scanned_at and (last_scan_dt is None or r.scanned_at > last_scan_dt):
                last_scan_dt = r.scanned_at

            row_baskets = [b for b in (r.baskets or "").split(",") if b]
            if basket != "all" and basket not in row_baskets:
                continue

            is_buffett_pick = (
                r.recommendation in ("STRONG_BUY", "BUY")
                or (r.buffett_score >= 70 and r.rule_number_one_risk == "LOW")
            )

            if r.buffett_score < min_score:
                continue
            if undervalued_only and r.margin_of_safety_pct <= 0:
                continue
            if buffett_picks_only and not is_buffett_pick:
                continue

            holding = holdings_map.get(r.ticker)
            items.append({
                "ticker": r.ticker,
                "company_name": r.company_name,
                "sector": r.sector,
                "industry": r.industry,
                "baskets": row_baskets,
                "current_price": r.current_price,
                "intrinsic_value": r.intrinsic_value,
                "margin_of_safety_pct": r.margin_of_safety_pct,
                "buffett_score": r.buffett_score,
                "recommendation": r.recommendation,
                "is_buffett_pick": is_buffett_pick,
                "rule_number_one_risk": r.rule_number_one_risk,
                "roic_pct": r.roic_pct,
                "roe_pct": r.roe_pct,
                "gross_margin_pct": r.gross_margin_pct,
                "net_debt_to_fcf": r.net_debt_to_fcf,
                "pe_ratio": r.pe_ratio,
                "dividend_yield_pct": r.dividend_yield_pct,
                "source": r.source,
                "in_paper_trading": holding is not None,
                "paper_trading_pnl_pct": round(holding.pnl_pct, 2) if holding else None,
                "paper_trading_entry_price": round(holding.entry_price, 2) if holding else None,
                "scanned_at": r.scanned_at.strftime("%Y-%m-%d %H:%M UTC") if r.scanned_at else None,
            })

        # Sortowanie: najpierw STRONG_BUY / BUY, potem Buffett Score i Margines Bezpieczeństwa
        rec_rank = {"STRONG_BUY": 3, "BUY": 2, "HOLD": 1, "AVOID": 0}
        items.sort(
            key=lambda x: (
                rec_rank.get(x["recommendation"], 0),
                x["buffett_score"],
                x["margin_of_safety_pct"],
            ),
            reverse=True,
        )

        baskets_meta = [
            {
                "id": "all",
                "name": "Wszystkie koszyki",
                "subtitle": "Pełne zestawienie kandydatów Buffetta ze wszystkich strategii",
                "count": basket_counts["all"],
            }
        ] + [
            {
                "id": b["id"],
                "name": b["name"],
                "subtitle": b["subtitle"],
                "count": basket_counts.get(b["id"], 0),
            }
            for b in BASKETS.values()
        ]

        return {
            "total": len(items),
            "universe_total": len(rows),
            "active_basket": basket,
            "baskets": baskets_meta,
            "last_scan_at": last_scan_dt.strftime("%Y-%m-%d %H:%M UTC") if last_scan_dt else None,
            "market_session": cls.get_market_session_info(),
            "alerts": cls.get_recent_alerts(db, limit=15),
            "items": items,
        }

    @classmethod
    async def scheduler_loop(cls):
        """
        Pętla harmonogramu w tle (uruchamiana z lifespan FastAPI):
        - Po zamknięciu sesji USA (Pn–Pt >= 16:15 ET): automatyczny skan EOD raz dziennie.
        - W trakcie sesji USA (Pn–Pt 9:30–16:00 ET): co 15 min lekki skan alertów intraday.
        """
        while True:
            try:
                now_et = datetime.now(US_EASTERN)
                weekday = now_et.weekday()
                hm = now_et.hour * 60 + now_et.minute
                today_et = now_et.strftime("%Y-%m-%d")

                # 1. Automatyczny skan EOD po zamknięciu sesji USA (16:15 ET)
                if weekday < 5 and hm >= 16 * 60 + 15 and cls._last_eod_date_et != today_et:
                    print(f"[MarketScanner] Start automatycznego skanu EOD ({today_et} {now_et.strftime('%H:%M')} ET)")
                    db = SessionLocal()
                    try:
                        await asyncio.to_thread(cls.run_market_scan, db, None, "EOD", True)
                    finally:
                        db.close()

                # 2. Alerty intraday w trakcie sesji USA (co 15 minut)
                elif weekday < 5 and (9 * 60 + 30 <= hm < 16 * 60):
                    need_check = (
                        cls._last_intraday_check is None
                        or (datetime.utcnow() - cls._last_intraday_check) >= timedelta(minutes=15)
                    )
                    if need_check:
                        db = SessionLocal()
                        try:
                            await asyncio.to_thread(cls.check_intraday_alerts, db)
                        finally:
                            db.close()
            except Exception as e:
                print(f"[MarketScanner scheduler error] {e}")

            await asyncio.sleep(300)  # sprawdzaj co 5 minut
