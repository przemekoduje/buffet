# BUFFET — Value Investing & AI Market Screener
> **Część 4 aplikacji przemokoduje.com**  
> *"Reguła nr 1: Nigdy nie trać pieniędzy. Reguła nr 2: Zawsze pamiętaj o punkcie pierwszym."* — Warren Buffett

Aplikacja analityczna dla inwestorów fundamentalnych, implementująca zasady Warrena Buffetta i Charliego Mungera z warstwą sztucznej inteligencji (AI) oraz 1-rocznym audytem skuteczności predykcji w koncie demonstracyjnym.

---

## 🏛️ Filozofia & 4 Filtry Buffetta w Kodzie

1. **Trwała Fosa Ekonomiczna (Economic Moat & Pricing Power):**
   - ROIC (Zwrot z zainwestowanego kapitału) > 12–15% stabilnie przez 5–10 lat.
   - Marża brutto (Gross Margin) > 40% jako dowód zdolności podnoszenia cen.
2. **Bezpieczny Bilans (Reguła nr 1: Ochrona przed stratą):**
   - Net Debt / FCF < 3.0 lata (firma może spłacić dług z trzech lat wolnych przepływów).
   - Wskaźnik płynności bieżącej (Current Ratio) > 1.2 oraz Altman Z-Score > 3.0.
3. **Kompetentny Zarząd & Alokacja Kapitału:**
   - Wysoki wskaźnik ROE (>15%), brak nadmiernego rozwodnienia akcji (SBC), skupy akcji.
4. **Wycena Intrinsic Value & Margines Bezpieczeństwa (Margin of Safety):**
   - Konserwatywna wycena DCF oparta na **Zysku Właścicielskim (Owner Earnings)**.
   - Rekomendacja kupna wyłącznie przy cenie rynkowej stanowiącej min. 70–80% wartości godziwej (margines min. +15–20%).
5. **Memoriał Inwestycyjny AI:**
   - Jakościowa analiza sprawozdań 10-K, transkryptów z konferencji zarządu i bezpośredni audyt ryzyk pod kątem Reguły 1.

---

## 📊 1-Roczny Audyt Skuteczności (Konto Demo Admina)

- Wszystkie wytypowane spółki są rejestrowane w bazie danych z niezmiennym znacznikiem czasu (`timestamp`), ceną wejścia i wyliczoną wyceną DCF.
- Codzienny automatyczny audyt P&L w relacji do benchmarku **S&P 500**.
- Wyliczanie **Alfy Buffetta** (o ile model wygrywa z rynkiem) i przestrzegania limitów ryzyka.

---

## 🔌 Architektura: 1 Dashboard, Wymienne Źródła Danych (Adapter Pattern)

Wszystkie wersje panelu admina wyglądają i działają identycznie. Koszt zależy wyłącznie od wybranego adaptera danych:

1. **Wersja Darmowa / Mock (0 zł):**
   - Wbudowane zweryfikowane dane 10 kluczowych spółek (BRK.B, AAPL, KO, GOOGL, V, JNJ, TGT) — idealna do testów natychmiastowych.
2. **Wersja Otwarta / yfinance (0 zł):**
   - Pobieranie na żywo wskaźników dla dowolnego tickera z giełd światowych (S&P 500, NASDAQ, GPW).
3. **Wersja Średnia / FMP API (~$19–29/mc):**
   - Znormalizowane sprawozdania finansowe za 30 lat wstecz, transkrypty rozmów zarządu (Earnings Calls) i transakcje insiderów.

---

## 🚀 Szybki Start

### Uruchomienie całości jednym poleceniem:
```bash
chmod +x start.sh
./start.sh
```

- **Frontend (Panel Admina):** `http://localhost:5173`
- **Backend (FastAPI Docs):** `http://localhost:8000/docs`
