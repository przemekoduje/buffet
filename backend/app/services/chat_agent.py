import re
import json
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.config import settings
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator
from app.services.portfolio_tracker import PortfolioTracker
from app.services.market_scanner import MarketScanner

APP_KNOWLEDGE_BASE = """
# ENCYKLOPEDIA I DOKUMENTACJA WIEDZY APLIKACJI BUFFET (przemokoduje.com - Moduł IV)

## 1. MISJA I GŁÓWNA FILOZOFIA
- BUFFET to czwarty moduł platformy przemokoduje.com, poświęcony w 100% inwestowaniu w wartość (Value Investing) według zasad Warrena Buffetta i Charliego Mungera.
- NADRZĘDNA ZASADA: „Reguła 1: Nigdy nie trać pieniędzy. Reguła 2: Zawsze pamiętaj o punkcie pierwszym.”
- Styl myślenia: Traktujemy akcję nie jako świstek papieru do spekulacji czy wykres do kreślenia kresek, lecz jako ułamek realnie działającego przedsiębiorstwa. Jeśli biznes radzi sobie świetnie przez 10-20 lat, kurs akcji nieuchronnie podąży za jego wynikami.

---

## 2. CZTERY FILTRY WARRENA BUFFETTA
Każda analizowana spółka musi przejść przez 4 rygorystyczne filtry selekcyjne:
1. **Zrozumiały biznes i trwała fosa ekonomiczna (Economic Moat):**
   - Spółka posiada produkt lub usługę o unikalnej pozycji rynkowej, wysokich kosztach zmiany dostawcy (switching costs), sile marki lub efekcie skali.
   - Wskaźniki fosy: ROIC >= 12-18% (zwrot z zainwestowanego kapitału) oraz Marża Brutto >= 40-45% (dowód siły cenowej / Pricing Power, odporność na inflację).
2. **Bezpieczny bilans i konserwatywna struktura kapitału (Ochrona wg Reguły 1):**
   - Spółka nie może być nadmiernie zadłużona. W razie kryzysu banki nie mogą zagrozić jej płynności.
   - Wskaźniki bilansowe: Dług Netto / Wolne Przepływy Pieniężne (Net Debt / FCF) < 2.5 roku (max 4.0 lata), Wskaźnik Płynności Bieżącej (Current Ratio) > 1.2, brak ukrytych zobowiązań leasingowych czy emerytalnych.
3. **Uczciwy, zorientowany na akcjonariuszy zarząd (Shareholder-Friendly Management):**
   - Zarząd traktuje pieniądze inwestorów jak własne.
   - Wskaźniki: Wysoki ROE >= 15-18%, mądra alokacja kapitału, regularne skupy akcji własnych (Buybacks) przy niskich wycenach, brak nadmiernego rozwadniania akcjonariuszy opcjami menedżerskimi (Stock-Based Compensation).
4. **Margines Bezpieczeństwa (Margin of Safety - MoS):**
   - Nawet najlepszy biznes staje się złą inwestycją, jeśli zapłacisz za niego zbyt dużo.
   - Wycena Wartości Wewnętrznej (Intrinsic Value) obliczana jest 10-letnim modelem DCF na bazie Znormalizowanego Zysku Właścicielskiego (Owner Earnings).
   - Wymagany dyskont: minimum 15-30% poniżej ceny rynkowej.

---

## 3. MODEL WYCENY: NORMALIZOWANY OWNER EARNINGS & 10-LETNI DCF

### A. Definicja Owner Earnings (Zysk Właścicielski Buffetta):
- Klasyczny wzór Buffetta z listu do akcjonariuszy Berkshire Hathaway (1986 r.):
  Owner Earnings = Zysk Netto + Amortyzacja (D&A) - Roczne Wydatki Inwestycyjne Utrzymaniowe (Maintenance CapEx).
- W algorytmie BUFFET:
  * Gdy FCF TTM jest dodatni i stabilny: bazujemy na FCF TTM z wygładzeniem skrajnych wahań.
  * Gdy FCF TTM jest przejściowo ujemny lub zaniżony (np. gigantyczny CapEx rozwojowy na AI w spółkach technologicznych lub jednorazowa ugoda podatkowa): algorytm normalizuje przepływy średnią historyczną 5-letnią lub konserwatywnym 70% Zysku Netto (Net Income).
  * Gdy wystąpił jednorazowy ekstremalny skok FCF (np. zawirowania floatu ubezpieczeniowego w Berkshire): FCF jest ważony z 5-letnią średnią.

### B. Dynamiczne założenia 10-letniego DCF:
1. **Lata 1-5 (Stopa wzrostu g1):**
   - Wyliczana na bazie 5-letniego CAGR przychodów firmy pomnożonego przez 0.85 (konserwatywny bufor).
   - Ograniczenia skali: dla mega-capów (kapitalizacja >$500 mld) stopa jest ograniczona do max 11%, dla firm >$200 mld max 13%, dla instytucji finansowych/ubezpieczeniowych max 7%.
2. **Lata 6-10 (Stopa wzrostu g2 - Fade-down):**
   - Prawa ekonomii i konkurencji spowalniają wzrost: g2 wynosi 60% tempa z lat 1-5, w przedziale [3.0%, 8.0%].
3. **Wartość Rezydualna / Terminal Value (Model Gordona):**
   - Stopa wzrostu wieczystego gt = 3.0% (tempo nominalnego wzrostu globalnego PKB).
   - Terminal Value = [CF_10 * (1 + gt)] / (Discount_Rate - gt).
4. **Stopa Dyskontowa (Hurdle Rate Buffetta):**
   - Buffett nie używa CAPM ani zmiennego WACC. Używa stałego, bezwzględnego kosztu alternatywnego kapitału:
   - 9.0% dla spółek o zerowym/niskim długu (Net Debt/FCF <= 2.5) i marży brutto >= 35%.
   - 9.5% dla umiarkowanego zadłużenia (Net Debt/FCF <= 4.0).
   - 10.5% dla spółek o podwyższonej dźwigni finansowej.
5. **Korekta o bilans (Enterprise Value -> Equity Value):**
   - Wartość Wewnętrzna Kapitału Własnego = PV(Przepływy 1-10 lat) + PV(Wartość Rezydualna) - Dług Netto.
   - Ujemny Dług Netto oznacza gotówkę netto (dodatkową wartość dla akcjonariuszy).
   - Specjalna reguła sektora finansowego/ubezpieczeniowego (np. BRK.B, JPM): gotówka w bilansie stanowi float regulacyjny, dlatego uwzględnia się konserwatywnie max 35% gotówki netto.
6. **Wartość Wewnętrzna na akcję (Intrinsic Value per share):**
   - Intrinsic Value = Equity Value / Liczba Rozwodnionych Akcji (Shares Outstanding).
7. **Margines Bezpieczeństwa (MoS %):**
   - MoS = ((Wartość Wewnętrzna - Aktualny Kurs) / Wartość Wewnętrzna) * 100%.
   - Wartość dodatnia (np. +35%): spółka notowana z dyskontem (okazja inwestycyjna).
   - Wartość ujemna (np. -60%): spółka notowana z premią (przewartościowana przez rynek).

---

## 4. METODOLOGIA BUFFETT SCORE (0 - 100 PKT)
Buffett Score to obiektywna, ważona ocena fundamentalna łącząca jakość biznesu, bezpieczeństwo bilansu i atrakcyjność ceny:

1. **ROIC (Zwrot z zainwestowanego kapitału) - Max 20 pkt:**
   - ROIC >= 18%: 20 pkt (Wybitna fosa)
   - ROIC 12 - 18%: 14 pkt (Solidny zwrot)
   - ROIC < 12%: 4 pkt (Przeciętna rentowność)
2. **ROE (Zwrot z kapitału własnego) - Max 15 pkt:**
   - ROE >= 18%: 15 pkt
   - ROE 12 - 18%: 10 pkt
   - ROE < 12%: 2 pkt
3. **Marża Brutto (Pricing Power / Fosa Cenowa) - Max 15 pkt:**
   - Marża >= 45%: 15 pkt (Silna fosa)
   - Marża 30 - 45%: 10 pkt (Umiarkowana fosa)
   - Marża < 30%: 3 pkt (Brak fosy cenowej)
4. **Bezpieczeństwo Zadłużenia (Net Debt / FCF) - Max 20 pkt:**
   - Gotówka netto (Net Debt <= 0): 20 pkt
   - Net Debt / FCF <= 2.5 roku: 18 pkt (Bezpieczny dług)
   - Net Debt / FCF 2.5 - 4.0 lat: 10 pkt (Znośne zadłużenie)
   - Net Debt / FCF > 4.0 lat: 0 pkt (Wysokie ryzyko dłużne)
5. **Margines Bezpieczeństwa (Wycena DCF vs Kurs) - Max 20 pkt:**
   - MoS >= +30%: 20 pkt (Głębokie niedowartościowanie)
   - MoS +15% do +30%: 14 pkt (Dobre dyskonto)
   - MoS 0% do +15%: 8 pkt (Godziwa cena)
   - MoS < 0%: 0 pkt (Brak marginesu / przewartościowanie)
6. **Wieloletni Wzrost Przychodów (5-letni CAGR) - Max 10 pkt:**
   - CAGR >= 8%: 10 pkt (Stabilny wzrost)
   - CAGR 3 - 8%: 6 pkt (Umiarkowany wzrost)
   - CAGR < 3%: 2 pkt (Stagnacja)

### Kategorie Rekomendacji:
- **STRONG_BUY:** Score >= 80 pkt, Margines Bezpieczeństwa >= 20% oraz Ryzyko Reguły 1 = LOW.
- **BUY:** Score >= 65 pkt oraz Margines Bezpieczeństwa >= 10%.
- **HOLD:** Score >= 50 pkt lub Margines Bezpieczeństwa >= -10%.
- **AVOID:** Score < 50 pkt lub skrajne przewartościowanie / wysoki dług.

---

## 5. REGUŁA NR 1 I POZIOMY RYZYKA (RULE #1 RISK)
Algorytm bada 4 krytyczne sygnały ostrzegawcze:
1. Net Debt / FCF > 4.5 roku (obsługa długu pochłonie ponad 4.5 lat wolnych przepływów).
2. Płynność bieżąca (Current Ratio) < 1.0 (ryzyko zatorów i niewypłacalności).
3. Margines Bezpieczeństwa < -25% (drastyczne przewartościowanie rynkowe).
4. ROIC < 8% (niska efektywność operacyjna, niszczenie kapitału akcjonariuszy).

Klasyfikacja:
- **LOW:** 0 ostrzeżeń — czysta spółka o najwyższym profilu bezpieczeństwa.
- **MODERATE:** 1-2 ostrzeżenia — wymaga uwagi i czujności.
- **HIGH:** 3 lub 4 ostrzeżenia — absolutny zakaz kupna wg Reguły 1.

---

## 6. MODUŁ PORTFEL PAPER TRADING & MONEY MANAGEMENT
- **Wirtualny kapitał startowy:** 100 000 USD (Paper Trading / konto demo bez ryzyka).
- **Zasady Money Management (Dyscyplina Kapitałowa):**
  * Domyślna wielkość 1 pozycji: 10% kapitału (10 000 USD).
  * Maksymalna dopuszczalna alokacja w 1 spółkę: 20-25% kapitału (koncentracja Buffetta, ale bez samobójczego ryzyka).
  * Maksymalna liczba spółek w portfelu: 10-15 podmiotów.
  * Obowiązkowa rezerwa gotówkowa (Cash Reserve): minimum 10-15% utrzymywane zawsze na rachunku („suchy proch” na krachy i przeceny).
  * Zlecenia Stop Loss (ochrona kapitału): 15% poniżej ceny zakupu.
  * Zlecenia Take Profit (realizacja zysków): 35-40% powyżej ceny zakupu.
  * Prowizja maklerska: modelowana na 0.0% (współczesne domy maklerskie USA).
  * Obsługa akcji ułamkowych (Fractional Shares).
- **Wskaźnik Alfa Buffetta:**
  * Wzór: Alfa (%) = Stopa Zwrotu Portfela (%) - Średnia Stopa Zwrotu S&P 500 (%).
  * Pokazuje czystą wartość dodaną selekcji spółek w wartość ponad szeroki indeks rynkowy.

---

## 7. SKANER RYNKU I KOSZYKI INWESTYCYJNE (SCREENER)
Skaner monitoruje bazę spółek i klasyfikuje je do 3 koszyków tematycznych:
1. `us_quality` (Jakość USA & Silna Fosa): Spółki o światowej renomie, dominującej pozycji i powtarzalnym popycie (np. Apple, Microsoft, Visa, Alphabet, Coca-Cola).
2. `sp500_value` (S&P 500 Promocje / Wartość): Spółki z indeksu S&P 500 wykazujące największe dyskonto wyceny DCF do kursu.
3. `dividend_aristocrats` (Arystokraci Dywidendy): Spółki podnoszące dywidendę nieprzerwanie od min. 25 lat, z bezpiecznym wskaźnikiem wypłaty Payout Ratio.
- **Harmonogram skanera:**
  * Skan sesyjny EOD (End of Day): wykonywany po zamknięciu giełd w USA (~22:15 czasu polskiego).
  * Alerty Intraday: skanowanie kursów co 15 minut podczas trwania sesji (15:30 - 22:00 CET).

---

## 8. SYNCHRONIZACJA W CHMURZE GOOGLE FIREBASE
- Aplikacja posiada pełną integrację z dedykowanym projektem Firebase `buffet` (`buffet-3620c`) w regionie `europe-west1`.
- Baza danych: Google Cloud Firestore Native. Kolekcja: `buffet_users/{uid}`.
- Zapisywane dane: stan portfela, historia transakcji, reguły Money Management, konfiguracja wskaźników, lista obserwowanych spółek (Watchlist).
- Dostępne metody logowania: Email + Hasło oraz 1-klikowe logowanie Google Sign-In.

---

## 9. SŁOWNICZEK WSZYSTKICH WSKAŹNIKÓW W APLIKACJI
- **P/E (Price to Earnings / C/Z):** Cena rynkowa / Zysk netto na akcję. Pokazuje ile lat zysków płacimy za spółkę.
- **P/FCF (Price to Free Cash Flow / C/PCP):** Cena / Wolne przepływy pieniężne na akcję. Znacznie trudniejszy do zmanipulowania przez księgowość niż P/E.
- **P/B (Price to Book / C/WK):** Cena / Wartość księgowa.
- **ROIC (Return on Invested Capital):** NOPAT / (Kapitał Własny + Dług Oprocentowany - Gotówka). Najważniejszy wskaźnik fosy Buffetta.
- **ROE (Return on Equity):** Zysk Netto / Kapitał Własny.
- **Marża Brutto (Gross Margin):** (Przychody - Koszt Własny Sprzedaży) / Przychody. Wskaźnik siły cenowej.
- **Marża Operacyjna (Operating Margin):** Zysk Operacyjny (EBIT) / Przychody.
- **FCF TTM (Free Cash Flow Trailing Twelve Months):** Przepływy z działalności operacyjnej minus wydatki majątkowe (CapEx) za ostatnie 12 miesięcy.
- **Dług Netto (Net Debt):** Zobowiązania finansowe oprocentowane minus gotówka i ekwiwalenty.
- **Net Debt / FCF:** Liczba lat wolnych przepływów potrzebnych na całkowitą spłatę długu netto.
- **Current Ratio:** Aktywa obrotowe / Zobowiązania krótkoterminowe.
- **Dividend Yield:** Roczna dywidenda na akcję / Aktualny kurs akcji.
- **Payout Ratio:** Dywidenda całkowita / Zysk Netto (bezpieczny poziom < 60%).
"""

