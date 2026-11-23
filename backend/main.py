import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.db import Base, engine, SessionLocal
from app.services.portfolio_tracker import PortfolioTracker
from app.services.market_scanner import MarketScanner
from app.routers import screener, analysis, portfolio, settings as settings_router

# Inicjalizacja schematu bazy danych (w tym tabel skanera i alertów)
Base.metadata.create_all(bind=engine)

# Inicjalizacja przykładowego portfela demonstracyjnego do forward-testów
db = SessionLocal()
try:
    PortfolioTracker.seed_initial_demo_portfolio(db)
finally:
    db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Harmonogram w tle: automatyczny skan EOD po zamknięciu sesji USA + alerty intraday w trakcie sesji
    scheduler_task = asyncio.create_task(MarketScanner.scheduler_loop())
    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_MOTTO,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS dla frontendu
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dołączanie routerów
app.include_router(screener.router)
app.include_router(analysis.router)
app.include_router(portfolio.router)
app.include_router(settings_router.router)


@app.get("/")
def health_check():
    return {
        "app": settings.PROJECT_NAME,
        "motto": settings.PROJECT_MOTTO,
        "status": "ONLINE",
        "version": settings.VERSION,
        "market_session": MarketScanner.get_market_session_info(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
