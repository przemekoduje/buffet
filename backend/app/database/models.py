from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from app.database.db import Base

class Signal(Base):
    """Przechowuje wygenerowane predykcje i rekomendacje Buffetta."""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    company_name = Column(String(100), nullable=False)
    sector = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Ceny w momencie sygnału
    entry_price = Column(Float, nullable=False)
    intrinsic_value = Column(Float, nullable=False)  # Wartość wewnętrzna wg DCF / Owner Earnings
    margin_of_safety_pct = Column(Float, nullable=False) # np. 28.5%
    recommendation = Column(String(30), nullable=False) # 'STRONG_BUY', 'BUY', 'HOLD', 'AVOID'
    buffett_score = Column(Integer, nullable=False) # 0 - 100
    rule_number_one_risk = Column(String(20), default="LOW") # LOW, MODERATE, HIGH
    
    # Metryki fundamentów
    roic_pct = Column(Float)
    roe_pct = Column(Float)
    gross_margin_pct = Column(Float)
    net_debt_to_fcf = Column(Float)
    pe_ratio = Column(Float)
    owner_earnings_yield_pct = Column(Float)
    
    # Analiza jakościowa AI
    ai_thesis = Column(Text) # Teza inwestycyjna
    ai_moat_analysis = Column(Text) # Analiza fosy ekonomicznej
    ai_risks = Column(Text) # Czynniki ryzyka (Reguła 1)

    # Status śledzenia demo
    is_active_demo = Column(Boolean, default=True)


class PortfolioHolding(Base):
    """Wirtualny portfel demonstracyjny (1-roczny audyt wyników)."""
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    company_name = Column(String(100), nullable=False)
    shares = Column(Float, default=1.0)
    entry_date = Column(DateTime, default=datetime.utcnow)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    intrinsic_value = Column(Float, nullable=False)
    pnl_pct = Column(Float, default=0.0)
    pnl_cash = Column(Float, default=0.0)
    weight_pct = Column(Float, default=0.0)
    benchmark_sp500_entry = Column(Float, default=5800.0)
    benchmark_sp500_current = Column(Float, default=5850.0)
    benchmark_pnl_pct = Column(Float, default=0.0)
    status = Column(String(20), default="ACTIVE") # ACTIVE, CLOSED_PROFIT, CLOSED_STOPLOSS


class PortfolioSnapshot(Base):
    """Codzienny snapshot portfela do wykresu equity vs S&P500."""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    total_portfolio_value = Column(Float, nullable=False)
    cash_balance = Column(Float, default=0.0)
    cumulative_return_pct = Column(Float, default=0.0)
    benchmark_sp500_return_pct = Column(Float, default=0.0)
    alpha_pct = Column(Float, default=0.0) # Przewaga nad S&P500
    active_positions_count = Column(Integer, default=0)
