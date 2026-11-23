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

### 4.7. Integracja z Google Firebase (Zapis Danych Użytkownika w Chmurze)
- **Firebase Client SDK (Frontend):**
  - Zainstalowano pakiet `firebase` w frontendzie.
  - Skonfigurowano `frontend/src/config/firebase.js` z `VITE_FIREBASE_*` (Auth + Firestore).
  - Dodano modal autoryzacji `AuthModal.jsx` z obsługą logowania przez Google (1-click popup) oraz Email + Hasło i trybem gościa.
  - Dodano wskaźnik stanu chmury w nagłówku `Header.jsx`: `🟢 Firebase Cloud: Zsynchronizowano` vs `⚪ Tryb Lokalny (Gość)` + awatar użytkownika.
- **Firebase Admin SDK (Backend):**
  - Zainstalowano `firebase-admin>=7.5.0` w środowisku wirtualnym i `backend/requirements.txt`.
  - Utworzono moduł `backend/app/services/firebase_service.py` z automatycznym wykrywaniem klucza `firebase-adminsdk.json` i połączeniem z Google Cloud Firestore.
  - Utworzono router `backend/app/routers/user.py` z endpointami `/api/user/status`, `/api/user/sync` i `/api/user/watchlist`.
- **Automatyczna synchronizacja:**
  - Wszystkie pozycje portfela Paper Trading, konfiguracja Money Management, historia zleceń oraz watchlisty użytkownika zapisują się w kolekcji Firestore `buffet_users/{uid}`.
  - Po zalogowaniu na innym komputerze lub w innej przeglądarce dane użytkownika są natychmiast odtwarzane z chmury Firebase.

### 4.8. Migracja na Dedykowany Projekt Firebase `buffet-3620c`
- **Wykrycie i rejestracja aplikacji Web:**
  - Zidentyfikowano dedykowany projekt Firebase: `buffet` (`buffet-3620c`).
  - Zarejestrowano w projekcie nową aplikację webową `buffet-web` (App ID: `1:940422840205:web:809bebc17f1dcfdb2387c4`).
  - Utworzono produkcyjną bazę Firestore Native w regionie `europe-west1` (`(default)`).
- **Poświadczenia i konfiguracja:**
  - Wygenerowano nowy klucz serwisowy Admin SDK dla `firebase-adminsdk-fbsvc@buffet-3620c.iam.gserviceaccount.com` i umieszczono w `backend/firebase-adminsdk.json` (zabezpieczony w `.gitignore`).
  - Zaktualizowano `frontend/.env` danymi nowego projektu `buffet-3620c`.
- **Weryfikacja:**
  - Potwierdzono pomyślny odczyt i zapis danych w kolekcji `buffet_users` w nowym projekcie `buffet-3620c`.
  - Serwery backend i frontend zrestartowane i aktywne.

### 4.9. Konfiguracja Logowania (Email / Hasło oraz Google)
- **Aktywacja Identity Platform na projekcie `buffet-3620c`:**
  - Powiązano konto rozliczeniowe z projektem.
  - Wywołano `initializeAuth` i aktywowano obsługę `signIn.email.enabled: true`.
  - Rozszerzono listę `authorizedDomains` o `localhost`, `127.0.0.1`, `buffet-3620c.firebaseapp.com` oraz `przemokoduje.com`.
- **Weryfikacja:**
  - Przetestowano pomyślną rejestrację i logowanie nowego użytkownika przez oficjalne REST API Firebase (`test@buffet.com`).
  - Zaktualizowano `AuthModal.jsx` z obsługą błędów i intuicyjnym przełącznikiem logowania/rejestracji.

### 4.10. Implementacja Wszechwiedzącego Agenta Chat AI (Guru Buffetta)
- **Moduł Doradcy Inwestycyjnego w Backendzie (`backend/app/services/chat_agent.py` & `backend/app/routers/chat.py`):**
  - Stworzono silnik `ChatAgent` posiadający pełną bazę wiedzy o aplikacji BUFFET (4 filary Buffetta, model DCF Owner Earnings, scoring fundamentalny 0-100, zasady Money Management, Paper Trading, wiadomości rynkowe, alerty i synchronizacja Firebase).
  - Agent automatycznie wykrywa tickery spółek w wypowiedziach użytkownika (np. AAPL, KO, BRK.B, TSLA) i w czasie rzeczywistym pobiera z rynków aktualne wskaźniki (P/E, ROIC, Margines Bezpieczeństwa, Wycena DCF, P/FCF, wiadomości).
  - Możliwość wprowadzania danych zewnętrznych przez użytkownika (np. wklejenie raportu kwartalnego, fragmentu 10-K, notatki maklerskiej) do dogłębnej analizy.
  - Generowanie odpowiedzi w oparciu o Google Gemini AI (lub inteligentny silnik regułowy w stylu Warrena Buffetta) wraz z interaktywnymi akcjami (otwarcie analizy spółki, złożenie zlecenia kupna w Paper Trading, przejście do screenera).
- **Interfejs Chat AI na Frontendzie (`frontend/src/components/ChatAdvisorDrawer.jsx`):**
  - Wysuwany panel boczny (Drawer) z awatarem i statusem Guru Inwestycyjnego ("Warren Buffett AI"), minimalistyczną typografią i możliwością rozszerzenia na pełny ekran.
  - Szybkie podpowiedzi (Starter Pills), akordeon na dane zewnętrzne z raportów/artykułów oraz interaktywne przyciski akcji do natychmiastowego przejścia do wykresów i zleceń.
  - Przycisk w nagłówku aplikacji (`Header.jsx`) z pulsującym wskaźnikiem oraz pływający przycisk FAB w prawym dolnym rogu ekranu (`App.jsx`).

