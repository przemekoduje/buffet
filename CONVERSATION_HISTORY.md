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

## 4. Dziennik Sesji — 2026-11-23

### 4.1. Naprawa pobierania danych i integracji Gemini AI
- **Diagnoza błędów składniowych:** usunięto zduplikowane fragmenty po nieudanym scaleniu w `backend/app/providers/yfinance_provider.py` i `backend/app/services/buffett_calculator.py` (`IndentationError`), przywracając start FastAPI.
- **Proxy Vite na Windows:** zmieniono cel proxy w `frontend/vite.config.js` z `http://localhost:8000` na `http://127.0.0.1:8000` (uniknięcie konfliktu IPv6 `::1` vs IPv4 `0.0.0.0`). Dodano wyraźną obsługę błędów w `SettingsView.jsx`.
- **Migracja modeli Gemini:** starsze modele `gemini-2.5-flash` i `gemini-2.0-flash` zwracały `HTTP 404` (wycofane dla nowych kluczy), a `gemini-3.8-flash` / `gemini-3.7-flash` zwracały `503 high demand`. Przełączono domyślny model na szybki i stabilny **`gemini-flash-lite-latest`** z łańcuchem fallbacków (`gemini-3.5-flash-lite`, `gemini-3-flash-preview`, `gemini-3.5-flash`) oraz krótszym timeoutem `12s`.
- **Launcher Windows:** dodano `start_buffet.bat` do niezależnego uruchamiania backendu i frontendu w osobnych oknach.

### 4.2. Kalibracja modelu DCF i spójność liczb w analizie AI
- **Analiza rozbieżności `BRK.B` (`$795.77` vs `~$433–$512`):** ograniczono maksymalny wzrost w DCF zależnie od skali firmy i sektora (dla `Financial Services` max `7%`, dla mega-capów > `$500 mld` max `11%` zamiast `18%`). Dla sektora finansowego/ubezpieczeniowego uwzględniana jest max `35%` gotówki netto (żeby nie traktować floatu ubezpieczeniowego jak wolnej gotówki). Wycena `BRK.B` spadła do realistycznego poziomu `~$397.33`.
- **Spójność dźwigni i liczb AI (`KO`):**
  - Stopa dyskontowa w `buffett_calculator.py` liczy dźwignię od znormalizowanego `Owner Earnings` (zamiast jednorazowo zaniżonego `FCF TTM`).
  - W `ai_analyzer.py` dodano `intrinsic_value` do klucza cache AI, obniżono `temperature` do `0.2` oraz wprowadzono post-processing gwarantujący 100% zgodności wartości DCF między kartą a tekstem memoriału AI.

### 4.3. Nowy Screener Rynku (EOD + 3 Koszyki + Alerty Sesyjne)
- **Nowe tabele SQLite (`models.py`):** `market_scan_results` (trwały zapis wyników skanu EOD) oraz `market_alerts` (alerty sesyjne z 6-godzinną deduplikacją).
- **Silnik `backend/app/services/market_scanner.py` + harmonogram w `lifespan` (`backend/main.py`):**
  - **3 koszyki tematyczne** (~40 spółek USA): `US Quality`, `S&P 500 Value`, `Dywidendowi Arystokraci`.
  - **Automatyczny skan EOD:** Pn–Pt po zamknięciu sesji USA (`16:15 ET` / `~22:15 PL`) + ręczny przycisk *„Skanuj rynek teraz (EOD)”*.
  - **Alerty sesyjne (Intraday):** co 15 min w trakcie sesji USA (batch `yf.download` dla całego uniwersum) — reguły `BUY_ZONE_DROP` (HIGH), `INTRADAY_PULLBACK`, `INTRADAY_SURGE`, `VOLUME_SPIKE`.
  - **Oznaczenie Paper Trading:** każda spółka w Screenerze i alertach ma status `W PORTFELU` (z P&L %) vs `Poza portfelem` + filtr ukrywania posiadanych pozycji oraz kolumnę rekomendacji (`STRONG BUY`, `BUY`, `HOLD`, `AVOID`).
- **Analiza kosztów:** skan EOD i alerty intraday opierają się na darmowym `yfinance` i lokalnym silniku DCF (**0 zł**). Gemini AI (`gemini-3.5-flash-lite` / `gemini-flash-lite-latest`) uruchamia się wyłącznie na żądanie w Deep Dive (Free Tier **0 zł**; Paid Tier ok. **~$0.0013 / ~0,5 gr** za analizę).

### 4.4. Realny Paper Trading z Money Management i Modalem Zleceń
- **Nowe tabele (`models.py`):** `paper_account_config` (stały kapitał startowy domyślnie `$100 000`, saldo gotówki, zrealizowany P&L, reguły MM: domyślna pozycja %, max w 1 spółce %, max liczba pozycji, rezerwa gotówki %, SL %, TP %, prowizja %, akcje ułamkowe) oraz `paper_trades` (dziennik wszystkich zleceń `BUY`/`SELL`).
- **Silnik `portfolio_tracker.py` + endpointy `portfolio.py`:** `POST /api/portfolio/buy`, `POST /api/portfolio/sell/{id}`, `GET/POST /api/portfolio/mm`, `POST /api/portfolio/reset` z twardą walidacją wszystkich reguł MM.
- **Zunifikowany modal `frontend/src/components/TradeOrderModal.jsx`:** każda operacja kupna, dokupienia, sprzedaży częściowej lub zamknięcia pozycji (z Portfela, Screenera i Deep Dive) wymaga potwierdzenia w modalu z podglądem wpływu na wagi/gotówkę/P&L oraz możliwością korekty reguł MM bezpośrednio przed zatwierdzeniem.

### 4.5. Newsy Rynkowe w Deep Dive i Analizie Gemini AI
- **`yfinance_provider.py`:** dodano `get_ticker_news()` (do 8 najnowszych wiadomości z Yahoo Finance z 15-min cache).
- **`ai_analyzer.py` + `DeepDiveView.jsx`:** 6 najnowszych nagłówków trafia do promptu Gemini AI, które zwraca ocenę sentymentu (`POZYTYWNY` / `NEUTRALNY` / `NEGATYWNY`) oraz sekcję *„Wpływ Bieżących Newsów Rynkowych”*; poniżej memoriału wyświetlane są klikalne karty newsów.

### 4.6. Kolejne ustalenia w toku (przegląd zakładki Screener)
- Rozpoczęto szczegółowy przegląd elementów zakładki Screener od punktu **1. „Sprawdź alerty sesyjne”** — zidentyfikowano 3 obszary do rozważenia: sortowanie alertów priorytetowo (`HIGH` na górze) + rozwijanie ponad 6 kart, dodanie alertów SL/TP z portfela Paper Trading oraz wyraźne oznaczanie sesji live vs ostatniej zamkniętej sesji.

---
*Dokument zarchiwizowany automatycznie dla celów ciągłości projektu.*
