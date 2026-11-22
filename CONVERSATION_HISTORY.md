# Historia Konwersacji & Kontekst Projektu BUFFET
> Data utworzenia: 2026-11-22  
> Moduł: 4. część ekosystemu **przemokoduje.com**  
> Repozytorium: [https://github.com/przemekoduje/buffet.git](https://github.com/przemekoduje/buffet.git)  
> Główne motto: **„Reguła nr 1: Nigdy nie trać pieniędzy. Reguła nr 2: Zawsze pamiętaj o punkcie pierwszym.”** — Warren Buffett

---

## 1. Cel i Wymagania Użytkownika

1. **Idea projektu**:
   Narzędzie analityczne na wzór filozofii Warrena Buffetta i Charliego Mungera, które analizuje spółki giełdowe i wskazuje te niedoszacowane (posiadające margines bezpieczeństwa, trwałą fosę ekonomiczną oraz bezpieczny bilans).
2. **Konto demonstracyjne / Audyt 1-roczny**:
   Demonstracyjne konto administracyjne, w którym przez rok w czasie rzeczywistym (forward-testing) weryfikowana jest skuteczność predykcji i sygnałów generowanych przez model vs benchmark S&P 500.
3. **Założenie architektoniczne**:
   Panel administratora, interfejs i silnik obliczeniowy we wszystkich wersjach wyglądają i działają identycznie. Różnica polega wyłącznie na podpiętym dostawcy danych rynkowych (Adapter Pattern):
   - **Wersja darmowa / Mock**: 0 zł (wbudowane zweryfikowane spółki lub open API yfinance).
   - **Wersja średnia (rekomendowana)**: ~$19–29/mc (Financial Modeling Prep API — 30 lat znormalizowanych danych, transkrypty z zarządem).
   - **Wersja wypasiona**: Institutional grade (wieloagentowa analiza Monte Carlo, alternatywne zbiory danych, bezpośrednie broker API).
4. **Design**:
   Bardzo minimalistyczny, jasny, elegancki, zorientowany na dane finansowe i typografię.

---

## 2. Zrealizowana Architektura

### Backend (Python / FastAPI / SQLite / SQLAlchemy)
- `backend/app/config.py`: Konfiguracja środowiska, kluczy API, wyboru aktywnego dostawcy danych.
- `backend/app/database/models.py`:
  - `Signal`: Zapisywane z timestampem sygnały i wyceny (niezmienna historia decyzji).
  - `PortfolioHolding`: Pozycje w 1-rocznym portfelu demonstracyjnym wraz z kursem wejścia, wyceną DCF i P&L.
  - `PortfolioSnapshot`: Codzienne punkty do wykresu krzywej kapitału (Equity Curve vs S&P 500).
- `backend/app/providers/`:
  - `base.py`: Klasa bazowa `BaseMarketDataProvider` i schemat `FundamentalData`.
  - `mock_provider.py`: Wbudowane zweryfikowane dane 10 spółek (BRK.B, AAPL, KO, GOOGL, V, TGT, JNJ itp.).
  - `yfinance_provider.py`: Skaner dowolnego tickera z rynków światowych.
  - `fmp_provider.py`: Adapter do komercyjnego Financial Modeling Prep API.
- `backend/app/services/`:
  - `buffett_calculator.py`: Wyliczanie wartości wewnętrznej (DCF na bazie Owner Earnings), wskaźnika Buffett Score (0–100), marginesu bezpieczeństwa oraz audyt Reguły 1.
  - `ai_analyzer.py`: Generowanie tezy inwestycyjnej, oceny fosy ekonomicznej (Moat) oraz ryzyk (wsparcie dla Gemini API lub heurystyczny generator memoriałów Buffetta).
  - `portfolio_tracker.py`: Silnik audytowy portfela demo i porównanie z S&P 500 (obliczanie Alfy Buffetta).
- `backend/app/routers/`:
  - `screener.py` (`/api/screener`)
  - `analysis.py` (`/api/analysis/{ticker}`)
  - `portfolio.py` (`/api/portfolio`)
  - `settings.py` (`/api/settings`)

### Frontend (React 19 / Vite / Tailwind CSS v4 / Recharts / Lucide Icons)
- `frontend/src/components/Header.jsx`: Minimalistyczny pasek z mottem Buffetta, statusem dostawcy i zakładkami.
- `frontend/src/components/PortfolioView.jsx`: Dashboard audytu 1-rocznego z wykresem Equity Curve vs S&P 500, wskaźnikiem Alfy, kartami KPI oraz tabelą otwartych pozycji.
- `frontend/src/components/ScreenerView.jsx`: Tabela filtrująca spółki (Buffett Score, margines bezpieczeństwa, ROIC, wskaźnik długu) oraz pole do skanowania dowolnego tickera.
- `frontend/src/components/DeepDiveView.jsx`: Karta wyceny DCF, Owner Earnings, checklist 4 Zasad Buffetta, memoriał AI oraz przycisk zapisu do portfela demonstracyjnego.
- `frontend/src/components/SettingsView.jsx`: Panel przełączania adaptera danych rynkowych i konfiguracji kluczy API.

---

## 3. Instrukcja Odtworzenia Projektu na Innym Komputerze

1. **Sklonowanie repozytorium**:
   ```bash
   git clone https://github.com/przemekoduje/buffet.git
   cd buffet
   ```
2. **Instalacja zależności**:
   - Backend:
     ```bash
     cd backend
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     cd ..
     ```
   - Frontend:
     ```bash
     cd frontend
     npm install
     cd ..
     ```
3. **Uruchomienie aplikacji**:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```
   - Aplikacja: `http://localhost:5173`
   - Dokumentacja API: `http://localhost:8000/docs`

---
*Dokument zarchiwizowany automatycznie dla celów ciągłości projektu.*
