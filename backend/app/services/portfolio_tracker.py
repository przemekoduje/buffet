import math
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database.db import engine
from app.database.models import (
    PaperAccountConfig,
    PaperTrade,
    PortfolioHolding,
    PortfolioSnapshot,
    Signal,
)
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator

_LAST_REFRESH_TS: float = 0.0
REFRESH_COOLDOWN_SEC: int = 300  # 5 minut


def ensure_portfolio_schema() -> None:
    """Bezpiecznie dodaje nowe kolumny SL/TP do istniejącej tabeli portfolio_holdings w SQLite."""
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(portfolio_holdings)")).fetchall()]
        if cols and "stop_loss_price" not in cols:
            conn.execute(text("ALTER TABLE portfolio_holdings ADD COLUMN stop_loss_price FLOAT"))
        if cols and "take_profit_price" not in cols:
            conn.execute(text("ALTER TABLE portfolio_holdings ADD COLUMN take_profit_price FLOAT"))
        conn.commit()


def _find_price_on_or_after(series: List[Dict[str, Any]], target_date: str) -> Optional[Tuple[str, float]]:
    """Znajduje cenę zamknięcia w dniu target_date lub w pierwszym kolejnym dniu sesyjnym."""
    if not series:
        return None
    for pt in series:
        if pt["date"] >= target_date:
            return pt["date"], pt["close"]
    last = series[-1]
    return last["date"], last["close"]