class ChatAgent:
    """
    Wszechwiedzący Asystent Inwestycyjny i Ekspert Aplikacji BUFFET.
    Zna każdy wskaźnik, wzór i funkcję systemu, analizuje dane w locie i doradza jak Warren Buffett.
    """

    @classmethod
    def _extract_tickers(cls, text: str) -> List[str]:
        """Wykrywa tickery giełdowe w zapytaniu użytkownika (np. AAPL, KO, BRK.B)."""
        candidates = re.findall(r'\b[A-Z]{1,5}(?:\.[A-Z])?\b', text)
        known_stocks = {
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "BRK.B", "BRK.A", "KO", "PEP", "V", "MA",
            "JNJ", "PG", "COST", "TGT", "NVDA", "MCD", "DIS", "WMT", "NKE", "IBM", "UNH", "XOM",
            "CVX", "HD", "LOW", "CAT", "JPM", "BAC", "TSLA", "META", "INTU", "ADBE", "PYPL", "ADP"
        }
        found = [c for c in candidates if c in known_stocks]
        
        lower = text.lower()
        name_map = {
            "apple": "AAPL", "coca cola": "KO", "coca-cola": "KO", "berkshire": "BRK.B",
            "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL", "visa": "V",
            "target": "TGT", "walmart": "WMT", "johnson": "JNJ", "costco": "COST", "amazon": "AMZN",
            "nvidia": "NVDA", "mcdonald": "MCD", "adobe": "ADBE", "intuit": "INTU", "paypal": "PYPL",
            "jpmorgan": "JPM", "jp morgan": "JPM"
        }
        for name, ticker in name_map.items():
            if name in lower and ticker not in found:
                found.append(ticker)
        return list(dict.fromkeys(found))

    @classmethod
    async def process_chat(
        cls,
        messages: List[Dict[str, str]],
        context_ticker: Optional[str] = None,
        custom_data: Optional[str] = None,
        user_portfolio_data: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        context_data: Dict[str, Any] = {}
        tickers = cls._extract_tickers(last_user_msg)
        if context_ticker and context_ticker not in tickers:
            tickers.append(context_ticker)

        provider = get_market_provider()

        # Pobierz dane dla wykrytych spółek
        stocks_info = []
        for t in tickers[:3]:
            try:
                data = provider.get_ticker_data(t)
                if data:
                    eval_res = BuffettCalculator.evaluate(data)
                    news = provider.get_ticker_news(t, limit=3) or []
                    stocks_info.append({
                        "ticker": t,
                        "company_name": data.company_name,
                        "sector": data.sector,
                        "current_price": data.current_price,
                        "intrinsic_value": eval_res["intrinsic_value"],
                        "margin_of_safety_pct": eval_res["margin_of_safety_pct"],
                        "buffett_score": eval_res["buffett_score"],
                        "recommendation": eval_res["recommendation"],
                        "roic_pct": data.roic_pct,
                        "roe_pct": data.roe_pct,
                        "gross_margin_pct": data.gross_margin_pct,
                        "net_debt_to_fcf": data.net_debt_to_fcf,
                        "pe_ratio": data.pe_ratio,
                        "rule_1_risk": eval_res.get("rule_number_one_risk") or eval_res.get("rule_1_risk_level", "LOW"),
                        "rule_1_warnings": eval_res.get("rule_1_warnings", []),
                        "recent_news": [
                            {"title": n.get("title"), "publisher": n.get("publisher"), "url": n.get("url")}
                            for n in news[:2]
                        ]
                    })
            except Exception as e:
                print(f"[ChatAgent Error fetching ticker {t}] {e}")
        if stocks_info:
            context_data["analyzed_stocks"] = stocks_info

        # Sprawdź czy pytanie dotyczy portfela lub stanu konta
        wants_portfolio = any(w in last_user_msg.lower() for w in ["portfel", "portfolio", "konto", "pozycje", "gotówka", "p&l", "zysk", "strata", "alfa"])
        if wants_portfolio and db:
            summary = PortfolioTracker.get_portfolio_summary(db)
            raw_holdings = summary.get("holdings") or []
            context_data["user_portfolio"] = {
                "total_portfolio_value": summary.get("total_portfolio_value"),
                "cash_balance": summary.get("cash_balance"),
                "total_pnl_pct": summary.get("total_pnl_pct"),
                "alpha_pct": summary.get("alpha_pct"),
                "positions_count": summary.get("positions_count"),
                "holdings": [
                    {
                        "ticker": h.get("ticker") if isinstance(h, dict) else getattr(h, "ticker", ""),
                        "shares": h.get("shares") if isinstance(h, dict) else getattr(h, "shares", 0),
                        "entry_price": h.get("entry_price") if isinstance(h, dict) else getattr(h, "entry_price", 0),
                        "current_price": h.get("current_price") if isinstance(h, dict) else getattr(h, "current_price", 0),
                        "pnl_pct": h.get("unrealized_pnl_pct") or (h.get("pnl_pct") if isinstance(h, dict) else getattr(h, "pnl_pct", 0.0)),
                        "weight_pct": h.get("weight_pct") if isinstance(h, dict) else getattr(h, "weight_pct", 0.0)
                    }
                    for h in raw_holdings
                ],
                "mm_rules": summary.get("mm_config")
            }

        # Sprawdź czy pytanie dotyczy rekomendacji / screenera / okazji rynkowych
        wants_screener = any(w in last_user_msg.lower() for w in ["okazj", "rekomendacj", "co kupić", "ranking", "screener", "tanie", "niedowartościowan"])
        if wants_screener and db:
            screener_data = MarketScanner.get_screener_payload(db)
            scan_res = screener_data.get("items", [])
            top_stocks = sorted(
                [s for s in scan_res if s.get("buffett_score", 0) >= 60],
                key=lambda x: (x.get("buffett_score", 0), x.get("margin_of_safety_pct", 0)),
                reverse=True
            )[:5]
            if top_stocks:
                context_data["top_screener_opportunities"] = [
                    {
                        "ticker": s["ticker"],
                        "company_name": s["company_name"],
                        "buffett_score": s["buffett_score"],
                        "margin_of_safety_pct": s["margin_of_safety_pct"],
                        "current_price": s["current_price"],
                        "intrinsic_value": s["intrinsic_value"],
                        "recommendation": s["recommendation"]
                    }
                    for s in top_stocks
                ]

        # 2. Generowanie odpowiedzi (z modelem językowym Gemini lub dynamicznym lokalnym fallbackiem)
        reply = await cls._generate_ai_response(messages, context_data, custom_data)

        # 3. Sugerowane akcje dla interfejsu użytkownika
        suggested_actions = []
        if stocks_info:
            top_t = stocks_info[0]["ticker"]
            suggested_actions.append({"label": f"Otwórz Deep Dive {top_t}", "action": "OPEN_TICKER", "ticker": top_t})
            if stocks_info[0]["margin_of_safety_pct"] > 0:
                suggested_actions.append({"label": f"Zlecenie KUP {top_t}", "action": "ORDER_BUY", "ticker": top_t})
        if wants_portfolio:
            suggested_actions.append({"label": "Przejdź do Portfela", "action": "NAVIGATE_TAB", "tab": "portfolio"})
        if wants_screener:
            suggested_actions.append({"label": "Przejdź do Screenera", "action": "NAVIGATE_TAB", "tab": "screener"})

        return {
            "reply": reply,
            "data_used": context_data,
            "suggested_actions": suggested_actions,
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    async def _generate_ai_response(
        cls,
        messages: List[Dict[str, str]],
        context_data: Dict[str, Any],
        custom_data: Optional[str] = None
    ) -> str:
        gemini_key = settings.GEMINI_API_KEY
        
        system_instruction = f"""
Jesteś Wybitnym Doradcą Inwestycyjnym i Mędrcem Rynkowym w stylu Warrena Buffetta i Charliego Mungera, wbudowanym bezpośrednio w aplikację BUFFET (moduł IV ekosystemu przemokoduje.com).

TWOJA ROLA, WIEDZA I OSOBOWOŚĆ:
1. Posiadasz absolutną, encyklopedyczną wiedzę o całej aplikacji BUFFET: znasz każdy wskaźnik (ROIC, ROE, marże, P/FCF, Net Debt/FCF, Current Ratio), wzór wyceny 10-letniego DCF na Owner Earnings, mechanikę kalkulatora Buffett Score (0-100), reguły Money Management i portfela Paper Trading, strukturę 3 koszyków w Screenerze oraz integrację z Firebase.
2. Twoją nadrzędną zasadą jest ZASADA NR 1: "Nigdy nie trać pieniędzy. Zasada 2: Nigdy nie zapominaj o punkcie pierwszym".
3. Odpowiadasz mądrze, wyczerpująco, logicznie i z mentorskim ciepłem Warrena Buffetta. Używasz twardych liczb, wzorów i analogii biznesowych. Jeśli użytkownik zapyta o jakikolwiek wskaźnik lub funkcję aplikacji, wyjaśniasz go w sposób precyzyjny i klarowny.
4. Gdy użytkownik podaje dane zewnętrzne, artykuł lub raport, poddajesz je rygorystycznemu audytowi bilansu i fosy.

ENCYKLOPEDIA WIEDZY O APLIKACJI BUFFET:
{APP_KNOWLEDGE_BASE}

DANE SYSTEMOWE POBRANE W LOCIE DLA BIEŻĄCEGO ZAPYTANIA:
{json.dumps(context_data, ensure_ascii=False, indent=2) if context_data else "Brak specyficznego kontekstu spółki - odpowiadaj z pełnej wiedzy o aplikacji i filozofii Buffetta."}

DODATKOWE DANE OD UŻYTKOWNIKA (JEŚLI PODANE):
{custom_data or "Brak"}
"""

        if gemini_key:
            # Lista modeli do wypróbowania w kolejności (od najszybszego i najbardziej stabilnego)
            candidate_models = [
                settings.GEMINI_MODEL or "gemini-3.5-flash-lite",
                "gemini-3.5-flash-lite",
                "gemini-flash-latest"
            ]
            # Usuń duplikaty zachowując kolejność
            models_to_try = list(dict.fromkeys(candidate_models))

            raw_contents = []
            for m in messages:
                role = "user" if m.get("role") == "user" else "model"
                txt = m.get("content", "").strip()
                if txt:
                    raw_contents.append({"role": role, "parts": [{"text": txt}]})

            # Gemini API wymaga, aby pierwsza wiadomość pochodziła od 'user'
            while raw_contents and raw_contents[0]["role"] != "user":
                raw_contents.pop(0)

            # Gemini wymaga naprzemiennych ról user -> model -> user
            alternating_contents = []
            last_role = None
            for c in raw_contents:
                if c["role"] != last_role:
                    alternating_contents.append(c)
                    last_role = c["role"]
                else:
                    alternating_contents[-1]["parts"][0]["text"] += "\n\n" + c["parts"][0]["text"]

            if alternating_contents:
                payload = {
                    "systemInstruction": {"parts": [{"text": system_instruction}]},
                    "contents": alternating_contents,
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 2000
                    }
                }

                for model in models_to_try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                    try:
                        async with httpx.AsyncClient(timeout=6.0) as client:
                            resp = await client.post(url, json=payload)
                            if resp.status_code == 200:
                                data = resp.json()
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts and parts[0].get("text"):
                                        return parts[0].get("text")
                            else:
                                print(f"[ChatAgent Gemini {model} HTTP {resp.status_code}] {resp.text[:120]}")
                    except Exception as e:
                        print(f"[ChatAgent Gemini {model} Error] {e}")

        # Inteligentny lokalny generator dynamiczny
        return cls._generate_fallback_response(messages, context_data, custom_data)

    @classmethod
    def _generate_fallback_response(
        cls,
        messages: List[Dict[str, str]],
        context_data: Dict[str, Any],
        custom_data: Optional[str]
    ) -> str:
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "").lower()
                break

        # Scenariusz 1: Pytanie o konkretną spółkę (zawsze priorytet)
        if "analyzed_stocks" in context_data and context_data["analyzed_stocks"]:
            s = context_data["analyzed_stocks"][0]
            mos = s["margin_of_safety_pct"]
            is_cheap = mos > 10
            moat_verdict = "potężną fosę ekonomiczną" if s["gross_margin_pct"] >= 40 and s["roic_pct"] >= 15 else "umiarkowaną fosę"
            debt_verdict = "bezpieczny" if s["net_debt_to_fcf"] <= 2.5 else "wymagający wzmożonej czujności"

            return (
                f"### Analiza w stylu Warrena Buffetta: **{s['company_name']} ({s['ticker']})**\n\n"
                f"*„Cena jest tym, co płacisz. Wartość jest tym, co otrzymujesz.”*\n\n"
                f"Przyjrzyjmy się fundamentom tej spółki z perspektywy Berkshire Hathaway:\n\n"
                f"1. **Wycena Intrinsic Value & Margines Bezpieczeństwa:**\n"
                f"   - Aktualny kurs rynkowy: **${s['current_price']}**\n"
                f"   - Wartość wewnętrzna (10-letni DCF Owner Earnings): **${s['intrinsic_value']}**\n"
                f"   - **Margines Bezpieczeństwa:** **{'+' if mos >= 0 else ''}{mos}%** "
                f"({ 'Spółka oferuje satysfakcjonującą poduszkę ochronną' if is_cheap else 'Brak wymaganego dyskonta do ceny godziwej' }).\n\n"
                f"2. **Fosa Ekonomiczna & Rentowność:**\n"
                f"   - **ROIC (Zwrot z zainwestowanego kapitału):** **{s['roic_pct']}%** (nasz próg to min. 12-15%).\n"
                f"   - **Marża brutto (Pricing Power):** **{s['gross_margin_pct']}%** — wskazuje na {moat_verdict}.\n"
                f"   - **ROE:** **{s['roe_pct']}%**.\n\n"
                f"3. **Reguła nr 1 (Nie trać pieniędzy):**\n"
                f"   - Poziom długu netto do FCF: **{s['net_debt_to_fcf']}x** ({debt_verdict}).\n"
                f"   - Buffett Score: **{s['buffett_score']}/100** — Rekomendacja modelu: **{s['recommendation']}**.\n\n"
                f"💡 **Mój werdykt:** "
                f"{'To wspaniałe przedsiębiorstwo w uczciwej cenie. Warto rozważyć alokację zgodną z Twoim Money Management (np. 10% kapitału).' if is_cheap and s['buffett_score'] >= 65 else 'Choć biznes może być solidny, obecny rynek nie oferuje odpowiedniego dyskonta. Pamiętaj: inwestowanie to gra, w której nie ma przymusu uderzania każdej piłki. Cierpliwość jest największą cnotą inwestora w wartość.'}"
            )

        # Scenariusz: Pytanie o Owner Earnings
        if any(w in last_user for w in ["owner earnings", "zysk właścicielski", "właścicielsk"]):
            return (
                "### Czym jest Owner Earnings (Zysk Właścicielski)?\n\n"
                "*„Kiedy z Charliem analizujemy sprawozdania, nie patrzymy na zysk netto ani na modną EBITDA. Patrzymy na realną gotówkę, którą właściciel może wyciągnąć ze spółki bez uszczerbku dla jej zdolności operacyjnych.”* — Warren Buffett\n\n"
                "**Wzór Buffetta:**\n"
                "$$\\text{Owner Earnings} = \\text{Zysk Netto} + \\text{Amortyzacja (D&A)} - \\text{CapEx Utrzymaniowy (Maintenance CapEx)}$$\n\n"
                "**Jak liczymy to w aplikacji BUFFET:**\n"
                "1. **Baza FCF:** Standardowo opieramy się na Free Cash Flow TTM (Operating Cash Flow minus Całkowity CapEx).\n"
                "2. **Inteligentna Normalizacja:** Jeśli firma (np. technologiczna) ponosi gigantyczny CapEx rozwojowy na AI lub miała jednorazowy odpis, nasz algorytm wygładza wynik 5-letnią średnią historyczną lub bierze 70% zysku netto, aby nie karać biznesu za inwestycje w przyszłą fosę."
            )

        # Scenariusz: Pytanie o Buffett Score
        if any(w in last_user for w in ["buffett score", "score", "punktacja", "jak liczycie score"]):
            return (
                "### Jak wyliczany jest Buffett Score (0 - 100 pkt)?\n\n"
                "Nasz algorytm ocenia spółkę w 6 rygorystycznych wymiarach fundamentalnych:\n\n"
                "1. **ROIC (Zwrot z zainwestowanego kapitału) — max 20 pkt:**\n"
                "   - $\\ge 18\\%$: **20 pkt** (potężna fosa) | $12-18\\%$: **14 pkt** | $<12\\%$: **4 pkt**\n"
                "2. **ROE (Zwrot z kapitału własnego) — max 15 pkt:**\n"
                "   - $\\ge 18\\%$: **15 pkt** | $12-18\\%$: **10 pkt** | $<12\\%$: **2 pkt**\n"
                "3. **Pricing Power (Marża Brutto) — max 15 pkt:**\n"
                "   - $\\ge 45\\%$: **15 pkt** | $30-45\\%$: **10 pkt** | $<30\\%$: **3 pkt**\n"
                "4. **Bezpieczeństwo Bilansu (Net Debt / FCF) — max 20 pkt:**\n"
                "   - Gotówka netto: **20 pkt** | $\\le 2.5$ roku FCF: **18 pkt** | $2.5-4.0$ lat: **10 pkt** | $>4.0$ lat: **0 pkt**\n"
                "5. **Margines Bezpieczeństwa (Cena vs DCF) — max 20 pkt:**\n"
                "   - Dyskonto $\\ge 30\\%$: **20 pkt** | $15-30\\%$: **14 pkt** | $0-15\\%$: **8 pkt** | Przewartościowanie: **0 pkt**\n"
                "6. **Wzrost Przychodów (5-letni CAGR) — max 10 pkt:**\n"
                "   - $\\ge 8\\%$: **10 pkt** | $3-8\\%$: **6 pkt** | $<3\\%$: **2 pkt**\n\n"
                "**Rekomendacje:** `STRONG_BUY` ($\\ge 80$ pkt + MoS $\\ge 20\\%$), `BUY` ($\\ge 65$ pkt), `HOLD` ($\\ge 50$ pkt), `AVOID` ($<50$ pkt)."
            )

        # Scenariusz: Pytanie o DCF i Wycenę
        if any(w in last_user for w in ["dcf", "wycen", "intrinsic value", "wartość wewnętrzna"]):
            return (
                "### Model Wyceny DCF w Aplikacji BUFFET\n\n"
                "Stosujemy konserwatywny, 10-letni model zdyskontowanych przepływów pieniężnych:\n"
                "- **Lata 1-5:** Wzrost oparty o 5-letni CAGR przychodów (z limitem max 11-13% dla mega-capów, aby uniknąć huraoptymizmu).\n"
                "- **Lata 6-10:** Spowolnienie tempa do 60% z lat 1-5 (efekt konkurencji rynkowej).\n"
                "- **Wartość Rezydualna:** Model Gordona z wieczystą stopą wzrostu $g = 3.0\\%$ (tempo wzrostu PKB).\n"
                "- **Stopa Dyskontowa:** Stały koszt alternatywny kapitału Buffetta: 9.0% dla spółek bezpiecznych, 9.5-10.5% dla bardziej zadłużonych.\n"
                "- **Korekta o Dług Netto:** Od wartości firmy odejmujemy dług netto (lub dodajemy gotówkę netto), dzieląc wynik przez liczbę wyemitowanych akcji."
            )

        # Scenariusz: Pytanie o Money Management
        if any(w in last_user for w in ["money management", "zarządzanie kapitałem", "rezerwa", "stop loss"]):
            return (
                "### Zasady Money Management w Aplikacji BUFFET\n\n"
                "Dyscyplina to różnica pomiędzy inwestorem a hazardzistą:\n"
                "- **Wirtualny Kapitał Startowy:** $100 000 USD.\n"
                "- **Wielkość Pozycji:** Domyślnie 10% kapitału (max 20-25% w jednej spółce — zasada rozsądnej koncentracji).\n"
                "- **Rezerwa Gotówkowa:** Zawsze utrzymujemy minimum 10-15% w gotówce na wypadek gwałtownych przecen rynkowych.\n"
                "- **Stop Loss / Take Profit:** Zlecenia obronne 15% poniżej ceny wejścia oraz realizacja zysków przy +35-40%.\n"
                "- **Alfa Buffetta:** Mierzymy zysk portfela ponad benchmark S&P 500."
            )

        # Scenariusz: Pytanie o konkretną spółkę
        if "analyzed_stocks" in context_data and context_data["analyzed_stocks"]:
            s = context_data["analyzed_stocks"][0]
            mos = s["margin_of_safety_pct"]
            is_cheap = mos > 10
            moat_verdict = "potężną fosę ekonomiczną" if s["gross_margin_pct"] >= 40 and s["roic_pct"] >= 15 else "umiarkowaną fosę"
            debt_verdict = "bezpieczny" if s["net_debt_to_fcf"] <= 2.5 else "wymagający wzmożonej czujności"

            return (
                f"### Analiza w stylu Warrena Buffetta: **{s['company_name']} ({s['ticker']})**\n\n"
                f"*„Cena jest tym, co płacisz. Wartość jest tym, co otrzymujesz.”*\n\n"
                f"Przyjrzyjmy się fundamentom tej spółki z perspektywy Berkshire Hathaway:\n\n"
                f"1. **Wycena Intrinsic Value & Margines Bezpieczeństwa:**\n"
                f"   - Aktualny kurs rynkowy: **${s['current_price']}**\n"
                f"   - Wartość wewnętrzna (10-letni DCF Owner Earnings): **${s['intrinsic_value']}**\n"
                f"   - **Margines Bezpieczeństwa:** **{'+' if mos >= 0 else ''}{mos}%** "
                f"({ 'Spółka oferuje satysfakcjonującą poduszkę ochronną' if is_cheap else 'Brak wymaganego dyskonta do ceny godziwej' }).\n\n"
                f"2. **Fosa Ekonomiczna & Rentowność:**\n"
                f"   - **ROIC (Zwrot z zainwestowanego kapitału):** **{s['roic_pct']}%** (nasz próg to min. 12-15%).\n"
                f"   - **Marża brutto (Pricing Power):** **{s['gross_margin_pct']}%** — wskazuje na {moat_verdict}.\n"
                f"   - **ROE:** **{s['roe_pct']}%**.\n\n"
                f"3. **Reguła nr 1 (Nie trać pieniędzy):**\n"
                f"   - Poziom długu netto do FCF: **{s['net_debt_to_fcf']}x** ({debt_verdict}).\n"
                f"   - Buffett Score: **{s['buffett_score']}/100** — Rekomendacja modelu: **{s['recommendation']}**.\n\n"
                f"💡 **Mój werdykt:** "
                f"{'To wspaniałe przedsiębiorstwo w uczciwej cenie. Warto rozważyć alokację zgodną z Twoim Money Management (np. 10% kapitału).' if is_cheap and s['buffett_score'] >= 65 else 'Choć biznes może być solidny, obecny rynek nie oferuje odpowiedniego dyskonta. Pamiętaj: inwestowanie to gra, w której nie ma przymusu uderzania każdej piłki. Cierpliwość jest największą cnotą inwestora w wartość.'}"
            )

        # Scenariusz ogólny
        return (
            "Witaj! Jestem Twoim wirtualnym doradcą w stylu **Warrena Buffetta** i **Charliego Mungera**, wbudowanym w aplikację **BUFFET** (moduł IV przemokoduje.com).\n\n"
            "Znam każdy element systemu na wylot. Możesz mnie zapytać o:\n"
            "1. **Szczegóły dowolnego wskaźnika:** ROIC, ROE, marżę brutto, dług netto/FCF, current ratio czy wskaźniki płynności.\n"
            "2. **Wycenę spółki:** Jak liczymy Owner Earnings i 10-letni DCF z wartością rezydualną.\n"
            "3. **Punktację Buffett Score (0-100):** Dokładną wagę każdego z 6 kryteriów oceny spółki.\n"
            "4. **Zasady Money Management:** Limity pozycji (10%), rezerwę gotówkową (15%), zlecenia Stop Loss i wskaźnik Alfa.\n"
            "5. **Audyt dowolnej spółki (np. Apple, Coca-Cola, Google):** Podaj ticker, a zbadam jej fosę i margines bezpieczeństwa.\n"
            "6. **Dane zewnętrzne:** Wklej fragment raportu 10-Q/10-K, a prześwietlę go dla Ciebie.\n\n"
            "O czym chciałbyś porozmawiać?"
        )
