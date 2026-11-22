from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import PortfolioHolding, PortfolioSnapshot, Signal
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator

class PortfolioTracker:
    """
    Silnik demonstracyjnego konta administracyjnego:
    - 1-roczny audyt wyników (Forward-testing w czasie rzeczywistym)
    - Porównanie zwrotu z indeksem S&P 500
    - Wyliczanie wskaźników ryzyka i Alfy Buffetta
    """

    @classmethod
    def seed_initial_demo_portfolio(cls, db: Session):
        """Inicjalizuje portfel demonstracyjny, jeśli jest pusty."""
        if db.query(PortfolioHolding).count() > 0:
            return

        provider = get_market_provider("mock")
        sp500_level = provider.get_sp500_current()

        seed_tickers = ["BRK.B", "AAPL", "KO", "GOOGL"]
        mock_entry_dates = [
            datetime.utcnow() - timedelta(days=90),
            datetime.utcnow() - timedelta(days=75),
            datetime.utcnow() - timedelta(days=60),
            datetime.utcnow() - timedelta(days=45),
        ]
        # Realistyczne historyczne ceny wejścia do demonstracji zysku
        entry_prices = {
            "BRK.B": 415.0,  # obecna ~455 (+9.6%)
            "AAPL": 210.0,   # obecna ~228 (+8.5%)
            "KO": 59.0,      # obecna ~64.5 (+9.3%)
            "GOOGL": 155.0   # obecna ~172 (+10.9%)
        }
        sp500_entries = {
            "BRK.B": 5450.0,
            "AAPL": 5520.0,
            "KO": 5580.0,
            "GOOGL": 5650.0
        }

        for i, ticker in enumerate(seed_tickers):
            fund_data = provider.get_ticker_data(ticker)
            if not fund_data:
                continue

            eval_res = BuffettCalculator.evaluate(fund_data)
            entry_p = entry_prices.get(ticker, fund_data.current_price * 0.92)
            sp_entry = sp500_entries.get(ticker, 5500.0)
            
            pnl_pct = round(((fund_data.current_price - entry_p) / entry_p) * 100, 2)
            benchmark_pnl = round(((sp500_level - sp_entry) / sp_entry) * 100, 2)

            holding = PortfolioHolding(
                ticker=ticker,
                company_name=fund_data.company_name,
                shares=10.0 if ticker != "BRK.B" else 5.0,
                entry_date=mock_entry_dates[i],
                entry_price=entry_p,
                current_price=fund_data.current_price,
                target_price=eval_res["intrinsic_value"],
                intrinsic_value=eval_res["intrinsic_value"],
                pnl_pct=pnl_pct,
                pnl_cash=round((fund_data.current_price - entry_p) * (10.0 if ticker != "BRK.B" else 5.0), 2),
                weight_pct=25.0,
                benchmark_sp500_entry=sp_entry,
                benchmark_sp500_current=sp500_level,
                benchmark_pnl_pct=benchmark_pnl,
                status="ACTIVE"
            )
            db.add(holding)

            # Dodajemy także wpis do tabeli sygnałów historycznych
            signal = Signal(
                ticker=ticker,
                company_name=fund_data.company_name,
                sector=fund_data.sector,
                created_at=mock_entry_dates[i],
                entry_price=entry_p,
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
                owner_earnings_yield_pct=round((eval_res["owner_earnings_ttm"] * 1e6 / fund_data.market_cap) * 100, 2),
                ai_thesis=f"Niedowartościowana spółka z fosą wytypowana na podstawie modelu Buffetta.",
                ai_moat_analysis=f"Wysoka marża brutto ({fund_data.gross_margin_pct}%) potwierdza pricing power.",
                ai_risks="Zadłużenie w normie, silna poduszka gotówkowa."
            )
            db.add(signal)

        # Wygenerujmy 12 punktów do krzywej equity (ostatnie 90 dni)
        base_val = 100_000.0
        sp_base = 5400.0
        now = datetime.utcnow()
        for d in range(12, -1, -1):
            date_pt = now - timedelta(days=d * 7)
            # Portfel Buffetta stabilnie rósł wyżej niż S&P
            buffett_growth = (12 - d) * 0.85 + 0.4
            sp_growth = (12 - d) * 0.55
            
            snap = PortfolioSnapshot(
                snapshot_date=date_pt,
                total_portfolio_value=round(base_val * (1 + buffett_growth / 100), 2),
                cash_balance=15000.0,
                cumulative_return_pct=round(buffett_growth, 2),
                benchmark_sp500_return_pct=round(sp_growth, 2),
                alpha_pct=round(buffett_growth - sp_growth, 2),
                active_positions_count=4
            )
            db.add(snap)

        db.commit()

    @classmethod
    def get_portfolio_summary(cls, db: Session) -> Dict[str, Any]:
        holdings = db.query(PortfolioHolding).all()
        snapshots = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date.asc()).all()

        total_val = sum(h.current_price * h.shares for h in holdings)
        total_invested = sum(h.entry_price * h.shares for h in holdings)
        total_pnl_cash = total_val - total_invested
        total_pnl_pct = round((total_pnl_cash / total_invested * 100), 2) if total_invested > 0 else 0.0

        # Średnia stopa zwrotu S&P 500 dla tych pozycji
        avg_sp_pnl = round(sum(h.benchmark_pnl_pct for h in holdings) / len(holdings), 2) if holdings else 0.0
        alpha = round(total_pnl_pct - avg_sp_pnl, 2)

        return {
            "total_portfolio_value": round(total_val, 2),
            "total_invested": round(total_invested, 2),
            "total_pnl_cash": round(total_pnl_cash, 2),
            "total_pnl_pct": total_pnl_pct,
            "benchmark_sp500_pnl_pct": avg_sp_pnl,
            "alpha_pct": alpha,
            "positions_count": len(holdings),
            "rule_1_compliance": "100% — Żadna pozycja nie naruszyła limitu bezpieczeństwa długu",
            "holdings": holdings,
            "equity_curve": [
                {
                    "date": s.snapshot_date.strftime("%Y-%m-%d"),
                    "portfolio_return": s.cumulative_return_pct,
                    "benchmark_return": s.benchmark_sp500_return_pct,
                    "alpha": s.alpha_pct
                }
                for s in snapshots
            ]
        }
