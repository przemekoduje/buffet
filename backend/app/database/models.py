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
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    status = Column(String(20), default="ACTIVE") # ACTIVE, CLOSED_PROFIT, CLOSED_STOPLOSS


class PaperAccountConfig(Base):
    """Konfiguracja konta Paper Trading i zasad Money Management (wirtualny kapitał)."""
    __tablename__ = "paper_account_config"

    id = Column(Integer, primary_key=True, default=1)
    initial_capital = Column(Float, default=100000.0, nullable=False)
    cash_balance = Column(Float, default=100000.0, nullable=False)
    realized_pnl = Column(Float, default=0.0, nullable=False)
    default_position_pct = Column(Float, default=10.0, nullable=False)   # domyślna alokacja na 1 transakcję (%)
    max_position_pct = Column(Float, default=20.0, nullable=False)       # maksymalny udział 1 spółki (%)
    max_positions = Column(Integer, default=15, nullable=False)          # max liczba otwartych pozycji
    min_cash_reserve_pct = Column(Float, default=10.0, nullable=False)   # minimalna rezerwa gotówki (%)
    default_stop_loss_pct = Column(Float, default=15.0, nullable=False)  # 0 = brak SL
    default_take_profit_pct = Column(Float, default=35.0, nullable=False) # 0 = brak TP
    commission_pct = Column(Float, default=0.0, nullable=False)          # prowizja brokera (%)
    allow_fractional_shares = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PaperTrade(Base):
    """Dziennik zrealizowanych zleceń BUY / SELL na koncie Paper Trading."""
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    company_name = Column(String(120), nullable=False)
    side = Column(String(10), nullable=False)  # BUY / SELL
    shares = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    gross_value = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    realized_pnl = Column(Float, nullable=True)
    realized_pnl_pct = Column(Float, nullable=True)
    note = Column(String(240), default="")
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)


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


class MarketScanResult(Base):
    """Zapisany wynik skanowania rynku (EOD po zamknięciu sesji lub ręczny)."""
    __tablename__ = "market_scan_results"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    company_name = Column(String(120), nullable=False)
    sector = Column(String(60), default="General")
    industry = Column(String(80), default="General")
    baskets = Column(String(120), default="")  # np. "us_quality,dividend_aristocrats"

    current_price = Column(Float, nullable=False)
    intrinsic_value = Column(Float, nullable=False)
    margin_of_safety_pct = Column(Float, nullable=False)
    buffett_score = Column(Integer, nullable=False)
    recommendation = Column(String(30), nullable=False)
    rule_number_one_risk = Column(String(20), default="LOW")

    roic_pct = Column(Float, default=0.0)
    roe_pct = Column(Float, default=0.0)
    gross_margin_pct = Column(Float, default=0.0)
    net_debt_to_fcf = Column(Float, default=0.0)
    pe_ratio = Column(Float, default=0.0)
    dividend_yield_pct = Column(Float, default=0.0)
    source = Column(String(30), default="yfinance")

    scan_type = Column(String(20), default="EOD")  # EOD / MANUAL
    scanned_at = Column(DateTime, default=datetime.utcnow, index=True)


class MarketAlert(Base):
    """Alerty sesyjne (intraday) wykrywające ciekawe ruchy i okazje Buffetta."""
    __tablename__ = "market_alerts"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    company_name = Column(String(120), nullable=False)
    alert_type = Column(String(40), nullable=False)  # BUY_ZONE_DROP, INTRADAY_PULLBACK, INTRADAY_SURGE, VOLUME_SPIKE
    severity = Column(String(20), default="MEDIUM")  # HIGH, MEDIUM, INFO
    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    price = Column(Float, default=0.0)
    change_pct = Column(Float, default=0.0)
    volume_ratio = Column(Float, default=1.0)
    margin_of_safety_pct = Column(Float, default=0.0)
    buffett_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_read = Column(Boolean, default=False)