### 4.11. Rozszerzenie Encyklopedycznej Bazy Wiedzy Agenta Chat AI i Optymalizacja LLM
- **Kompleksowa Encyklopedia Wiedzy Aplikacji (`backend/app/services/chat_agent.py`):**
  - Wprowadzono do promptu systemowego agenta pełną dokumentację każdego mechanizmu aplikacji BUFFET:
    - Dokładne wzory wyceny: kalkulacja Znormalizowanego Zysku Właścicielskiego (*Owner Earnings*), 10-letni dynamiczny DCF (wzrost lat 1-5 z ograniczeniem mega-cap i instytucji finansowych, fade-down lat 6-10, model Gordona z $g=3.0\%$, stałe stopy dyskontowe Buffetta 9.0%-10.5%, korekta o dług netto i specjalna zasada 35% floatu dla spółek ubezpieczeniowych).
    - Punktacja *Buffett Score (0-100)*: dokładna waga i progi punktowe dla 6 kryteriów (ROIC max 20 pkt, ROE max 15 pkt, Pricing Power / Marża Brutto max 15 pkt, Dług Netto / FCF max 20 pkt, Margines Bezpieczeństwa max 20 pkt, CAGR przychodów max 10 pkt) oraz warunki rekomendacji (`STRONG_BUY`, `BUY`, `HOLD`, `AVOID`).
    - Audyt ryzyka wg Reguły nr 1 (kryteria i poziomy `LOW`, `MODERATE`, `HIGH`).
    - Zasady dyscypliny kapitałowej Money Management ($100 000 wirtualnego kapitału, pozycja 10%, max alokacja 20-25%, rezerwa gotówkowa min. 10-15%, Stop Loss 15%, Take Profit 35%, kalkulacja Alfy portfela względem S&P 500).
    - Struktura i harmonogram Screenera (3 koszyki: `us_quality`, `sp500_value`, `dividend_aristocrats`, alerty intraday i EOD).
    - Integracja z Firebase Firestore Native (`buffet_users/{uid}`) i definicje wszystkich wskaźników giełdowych.
- **Wielopoziomowa odporność i rotacja modeli językowych:**
  - Skonfigurowano model `gemini-3.5-flash-lite` z dynamicznym fallbackiem na `gemini-flash-latest` oraz zoptymalizowanym czasem oczekiwania (timeout 6s) eliminującym zawieszanie się na zewnętrznych przeciążeniach 503.
  - Rozbudowano silnik dynamicznego wnioskowania lokalnego o natychmiastowe, szczegółowe odpowiedzi na pytania o każdy wskaźnik, wzór i funkcję aplikacji w sytuacji braku odpowiedzi zewnętrznego API.

### 4.12. Dedykowany Moduł Banku Wiedzy (Knowledge Base) i Przeglądarka Zagadnień
- **Struktura Modułu Banku Wiedzy (`backend/app/knowledge/knowledge_base.py`):**
  - Utworzono 10 ustrukturyzowanych rozdziałów wiedzy pokrywających każdy aspekt serwisu:
    1. *Filozofia Inwestowania w Wartość i Reguła Nr 1* (`philosophy`),
    2. *Cztery Filtry Selekcyjne Warrena Buffetta* (`four_filters`),
    3. *Zysk Właścicielski (Owner Earnings) i Normalizacja Przepływów* (`owner_earnings`),
    4. *Model 10-letniego DCF i Wartość Wewnętrzna (Intrinsic Value)* (`dcf_model`),
    5. *Metodologia Punktacji Buffett Score (0-100 pkt)* (`buffett_score`),
    6. *Reguła Nr 1: Audyt Ryzyka i Sygnały Ostrzegawcze* (`rule_one_risk`),
    7. *Portfel Paper Trading i Zasady Money Management* (`portfolio_money_management`),
    8. *Skaner Rynku (Screener), Koszyki i Alerty Sesyjne* (`screener_baskets`),
    9. *Encyklopedia Wszystkich Wskaźników Finansowych* (`financial_metrics_glossary` — ROIC, ROE, marże, FCF TTM, Net Debt/FCF, Current Ratio, Altman Z-Score, P/E, P/FCF, Dividend Yield, CAGR),
    10. *Architektura Danych, Firebase Firestore i Bezpieczeństwo* (`firebase_architecture`).
  - Zaimplementowano funkcje retrievalowe: `get_full_knowledge_document()`, `get_topics_list()`, `get_topic_by_id()` oraz `find_relevant_knowledge()` z precyzyjnym dopasowywaniem całych słów i wag słów kluczowych.
- **Rozszerzenie API Chat (`backend/app/routers/chat.py`):**
  - Dodano endpoint `GET /api/chat/knowledge` zwracający listę tematów i podsumowań.
  - Dodano endpoint `GET /api/chat/knowledge/{topic_id}` zwracający pełną treść wybranego zagadnienia.
- **Interaktywna Przeglądarka w Frontendzie (`frontend/src/components/ChatAdvisorDrawer.jsx`):**
  - Dodano przycisk `📚 Bank Wiedzy` w nagłówku okna czatu.
  - Zaimplementowano rozwijany panel z kafelkami wszystkich 10 tematów (kategorie, tytuły, zwięzłe streszczenia), umożliwiający natychmiastowe odpytanie agenta jednym kliknięciem.
