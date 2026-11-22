from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.db import Base, engine, SessionLocal
from app.services.portfolio_tracker import PortfolioTracker
from app.routers import screener, analysis, portfolio, settings as settings_router

# Inicjalizacja schematu bazy danych
Base.metadata.create_all(bind=engine)

# Inicjalizacja przykładowego portfela demonstracyjnego do forward-testów
db = SessionLocal()
try:
    PortfolioTracker.seed_initial_demo_portfolio(db)
finally:
    db.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_MOTTO,
    version=settings.VERSION
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
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