class PortfolioTracker:
    """
    Realny silnik Paper Trading (wirtualny kapitał) z Money Management:
    - Stały kapitał początkowy, wolna gotówka, zrealizowany i niezrealizowany P&L
    - Reguły MM: wielkość pozycji %, max ekspozycja na 1 spółkę %, max liczba pozycji, rezerwa gotówki %, SL/TP, prowizja
    - Pełny dziennik transakcji BUY/SELL oraz realna krzywa kapitału vs S&P 500 (^GSPC)
    """

    @classmethod
    def get_or_create_account(cls, db: Session) -> PaperAccountConfig:
        acc = db.query(PaperAccountConfig).filter(PaperAccountConfig.id == 1).first()
        if acc:
            return acc

        holdings = db.query(PortfolioHolding).all()
        invested = sum(h.entry_price * h.shares for h in holdings)
        initial_cap = max(100000.0, math.ceil(invested / 10000.0) * 10000.0 + 20000.0) if invested > 90000 else 100000.0
        cash = round(max(initial_cap - invested, 0.0), 2)

        acc = PaperAccountConfig(
            id=1,
            initial_capital=initial_cap,
            cash_balance=cash,
            realized_pnl=0.0,
            default_position_pct=10.0,
            max_position_pct=20.0,
            max_positions=15,
            min_cash_reserve_pct=10.0,
            default_stop_loss_pct=15.0,
            default_take_profit_pct=35.0,
            commission_pct=0.0,
            allow_fractional_shares=True,
            updated_at=datetime.utcnow(),
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        return acc

    @classmethod
    def update_mm_settings(cls, db: Session, updates: Dict[str, Any]) -> PaperAccountConfig:
        acc = cls.get_or_create_account(db)

        if updates.get("initial_capital") is not None:
            new_cap = max(float(updates["initial_capital"]), 1000.0)
            delta = new_cap - acc.initial_capital
            acc.initial_capital = round(new_cap, 2)
            acc.cash_balance = round(max(acc.cash_balance + delta, 0.0), 2)

        if updates.get("default_position_pct") is not None:
            acc.default_position_pct = min(max(float(updates["default_position_pct"]), 1.0), 100.0)
        if updates.get("max_position_pct") is not None:
            acc.max_position_pct = min(max(float(updates["max_position_pct"]), 1.0), 100.0)
        if updates.get("max_positions") is not None:
            acc.max_positions = min(max(int(updates["max_positions"]), 1), 100)
        if updates.get("min_cash_reserve_pct") is not None:
            acc.min_cash_reserve_pct = min(max(float(updates["min_cash_reserve_pct"]), 0.0), 90.0)
        if updates.get("default_stop_loss_pct") is not None:
            acc.default_stop_loss_pct = min(max(float(updates["default_stop_loss_pct"]), 0.0), 80.0)
        if updates.get("default_take_profit_pct") is not None:
            acc.default_take_profit_pct = min(max(float(updates["default_take_profit_pct"]), 0.0), 500.0)
        if updates.get("commission_pct") is not None:
            acc.commission_pct = min(max(float(updates["commission_pct"]), 0.0), 5.0)
        if updates.get("allow_fractional_shares") is not None:
            acc.allow_fractional_shares = bool(updates["allow_fractional_shares"])

        acc.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(acc)
        return acc

    @classmethod
    def reset_account(cls, db: Session, initial_capital: Optional[float] = None) -> PaperAccountConfig:
        """Resetuje konto Paper Trading do 100% czystej gotówki (0 pozycji, czysta historia zleceń)."""
        acc = cls.get_or_create_account(db)
        cap = round(max(float(initial_capital), 1000.0), 2) if initial_capital else acc.initial_capital

        db.query(PortfolioHolding).delete()
        db.query(PortfolioSnapshot).delete()
        db.query(PaperTrade).delete()

        acc.initial_capital = cap
        acc.cash_balance = cap
        acc.realized_pnl = 0.0
        acc.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(acc)
        return acc

    @classmethod
    def _recalc_weights(cls, db: Session, acc: PaperAccountConfig) -> float:
        holdings = db.query(PortfolioHolding).all()
        market_val = sum(h.current_price * h.shares for h in holdings)
        total_equity = market_val + acc.cash_balance
        if total_equity > 0:
            for h in holdings:
                h.weight_pct = round((h.current_price * h.shares / total_equity) * 100.0, 1)
        return total_equity

    @classmethod
    def buy_position(
        cls,
        db: Session,
        ticker: str,
        amount_usd: Optional[float] = None,
        shares: Optional[float] = None,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        provider_name: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Wykonuje wirtualne zlecenie KUP z pełną walidacją zasad Money Management."""
        acc = cls.get_or_create_account(db)
        provider = get_market_provider(provider_name)
        fund_data = provider.get_ticker_data(ticker)
        if not fund_data or fund_data.current_price <= 0:
            raise ValueError(f"Nie znaleziono aktualnych danych rynkowych dla {ticker.upper()}.")

        price = round(fund_data.current_price, 2)
        holdings = db.query(PortfolioHolding).all()
        market_val = sum(h.current_price * h.shares for h in holdings)
        total_equity = market_val + acc.cash_balance
        existing = next((h for h in holdings if h.ticker == fund_data.ticker), None)

        # 1. Walidacja maksymalnej liczby pozycji (tylko dla nowej spółki)
        if existing is None and len(holdings) >= acc.max_positions:
            raise ValueError(
                f"Limit MM: masz już {len(holdings)}/{acc.max_positions} otwartych pozycji. Zamknij jedną lub zwiększ limit w ustawieniach MM."
            )

        # 2. Wyliczenie wielkości zlecenia
        min_reserve_usd = total_equity * (acc.min_cash_reserve_pct / 100.0)
        investable_cash = max(acc.cash_balance - min_reserve_usd, 0.0)

        if shares is not None and shares > 0:
            qty = float(shares)
            if not acc.allow_fractional_shares:
                qty = float(math.floor(qty))
            gross_val = round(qty * price, 2)
        else:
            if amount_usd is not None and amount_usd > 0:
                target_usd = float(amount_usd)
            else:
                target_usd = total_equity * (acc.default_position_pct / 100.0)
                target_usd = min(target_usd, investable_cash)

            if acc.allow_fractional_shares:
                qty = round(target_usd / price, 4)
            else:
                qty = float(math.floor(target_usd / price))
            gross_val = round(qty * price, 2)

        if qty <= 0 or gross_val <= 0:
            raise ValueError(
                f"Zbyt mała kwota na zakup (kurs ${price:.2f}, dostępna gotówka ponad rezerwę MM: ${investable_cash:,.2f})."
            )

        commission = round(gross_val * (acc.commission_pct / 100.0), 2)
        total_cost = round(gross_val + commission, 2)

        # 3. Walidacja gotówki i rezerwy gotówkowej MM
        if total_cost > acc.cash_balance + 0.01:
            raise ValueError(
                f"Niewystarczająca gotówka: potrzebujesz ${total_cost:,.2f}, dostępne saldo to ${acc.cash_balance:,.2f}."
            )

        cash_after = acc.cash_balance - total_cost
        if cash_after + 0.01 < min_reserve_usd and acc.min_cash_reserve_pct > 0:
            raise ValueError(
                f"Naruszenie rezerwy MM ({acc.min_cash_reserve_pct}% = ${min_reserve_usd:,.2f}). "
                f"Maksymalnie możesz teraz zainwestować ${investable_cash:,.2f}."
            )

        # 4. Walidacja maksymalnej ekspozycji na 1 spółkę
        existing_val = (existing.current_price * existing.shares) if existing else 0.0
        new_pos_pct = ((existing_val + gross_val) / total_equity) * 100.0 if total_equity > 0 else 100.0
        if new_pos_pct > acc.max_position_pct + 0.25:
            max_add = max((total_equity * acc.max_position_pct / 100.0) - existing_val, 0.0)
            raise ValueError(
                f"Limit MM: pozycja w {fund_data.ticker} osiągnęłaby {new_pos_pct:.1f}% portfela (limit: {acc.max_position_pct}%). "
                f"Możesz dokupić max za ${max_add:,.2f}."
            )

        eval_res = BuffettCalculator.evaluate(fund_data)
        sp500_level = provider.get_sp500_current()

        sl_pct = acc.default_stop_loss_pct if stop_loss_pct is None else float(stop_loss_pct)
        tp_pct = acc.default_take_profit_pct if take_profit_pct is None else float(take_profit_pct)

        if existing:
            new_total_shares = round(existing.shares + qty, 4)
            weighted_entry = ((existing.entry_price * existing.shares) + gross_val) / new_total_shares
            existing.shares = new_total_shares
            existing.entry_price = round(weighted_entry, 2)
            existing.current_price = price
            existing.intrinsic_value = eval_res["intrinsic_value"]
            existing.target_price = eval_res["intrinsic_value"]
            existing.pnl_cash = round((price - existing.entry_price) * new_total_shares, 2)
            existing.pnl_pct = round(((price - existing.entry_price) / existing.entry_price) * 100.0, 2)
            existing.stop_loss_price = round(existing.entry_price * (1 - sl_pct / 100.0), 2) if sl_pct > 0 else None
            existing.take_profit_price = round(existing.entry_price * (1 + tp_pct / 100.0), 2) if tp_pct > 0 else None
            holding = existing
            action_label = "Dokupiono"
        else:
            sl_price = round(price * (1 - sl_pct / 100.0), 2) if sl_pct > 0 else None
            tp_price = round(price * (1 + tp_pct / 100.0), 2) if tp_pct > 0 else None
            holding = PortfolioHolding(
                ticker=fund_data.ticker,
                company_name=fund_data.company_name,
                shares=qty,
                entry_date=datetime.utcnow(),
                entry_price=price,
                current_price=price,
                target_price=eval_res["intrinsic_value"],
                intrinsic_value=eval_res["intrinsic_value"],
                pnl_pct=0.0,
                pnl_cash=0.0,
                weight_pct=round(new_pos_pct, 1),
                benchmark_sp500_entry=round(sp500_level, 2) if sp500_level > 0 else 5800.0,
                benchmark_sp500_current=round(sp500_level, 2) if sp500_level > 0 else 5800.0,
                benchmark_pnl_pct=0.0,
                stop_loss_price=sl_price,
                take_profit_price=tp_price,
                status="ACTIVE",
            )
            db.add(holding)
            action_label = "Kupiono"

        acc.cash_balance = round(acc.cash_balance - total_cost, 2)
        acc.updated_at = datetime.utcnow()

        trade = PaperTrade(
            ticker=fund_data.ticker,
            company_name=fund_data.company_name,
            side="BUY",
            shares=qty,
            price=price,
            gross_value=gross_val,
            commission=commission,
            note=note or f"{action_label} wg MM (waga ~{new_pos_pct:.1f}%)",
            executed_at=datetime.utcnow(),
        )
        db.add(trade)

        # Zapisz także sygnał audytowy
        oe_yield = (
            round((eval_res["owner_earnings_ttm"] * 1e6 / fund_data.market_cap) * 100, 2)
            if fund_data.market_cap > 0
            else 0.0
        )
        db.add(
            Signal(
                ticker=fund_data.ticker,
                company_name=fund_data.company_name,
                sector=fund_data.sector,
                entry_price=price,
                intrinsic_value=eval_res["intrinsic_value"],
                margin_of_safety_pct=eval_res["margin_of_safety_pct"],
                recommendation=eval_res["recommendation"],
                buffett_score=eval_res["buffett_score"],
                rule_number_one_risk=eval_res["rule_number_one_risk"],
                roic_pct=fund_data.roic_pct,
                roe_pct=fund_data.roe_pct,
                gross_margin_pct=fund_data.gross_margin_pct,
                net_debt_to_fcf=fund_data.net_debt_to_fcf,
                pe_ratio=fund_data.pe_ratio,
                owner_earnings_yield_pct=oe_yield,
                ai_thesis=f"Zlecenie Paper Trading: {action_label} {qty} akcji po ${price:.2f} (${gross_val:,.2f}).",
                ai_moat_analysis=f"ROIC {fund_data.roic_pct}%, Marża brutto {fund_data.gross_margin_pct}%.",
                ai_risks=f"Net Debt/FCF: {fund_data.net_debt_to_fcf}x, Reguła 1: {eval_res['rule_number_one_risk']}.",
            )
        )

        db.flush()
        cls._recalc_weights(db, acc)
        db.commit()

        return {
            "status": "SUCCESS",
            "message": f"{action_label} {qty} akcji {fund_data.ticker} po ${price:.2f} (wartość ${gross_val:,.2f}). Pozostała gotówka: ${acc.cash_balance:,.2f}.",
            "trade": {
                "ticker": fund_data.ticker,
                "side": "BUY",
                "shares": qty,
                "price": price,
                "gross_value": gross_val,
                "commission": commission,
            },
            "cash_balance": acc.cash_balance,
        }

    @classmethod
    def sell_position(
        cls,
        db: Session,
        holding_id: int,
        shares: Optional[float] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Sprzedaje całą lub część pozycji, zwraca gotówkę na saldo i zapisuje zrealizowany P&L."""
        acc = cls.get_or_create_account(db)
        holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
        if not holding:
            raise ValueError("Pozycja nie została znaleziona.")

        # Pobierz możliwie najświeższą cenę
        provider = get_market_provider()
        fund = provider.get_ticker_data(holding.ticker)
        sell_price = round(fund.current_price, 2) if (fund and fund.current_price > 0) else holding.current_price

        qty_to_sell = holding.shares if (shares is None or shares >= holding.shares) else float(shares)
        if qty_to_sell <= 0:
            raise ValueError("Liczba akcji do sprzedaży musi być dodatnia.")

        gross_val = round(qty_to_sell * sell_price, 2)
        commission = round(gross_val * (acc.commission_pct / 100.0), 2)
        cost_basis = round(qty_to_sell * holding.entry_price, 2)
        realized_pnl = round(gross_val - cost_basis - commission, 2)
        realized_pnl_pct = round((realized_pnl / cost_basis) * 100.0, 2) if cost_basis > 0 else 0.0

        acc.cash_balance = round(acc.cash_balance + gross_val - commission, 2)
        acc.realized_pnl = round(acc.realized_pnl + realized_pnl, 2)
        acc.updated_at = datetime.utcnow()

        ticker = holding.ticker
        company_name = holding.company_name

        if qty_to_sell >= holding.shares - 1e-6:
            db.delete(holding)
            action_desc = "Zamknięto całą pozycję"
        else:
            holding.shares = round(holding.shares - qty_to_sell, 4)
            holding.current_price = sell_price
            holding.pnl_cash = round((sell_price - holding.entry_price) * holding.shares, 2)
            holding.pnl_pct = round(((sell_price - holding.entry_price) / holding.entry_price) * 100.0, 2)
            action_desc = f"Sprzedano część ({qty_to_sell} akcji)"

        trade = PaperTrade(
            ticker=ticker,
            company_name=company_name,
            side="SELL",
            shares=qty_to_sell,
            price=sell_price,
            gross_value=gross_val,
            commission=commission,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            note=note or action_desc,
            executed_at=datetime.utcnow(),
        )
        db.add(trade)
        db.flush()
        cls._recalc_weights(db, acc)
        db.commit()

        return {
            "status": "SOLD",
            "message": f"{action_desc} {ticker} po ${sell_price:.2f}. Zrealizowany P&L: {'+' if realized_pnl >= 0 else ''}${realized_pnl:,.2f} ({realized_pnl_pct:+.2f}%).",
            "realized_pnl": realized_pnl,
            "cash_balance": acc.cash_balance,
        }

    @classmethod
    def seed_initial_demo_portfolio(cls, db: Session, force: bool = False):
        """Inicjalizuje portfel Paper Trading z realnym MM (domyślny kapitał $100,000, równe alokacje po $10,000)."""
        ensure_portfolio_schema()
        acc = cls.get_or_create_account(db)

        if not force and db.query(PortfolioHolding).count() > 0:
            return

        if force:
            db.query(PortfolioHolding).delete()
            db.query(PortfolioSnapshot).delete()
            db.query(PaperTrade).delete()
            db.query(Signal).delete()
            acc.cash_balance = acc.initial_capital
            acc.realized_pnl = 0.0
            db.commit()

        provider = get_market_provider()
        # Równe alokacje wg MM (domyślnie po 10% kapitału = $10,000 na każdą pozycję)
        alloc_usd = acc.initial_capital * (acc.default_position_pct / 100.0)
        seed_plan = [
            ("BRK.B", 90),
            ("AAPL", 75),
            ("KO", 60),
            ("GOOGL", 45),
        ]
        tickers = [t for t, _ in seed_plan]
        hist_map = provider.get_historical_prices(tickers + ["^GSPC"], days=100)
        sp_series = hist_map.get("^GSPC", [])
        sp500_current = sp_series[-1]["close"] if sp_series else provider.get_sp500_current()

        now = datetime.utcnow()
        created_holdings: List[PortfolioHolding] = []
        spent_total = 0.0

        for ticker, days_ago in seed_plan:
            fund_data = provider.get_ticker_data(ticker)
            if not fund_data:
                continue

            eval_res = BuffettCalculator.evaluate(fund_data)
            target_dt = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")

            t_series = hist_map.get(ticker, [])
            entry_info = _find_price_on_or_after(t_series, target_dt)
            if entry_info:
                entry_date_str, entry_p = entry_info
                entry_dt = datetime.strptime(entry_date_str, "%Y-%m-%d")
            else:
                entry_date_str = target_dt
                entry_dt = now - timedelta(days=days_ago)
                entry_p = fund_data.current_price

            if entry_p <= 0:
                continue

            shares = round(alloc_usd / entry_p, 4) if acc.allow_fractional_shares else float(math.floor(alloc_usd / entry_p))
            if shares <= 0:
                continue

            gross_entry = round(shares * entry_p, 2)
            spent_total += gross_entry

            sp_entry_info = _find_price_on_or_after(sp_series, entry_date_str)
            sp_entry = sp_entry_info[1] if sp_entry_info else sp500_current

            cur_price = fund_data.current_price
            pnl_pct = round(((cur_price - entry_p) / entry_p) * 100, 2) if entry_p > 0 else 0.0
            benchmark_pnl = round(((sp500_current - sp_entry) / sp_entry) * 100, 2) if sp_entry > 0 else 0.0

            sl_price = round(entry_p * (1 - acc.default_stop_loss_pct / 100.0), 2) if acc.default_stop_loss_pct > 0 else None
            tp_price = round(entry_p * (1 + acc.default_take_profit_pct / 100.0), 2) if acc.default_take_profit_pct > 0 else None

            holding = PortfolioHolding(
                ticker=ticker,
                company_name=fund_data.company_name,
                shares=shares,
                entry_date=entry_dt,
                entry_price=round(entry_p, 2),
                current_price=round(cur_price, 2),
                target_price=eval_res["intrinsic_value"],
                intrinsic_value=eval_res["intrinsic_value"],
                pnl_pct=pnl_pct,
                pnl_cash=round((cur_price - entry_p) * shares, 2),
                weight_pct=acc.default_position_pct,
                benchmark_sp500_entry=round(sp_entry, 2),
                benchmark_sp500_current=round(sp500_current, 2),
                benchmark_pnl_pct=benchmark_pnl,
                stop_loss_price=sl_price,
                take_profit_price=tp_price,
                status="ACTIVE",
            )
            db.add(holding)
            created_holdings.append(holding)

            db.add(
                PaperTrade(
                    ticker=ticker,
                    company_name=fund_data.company_name,
                    side="BUY",
                    shares=shares,
                    price=round(entry_p, 2),
                    gross_value=gross_entry,
                    commission=0.0,
                    note=f"Startowa alokacja MM ({acc.default_position_pct:.0f}% kapitału)",
                    executed_at=entry_dt,
                )
            )

        acc.cash_balance = round(max(acc.initial_capital - spent_total, 0.0), 2)
        db.flush()
        cls._recalc_weights(db, acc)
        cls._rebuild_real_equity_curve(db, created_holdings, hist_map, acc)
        db.commit()

    @classmethod
    def _rebuild_real_equity_curve(
        cls,
        db: Session,
        holdings: List[PortfolioHolding],
        hist_map: Dict[str, List[Dict[str, Any]]],
        acc: Optional[PaperAccountConfig] = None,
    ) -> None:
        """Buduje realną krzywą zwrotu portfela i S&P 500 na bazie dziennych cen zamknięcia."""
        db.query(PortfolioSnapshot).delete()
        sp_series = hist_map.get("^GSPC", [])
        if not holdings or not sp_series:
            return

        earliest_entry = min(h.entry_date.strftime("%Y-%m-%d") for h in holdings)
        sp_filtered = [pt for pt in sp_series if pt["date"] >= earliest_entry]
        if not sp_filtered:
            return

        price_lookup: Dict[str, Dict[str, float]] = {}
        for h in holdings:
            price_lookup[h.ticker] = {pt["date"]: pt["close"] for pt in hist_map.get(h.ticker, [])}

        sp_base = sp_filtered[0]["close"]
        step = max(len(sp_filtered) // 20, 1)
        sampled = sp_filtered[::step]
        if sampled[-1]["date"] != sp_filtered[-1]["date"]:
            sampled.append(sp_filtered[-1])

        last_known_price: Dict[str, float] = {h.ticker: h.entry_price for h in holdings}

        for pt in sampled:
            d_str = pt["date"]
            sp_close = pt["close"]
            sp_ret = round(((sp_close - sp_base) / sp_base) * 100, 2) if sp_base > 0 else 0.0

            port_cost = 0.0
            port_val = 0.0
            active_cnt = 0

            for h in holdings:
                h_entry_str = h.entry_date.strftime("%Y-%m-%d")
                if d_str < h_entry_str:
                    continue
                active_cnt += 1
                t_prices = price_lookup.get(h.ticker, {})
                if d_str in t_prices:
                    last_known_price[h.ticker] = t_prices[d_str]
                else:
                    prior = [v for k, v in t_prices.items() if k <= d_str]
                    if prior:
                        last_known_price[h.ticker] = prior[-1]

                port_cost += h.entry_price * h.shares
                port_val += last_known_price[h.ticker] * h.shares

            if port_cost <= 0:
                continue

            port_ret = round(((port_val - port_cost) / port_cost) * 100, 2)
            snap = PortfolioSnapshot(
                snapshot_date=datetime.strptime(d_str, "%Y-%m-%d"),
                total_portfolio_value=round(port_val + (acc.cash_balance if acc else 0.0), 2),
                cash_balance=round(acc.cash_balance, 2) if acc else 0.0,
                cumulative_return_pct=port_ret,
                benchmark_sp500_return_pct=sp_ret,
                alpha_pct=round(port_ret - sp_ret, 2),
                active_positions_count=active_cnt,
            )
            db.add(snap)

    @classmethod
    def refresh_portfolio(cls, db: Session, force: bool = False) -> bool:
        """Odświeża aktualne ceny wszystkich pozycji oraz benchmark S&P 500 z aktywnego dostawcy."""
        global _LAST_REFRESH_TS
        now = time.time()
        if not force and (now - _LAST_REFRESH_TS) < REFRESH_COOLDOWN_SEC:
            return False

        acc = cls.get_or_create_account(db)
        holdings = db.query(PortfolioHolding).all()
        if not holdings:
            return False

        provider = get_market_provider()
        sp500_current = provider.get_sp500_current()

        for h in holdings:
            fund_data = provider.get_ticker_data(h.ticker)
            if not fund_data:
                continue

            eval_res = BuffettCalculator.evaluate(fund_data)
            h.current_price = round(fund_data.current_price, 2)
            h.intrinsic_value = eval_res["intrinsic_value"]
            h.target_price = eval_res["intrinsic_value"]
            h.pnl_cash = round((h.current_price - h.entry_price) * h.shares, 2)
            h.pnl_pct = round(((h.current_price - h.entry_price) / h.entry_price) * 100, 2) if h.entry_price > 0 else 0.0
            if sp500_current > 0:
                h.benchmark_sp500_current = round(sp500_current, 2)
                if h.benchmark_sp500_entry > 0:
                    h.benchmark_pnl_pct = round(
                        ((sp500_current - h.benchmark_sp500_entry) / h.benchmark_sp500_entry) * 100, 2
                    )

        cls._recalc_weights(db, acc)

        tickers = [h.ticker for h in holdings]
        hist_map = provider.get_historical_prices(tickers + ["^GSPC"], days=100)
        if hist_map.get("^GSPC"):
            cls._rebuild_real_equity_curve(db, holdings, hist_map, acc)

        db.commit()
        _LAST_REFRESH_TS = now
        return True

    @classmethod
    def get_portfolio_summary(cls, db: Session, force_refresh: bool = False) -> Dict[str, Any]:
        ensure_portfolio_schema()
        acc = cls.get_or_create_account(db)
        cls.refresh_portfolio(db, force=force_refresh)

        holdings = db.query(PortfolioHolding).all()
        snapshots = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date.asc()).all()
        trades = db.query(PaperTrade).order_by(PaperTrade.executed_at.desc()).limit(30).all()

        market_val = round(sum(h.current_price * h.shares for h in holdings), 2)
        invested_cost = round(sum(h.entry_price * h.shares for h in holdings), 2)
        cash_balance = round(acc.cash_balance, 2)
        total_equity = round(market_val + cash_balance, 2)
        cash_pct = round((cash_balance / total_equity) * 100.0, 1) if total_equity > 0 else 100.0

        unrealized_pnl = round(market_val - invested_cost, 2)
        realized_pnl = round(acc.realized_pnl, 2)
        total_pnl_cash = round(total_equity - acc.initial_capital, 2)
        total_pnl_pct = round((total_pnl_cash / acc.initial_capital) * 100.0, 2) if acc.initial_capital > 0 else 0.0

        avg_sp_pnl = round(sum(h.benchmark_pnl_pct for h in holdings) / len(holdings), 2) if holdings else 0.0
        alpha = round(total_pnl_pct - avg_sp_pnl, 2)

        min_reserve_usd = round(total_equity * (acc.min_cash_reserve_pct / 100.0), 2)
        investable_cash = round(max(cash_balance - min_reserve_usd, 0.0), 2)
        suggested_order = round(min(total_equity * (acc.default_position_pct / 100.0), investable_cash), 2)

        # Weryfikacja zgodności z Regułą 1
        high_risk_count = 0
        for h in holdings:
            sig = (
                db.query(Signal)
                .filter(Signal.ticker == h.ticker)
                .order_by(Signal.created_at.desc())
                .first()
            )
            if sig and sig.rule_number_one_risk == "HIGH":
                high_risk_count += 1

        if not holdings:
            rule_1_compliance = "100% gotówka — brak otwartego ryzyka"
        elif high_risk_count == 0:
            rule_1_compliance = f"100% ({len(holdings)}/{len(holdings)}) — Żadna pozycja nie ma wysokiego ryzyka"
        else:
            ok_cnt = len(holdings) - high_risk_count
            pct = round((ok_cnt / len(holdings)) * 100)
            rule_1_compliance = f"{pct}% ({ok_cnt}/{len(holdings)}) — {high_risk_count} poz. wymaga uwagi"

        holdings_out = []
        for h in holdings:
            m_val = round(h.current_price * h.shares, 2)
            c_val = round(h.entry_price * h.shares, 2)
            w_pct = round((m_val / total_equity) * 100.0, 1) if total_equity > 0 else 0.0
            holdings_out.append({
                "id": h.id,
                "ticker": h.ticker,
                "company_name": h.company_name,
                "shares": h.shares,
                "entry_date": h.entry_date.strftime("%Y-%m-%d") if h.entry_date else None,
                "entry_price": h.entry_price,
                "current_price": h.current_price,
                "intrinsic_value": h.intrinsic_value,
                "invested_value": c_val,
                "market_value": m_val,
                "weight_pct": w_pct,
                "pnl_cash": round(m_val - c_val, 2),
                "pnl_pct": h.pnl_pct,
                "benchmark_pnl_pct": h.benchmark_pnl_pct,
                "stop_loss_price": h.stop_loss_price,
                "take_profit_price": h.take_profit_price,
                "sl_triggered": bool(h.stop_loss_price and h.current_price <= h.stop_loss_price),
                "tp_triggered": bool(h.take_profit_price and h.current_price >= h.take_profit_price),
                "status": h.status,
            })

        return {
            "initial_capital": round(acc.initial_capital, 2),
            "total_portfolio_value": total_equity,
            "market_value": market_val,
            "cash_balance": cash_balance,
            "cash_pct": cash_pct,
            "total_invested": invested_cost,
            "unrealized_pnl_cash": unrealized_pnl,
            "realized_pnl_cash": realized_pnl,
            "total_pnl_cash": total_pnl_cash,
            "total_pnl_pct": total_pnl_pct,
            "benchmark_sp500_pnl_pct": avg_sp_pnl,
            "alpha_pct": alpha,
            "positions_count": len(holdings),
            "rule_1_compliance": rule_1_compliance,
            "data_source": settings.DATA_PROVIDER,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "mm_config": {
                "initial_capital": acc.initial_capital,
                "default_position_pct": acc.default_position_pct,
                "max_position_pct": acc.max_position_pct,
                "max_positions": acc.max_positions,
                "min_cash_reserve_pct": acc.min_cash_reserve_pct,
                "default_stop_loss_pct": acc.default_stop_loss_pct,
                "default_take_profit_pct": acc.default_take_profit_pct,
                "commission_pct": acc.commission_pct,
                "allow_fractional_shares": acc.allow_fractional_shares,
                "min_reserve_usd": min_reserve_usd,
                "investable_cash_usd": investable_cash,
                "suggested_order_usd": suggested_order,
            },
            "holdings": holdings_out,
            "trades": [
                {
                    "id": t.id,
                    "ticker": t.ticker,
                    "company_name": t.company_name,
                    "side": t.side,
                    "shares": t.shares,
                    "price": t.price,
                    "gross_value": t.gross_value,
                    "commission": t.commission,
                    "realized_pnl": t.realized_pnl,
                    "realized_pnl_pct": t.realized_pnl_pct,
                    "note": t.note,
                    "executed_at": t.executed_at.strftime("%Y-%m-%d %H:%M") if t.executed_at else "",
                }
                for t in trades
            ],
            "equity_curve": [
                {
                    "date": s.snapshot_date.strftime("%Y-%m-%d"),
                    "portfolio_return": s.cumulative_return_pct,
                    "benchmark_return": s.benchmark_sp500_return_pct,
                    "alpha": s.alpha_pct,
                }
                for s in snapshots
            ],
        }
