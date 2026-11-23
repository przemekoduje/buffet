"""
Kompleksowy Bank Wiedzy Aplikacji BUFFET (przemokoduje.com - Moduł IV)
Zawiera pełną dokumentację każdego wskaźnika, wzoru matematycznego,
kryterium punktowego, techniki wyceny oraz zasad zarządzania kapitałem.
"""

from typing import Dict, Any, List, Optional

KNOWLEDGE_TOPICS: Dict[str, Dict[str, Any]] = {
    "philosophy": {
        "id": "philosophy",
        "title": "Filozofia Inwestowania w Wartość i Reguła Nr 1",
        "category": "Foundations",
        "keywords": ["filozofia", "zasady", "reguła 1", "regula 1", "buffett", "munger", "misja", "wartość"],
        "summary": "Inwestowanie w wartość traktuje akcję jako ułamek realnego przedsiębiorstwa, a nadrzędnym celem jest bezwzględna ochrona kapitału.",
        "content": """
### 1. Filozofia Inwestowania w Wartość (Value Investing)

Aplikacja **BUFFET** jest czwartym modułem platformy **przemokoduje.com**, zaprojektowanym w 100% według szkoły Warrena Buffetta, Charliego Mungera i Benjamina Grahama.

#### Główne Filary Myślenia:
1. **Akcja to ułamek biznesu:** Nie traktujemy akcji jako wirtualnego symbolu na wykresie podlegającego spekulacji technicznej, lecz jako proporcjonalną własność realnego przedsiębiorstwa posiadającego fabryki, klientów, patenty i przepływy pieniężne.
2. **Pan Rynek (Mr. Market):** Rynek giełdowy jest jak emocjonalny partner biznesowy, który codziennie podaje cenę, za którą jest gotów odkupić Twoje udziały lub sprzedać swoje. Kiedy popada w nieuzasadnioną euforię – ceny są za wysokie; kiedy wpada w panikę lub depresję – oferuje wspaniałe firmy za ułamek ich realnej wartości.
3. **Reguła Nr 1 (Ochrona Kapitału):**
   * *„Zasada 1: Nigdy nie trać pieniędzy.”*
   * *„Zasada 2: Zawsze pamiętaj o zasadzie numer jeden.”*
   * Matematyka strat jest bezlitosna: strata 50% kapitału wymaga zysku 100%, aby wyjść na zero. Strata 80% wymaga zysku 400%. Dlatego w aplikacji BUFFET priorytetem jest unikanie katastrofalnych błędów.
4. **Krąg Kompetencji (Circle of Competence):** Inwestujemy wyłącznie w biznesy, których model ekonomiczny, źródła przychodów i zagrożenia konkurencyjne rozumiemy w horyzoncie 10–20 lat.
"""
    },
    "four_filters": {
        "id": "four_filters",
        "title": "Cztery Filtry Selekcyjne Warrena Buffetta",
        "category": "Strategy",
        "keywords": ["filtry", "4 filtry", "cztery filtry", "selekcja", "fosa", "zarząd", "kryteria"],
        "summary": "Czteroetapowe sito weryfikujące fosę ekonomiczną, bezpieczeństwo bilansu, jakość zarządu oraz cenę.",
        "content": """
### 2. Cztery Filtry Selekcyjne Buffetta

Każda spółka wprowadzana do analizy w aplikacji BUFFET podlega 4-etapowemu audytowi:

1. **Filtr 1: Zrozumiały biznes i trwała fosa ekonomiczna (Economic Moat):**
   - Spółka posiada unikalną przewagę konkurencyjną chroniącą jej wysokie zyski przed atakiem rywali.
   - Źródła fosy: siła marki (np. Coca-Cola, Apple), wysokie koszty zmiany dostawcy (np. Microsoft, Adobe), efekt sieciowy (np. Visa, Mastercard) lub przewaga niskich kosztów skali (np. Costco, Walmart).
   - Metryki twarde w aplikacji: **ROIC >= 15%** oraz **Marża Brutto >= 40%**.
2. **Filtr 2: Bezpieczny bilans i odporność na kryzysy (Zasada 1):**
   - Spółka nie może być uzależniona od łaski banków ani rolowania długu w środowisku wysokich stóp procentowych.
   - Metryki twarde: **Dług Netto / FCF <= 2.5 roku** (maksymalnie 4.0 lata), **Płynność Bieżąca (Current Ratio) > 1.2**.
3. **Filtr 3: Uczciwy i kompetentny zarząd (Shareholder-Friendly Management):**
   - Zarząd traktuje akcjonariuszy jak długoletnich partnerów, alokuje kapitał z chirurgiczną precyzją, nie rozwadnia akcji opcjami menedżerskimi (Stock-Based Compensation) i skupuje akcje (Buybacks) tylko przy ich niedowartościowaniu.
   - Metryki twarde: **ROE >= 15-18%**, stabilny wzrost zysku na akcję, powściągliwość w fuzjach i przejęciach.
4. **Filtr 4: Margines Bezpieczeństwa (Margin of Safety):**
   - Nawet wspaniała spółka staje się złą inwestycją, jeśli zapłacisz za nią zbyt wygórowaną cenę.
   - Wymóg: Zakup z dyskontem minimum 15–30% względem konserwatywnej wartości wewnętrznej (DCF na bazie Owner Earnings).
"""
    },
    "owner_earnings": {
        "id": "owner_earnings",
        "title": "Zysk Właścicielski (Owner Earnings) i Normalizacja Przepływów",
        "category": "Valuation",
        "keywords": ["owner earnings", "zysk właścicielski", "capex", "fcf", "przepływy", "wzór owner earnings"],
        "summary": "Kluczowa koncepcja Buffetta mierząca realną gotówkę do dyspozycji właściciela po odliczeniu CapExu utrzymaniowego.",
        "content": """
### 3. Zysk Właścicielski (Owner Earnings)

Warren Buffett zdefiniował to pojęcie w Liście do Akcjonariuszy Berkshire Hathaway w 1986 roku jako jedyną prawdziwą miarę zdolności przedsiębiorstwa do generowania wartości.

#### Wzór Matematyczny:
$$\\text{Owner Earnings} = \\text{Zysk Netto} + \\text{Amortyzacja (D&A)} - \\text{CapEx Utrzymaniowy (Maintenance CapEx)}$$

#### Dlaczego Zysk Netto i EBITDA wprowadzają w błąd?
- **Zysk Netto (Net Income):** Zawiera niegotówkowe zapisy księgowe i ignoruje konieczność ciągłego reinwestowania w maszyny i infrastrukturę.
- **EBITDA:** Pomija koszty odsetek, podatków i co najważniejsze – zużycie kapitału (CapEx). Buffett nazywa EBITDA „wskaźnikiem oszustów”, pytając: *„Czy zarząd uważa, że to zębowa wróżka opłaca nowe fabryki i sprzęt?”*.

#### Algorytm Normalizacji w Aplikacji BUFFET:
1. **Podstawowa baza:** Wolne Przepływy Pieniężne (Free Cash Flow TTM = Przepływy Operacyjne minus Całkowity CapEx).
2. **Korekta CapEx Rozwojowego (Growth vs Maintenance):**
   - Jeśli spółka ponosi gigantyczne nakłady inwestycyjne o charakterze czysto rozwojowym (np. centra danych AI w Alphabet/Microsoft), algorytm nie karze jej za te inwestycje.
   - Gdy FCF TTM jest przejściowo ujemny lub zaniżony, aplikacja normalizuje go 5-letnią średnią historyczną FCF lub konserwatywnym 70% Zysku Netto.
3. **Wygładzanie wahań:** W przypadku jednorazowych zdarzeń (np. spłata podatku przez Coca-Colę, skoki floatu ubezpieczeniowego Berkshire), wynik jest ważony średnią wieloletnią.
"""
    },
    "dcf_model": {
        "id": "dcf_model",
        "title": "Model 10-letniego DCF i Wartość Wewnętrzna (Intrinsic Value)",
        "category": "Valuation",
        "keywords": ["dcf", "wycena", "intrinsic value", "wartość wewnętrzna", "stopa dyskontowa", "terminal value", "gordona"],
        "summary": "Konserwatywny, dynamiczny model DCF z dyskontem stałym, etapowym wygaszaniem wzrostu i korektą bilansową.",
        "content": """
### 4. Dynamiczny 10-letni Model DCF (Discounted Cash Flow)

Wycena Wartości Wewnętrznej (*Intrinsic Value*) określa, ile gotówki przedsiębiorstwo wygeneruje dla inwestora od dnia dzisiejszego do końca swojego istnienia, zdyskontowanej do wartości bieżącej.

#### Etapy Kalkulacji w Aplikacji:
1. **Lata 1–5 (Faza Pierwszego Wzrostu $g_1$):**
   - Stopa wzrostu bazuje na 5-letnim CAGR przychodów firmy pomnożonym przez bufor konserwatywny $0.85$.
   - **Twarde limity skali (Caps):**
     * Mega-Cap (> $500 mld kapitalizacji): max 11.0% rocznie.
     * Duże spółki (> $200 mld): max 13.0% rocznie.
     * Sektor finansowo-ubezpieczeniowy: max 7.0% rocznie.
     * Pozostałe spółki: max 16.0% rocznie.
2. **Lata 6–10 (Faza Wygaszania / Fade-down $g_2$):**
   - Zgodnie z prawami konkurencji rentowność dąży do średniej: $g_2 = 0.60 \\times g_1$, z ograniczeniem do przedziału $[3.0\\%, 8.0\\%]$.
3. **Wartość Rezydualna / Terminal Value (Model Gordona):**
   - Założenie nieskończonego wzrostu o stopie $g_t = 3.0\\%$ (tempo wzrostu globalnego PKB).
   - $\\text{Terminal Value} = \\frac{\\text{CF}_{10} \\times (1 + g_t)}{r - g_t}$
   - $\\text{PV(Terminal Value)} = \\frac{\\text{Terminal Value}}{(1 + r)^{10}}$
4. **Stopa Dyskontowa ($r$ - Hurdle Rate Buffetta):**
   - Buffett odrzuca zmienny rynkowy model CAPM/Beta. Zamiast tego stosuje stałe stopy poprzeczki inwestycyjnej:
     * **9.0%** – dla spółek o zerowym/niskim długu (Net Debt / FCF <= 2.5) i marży brutto >= 35%.
     * **9.5%** – dla spółek o umiarkowanym zadłużeniu (Net Debt / FCF <= 4.0).
     * **10.5%** – dla spółek o podwyższonej dźwigni finansowej.
5. **Korekta o Dług Netto i Gotówkę (Enterprise Value -> Equity Value):**
   - $\\text{Equity Value} = \\text{PV(Przepływy 1-10)} + \\text{PV(Terminal Value)} - \\text{Dług Netto}$
   - Ujemny dług netto oznacza gotówkę netto (dodatkowa wartość dla akcjonariusza).
   - *Specjalna reguła finansowa:* Dla banków i ubezpieczycieli (np. BRK.B, JPM) gotówka w bilansie stanowi float regulacyjny i rezerwy na wypłaty odszkodowań — algorytm uwzględnia maksymalnie 35% gotówki netto jako wolną nadwyżkę.
6. **Wartość Wewnętrzna na Jedną Akcję:**
   - $\\text{Intrinsic Value per share} = \\frac{\\text{Equity Value}}{\\text{Liczba Rozwodnionych Akcji}}$
7. **Margines Bezpieczeństwa (Margin of Safety - MoS):**
   - $\\text{MoS (\\%)} = \\frac{\\text{Intrinsic Value} - \\text{Aktualny Kurs}}{\\text{Intrinsic Value}} \\times 100\\%$
"""
    },
    "buffett_score": {
        "id": "buffett_score",
        "title": "Metodologia Punktacji Buffett Score (0 - 100 pkt)",
        "category": "Scoring",
        "keywords": ["buffett score", "score buffetta", "punktacja", "skala punktowa", "rekomendacje", "kryteria punktowe"],
        "summary": "Obiektywna, syntetyczna ocena fundamentalna spółki w 6 kluczowych wymiarach Buffetta.",
        "content": """
### 5. Metodologia Buffett Score (0 - 100 pkt)

Buffett Score to ważona ocena kondycji fundamentalnej spółki. Maksymalnie spółka może uzyskać 100 punktów podzielonych na 6 filarów:

| Filar Oceny | Kryterium i Progi | Punkty | Interpretacja |
| :--- | :--- | :---: | :--- |
| **1. ROIC (Zwrot z Kapitału)** | ROIC >= 18%<br>ROIC 12% - 18%<br>ROIC < 12% | **20 pkt**<br>14 pkt<br>4 pkt | Kluczowy dowód trwałej fosy ekonomicznej i efektywności alokacji kapitału. |
| **2. ROE (Rentowność Własna)** | ROE >= 18%<br>ROE 12% - 18%<br>ROE < 12% | **15 pkt**<br>10 pkt<br>2 pkt | Sprawność generowania zysków z kapitału powierzonego przez akcjonariuszy. |
| **3. Pricing Power (Marża Brutto)** | Marża >= 45%<br>Marża 30% - 45%<br>Marża < 30% | **15 pkt**<br>10 pkt<br>3 pkt | Zdolność do podnoszenia cen bez utraty klientów w warunkach inflacji. |
| **4. Bezpieczeństwo Długu (Net Debt/FCF)** | Gotówka Netto (Dług <= 0)<br>Dług/FCF <= 2.5 roku<br>Dług/FCF 2.5 - 4.0 lat<br>Dług/FCF > 4.0 lat | **20 pkt**<br>18 pkt<br>10 pkt<br>0 pkt | Liczba lat wolnych przepływów potrzebnych do całkowitej spłaty zadłużenia netto. |
| **5. Margines Bezpieczeństwa (MoS)** | MoS >= +30%<br>MoS +15% do +30%<br>MoS 0% do +15%<br>MoS < 0% (przewartościowana) | **20 pkt**<br>14 pkt<br>8 pkt<br>0 pkt | Dyskonto ceny rynkowej do konserwatywnej wartości wewnętrznej DCF. |
| **6. Stabilność Wzrostu (CAGR 5y)** | CAGR Przychodów >= 8%<br>CAGR 3% - 8%<br>CAGR < 3% | **10 pkt**<br>6 pkt<br>2 pkt | Dowód długoterminowego popytu na produkty i usługi przedsiębiorstwa. |

#### Klasy Rekomendacji:
- **STRONG_BUY (Kupuj zdecydowanie):** Score >= 80 pkt, Margines Bezpieczeństwa >= 20% oraz Poziom Ryzyka Reguły 1 = LOW.
- **BUY (Kupuj):** Score >= 65 pkt oraz Margines Bezpieczeństwa >= 10%.
- **HOLD (Trzymaj / Obserwuj):** Score >= 50 pkt lub Margines Bezpieczeństwa >= -10%. Dobre spółki, ale bez odpowiedniego dyskonta cenowego.
- **AVOID (Unikaj):** Score < 50 pkt lub wysoki dług / skrajne przewartościowanie.
"""
    },
    "rule_one_risk": {
        "id": "rule_one_risk",
        "title": "Reguła Nr 1: Audyt Ryzyka i Sygnały Ostrzegawcze",
        "category": "Risk",
        "keywords": ["reguła 1", "ryzyko", "ostrzeżenia", "bezpieczeństwo", "low", "moderate", "high"],
        "summary": "System wczesnego ostrzegania przed utratą kapitału badający 4 krytyczne patologie bilansowe.",
        "content": """
### 6. Audyt Ryzyka wg Reguły Nr 1 (Rule #1 Risk)

Zgodnie z naukami Buffetta, ryzyko nie wynika ze zmienności kursu (Beta), lecz z prawdopodobieństwa trwałej utraty kapitału (*permanent loss of capital*).

#### Cztery Sygnały Ostrzegawcze:
1. **Dźwignia Finansowa:** Net Debt / FCF > 4.5 roku (spółka potrzebuje ponad 4.5 roku wolnej gotówki na spłatę długu).
2. **Płynność Bieżąca:** Current Ratio < 1.0 (zobowiązania krótkoterminowe przewyższają aktywa obrotowe – ryzyko zatorów płatniczych).
3. **Ekstremalna Wycena:** Margines Bezpieczeństwa < -25% (inwestor płaci ponad 25% premii ponad wartość wewnętrzną biznesu).
4. **Niska Rentowność:** ROIC < 8% (biznes nie pokrywa swojego kosztu kapitału, niszcząc wartość dla akcjonariuszy).

#### Poziomy Klasyfikacji Ryzyka:
- **LOW (Niskie):** 0 sygnałów ostrzegawczych. Spółka o nieskazitelnym bilansie i silnej fosie.
- **MODERATE (Umiarkowane):** 1–2 sygnały ostrzegawcze. Biznes solidny, lecz wymaga wzmożonej czujności.
- **HIGH (Wysokie):** 3 lub 4 sygnały ostrzegawcze. Spółka narusza fundamentalną Regułę Nr 1 — bezwzględny zakaz otwierania nowych pozycji.
"""
    },
    "portfolio_money_management": {
        "id": "portfolio_money_management",
        "title": "Portfel Paper Trading i Zasady Money Management",
        "category": "Portfolio",
        "keywords": ["portfel", "paper trading", "money management", "alfa", "rezerwa", "stop loss", "take profit", "wielkość pozycji"],
        "summary": "Zasady prowadzenia wirtualnego portfela, dyscyplina kapitałowa i wskaźnik Alfa Buffetta.",
        "content": """
### 7. Portfel Paper Trading i Money Management

Moduł Portfela służy do testowania skuteczności strategii Buffetta w czasie rzeczywistym (Forward-Testing) bez ryzykowania prawdziwych oszczędności.

#### Parametry i Domyślne Reguły Zarządzania Kapitałem:
- **Kapitał początkowy:** $100 000 USD (wirtualny bilans demo).
- **Domyślna wielkość 1 pozycji:** 10.0% kapitału portfela ($10 000 USD).
- **Maksymalna alokacja w 1 spółkę:** 20.0% - 25.0% (zasada rozsądnej koncentracji Buffetta: *„Dywersyfikacja to ochrona przed ignorancją. Nie ma sensu, jeśli wiesz, co robisz”*).
- **Maksymalna liczba pozycji:** 10–15 spółek (skupienie na najlepszych pomysłach zamiast rozdrabniania).
- **Minimalna rezerwa gotówki (Cash Reserve):** 10.0% - 15.0% portfela. Gotówka musi być zawsze dostępna w portfelu jako „suchy proch” na zakupy w dołkach rynkowych.
- **Zlecenie obronne Stop Loss:** Domyślnie 15.0% poniżej ceny zakupu (ochrona przed błędem w analizie fundamentalnej).
- **Zlecenie realizacji zysków Take Profit:** Domyślnie 35.0% - 40.0% powyżej ceny zakupu (moment na realizację zysków lub ponowne przeliczenie wyceny DCF).
- **Akcje ułamkowe (Fractional Shares):** Pełna obsługa ułamków akcji pozwala precyzyjnie alokować kapitał nawet w drogie walory (np. Berkshire Hathaway BRK.A / BRK.B).

#### Wskaźnik Alfa Buffetta:
$$\\text{Alfa (\\%)} = \\text{Stopa Zwrotu Portfela (\\%)} - \\text{Średnia Stopa Zwrotu S&P 500 (\\%)}$$
- Pokazuje czystą wartość dodaną selekcji spółek w wartość ponad pasywne trzymanie indeksu szerokiego rynku.
"""
    },
    "screener_baskets": {
        "id": "screener_baskets",
        "title": "Skaner Rynku (Screener), Koszyki i Alerty Sesyjne",
        "category": "Screener",
        "keywords": ["screener", "skaner", "koszyki", "alerty", "intraday", "eod", "us_quality", "sp500_value", "aristocrats"],
        "summary": "Automatyczny monitoring uniwersum akcji z podziałem na 3 koszyki oraz alerty intraday i EOD.",
        "content": """
### 8. Skaner Rynku (Screener) i Koszyki Tematyczne

Skaner przeszukuje uniwersum giełdowe i automatycznie klasyfikuje spółki do 3 wyspecjalizowanych koszyków:

1. **`us_quality` (Jakość USA & Silna Fosa):**
   - Elitarne amerykańskie korporacje o ugruntowanej marce, dominującej pozycji i powtarzalnym popycie (np. Apple, Microsoft, Alphabet, Visa, Coca-Cola, Johnson & Johnson).
2. **`sp500_value` (S&P 500 Promocje / Wartość):**
   - Spółki z indeksu S&P 500 notowane z największym dyskontem do wyceny Intrinsic Value, gdzie rynek nadmiernie ukarał kurs za przejściowe trudności.
3. **`dividend_aristocrats` (Arystokraci Dywidendy):**
   - Spółki podnoszące dywidendę nieprzerwanie od co najmniej 25 lat, z bezpiecznym wskaźnikiem wypłaty zysków (Payout Ratio < 60%).

#### Tryby i Harmonogram Skanera:
- **Skan Sesyjny EOD (End of Day):** Uruchamiany automatycznie po zamknięciu giełd w Nowym Jorku (ok. godz. 22:15 czasu polskiego). Przelicza pełne bilanse, Owner Earnings i Buffett Score.
- **Alerty Intraday (w trakcie sesji):** Szybki monitoring cen co 15 minut (w godzinach 15:30 – 22:00 CET), wykrywający natychmiastowe okazje cenowe lub gwałtowne wyprzedaże.
"""
    },
    "financial_metrics_glossary": {
        "id": "financial_metrics_glossary",
        "title": "Encyklopedia Wszystkich Wskaźników Finansowych",
        "category": "Metrics",
        "keywords": ["wskaźniki", "metryki", "pe", "roic", "roe", "fcf", "marża", "altman", "current ratio", "dividend yield"],
        "summary": "Szczegółowy słownik i formuły wszystkich wskaźników fundamentalnych obecnych w aplikacji.",
        "content": """
### 9. Kompletny Słownik Wskaźników Finansowych w BUFFET

- **ROIC (Return on Invested Capital / Zwrot z Zainwestowanego Kapitału):**
  * Wzór: $\\text{ROIC} = \\frac{\\text{NOPAT}}{\\text{Kapitał Własny} + \\text{Dług Długoterminowy} - \\text{Gotówka}}$
  * Dlaczego to ulubiony wskaźnik Buffetta: Mierzy ile groszy czystego zysku operacyjnego firma generuje z każdego dolara włożonego w fabryki i operacje. Próg Buffetta: min. 15%.
- **ROE (Return on Equity / Zwrot z Kapitału Własnego):**
  * Wzór: $\\text{ROE} = \\frac{\\text{Zysk Netto}}{\\text{Kapitał Własny}}$
  * Mierzy rentowność kapitału należącego do akcjonariuszy. Uwaga: może być sztucznie zawyżony wysokim długiem, dlatego w aplikacji zawsze analizowany jest w parze z ROIC.
- **Marża Brutto (Gross Margin):**
  * Wzór: $\\frac{\\text{Przychody} - \\text{Koszt Własny Sprzedaży (COGS)}}{\\text{Przychody}} \\times 100\\%$
  * Kluczowy wskaźnik siły cenowej (Pricing Power). Wynik powyżej 40-45% świadczy o trwałej przewadze konkurencyjnej.
- **Marża Operacyjna (Operating Margin):**
  * Wzór: $\\frac{\\text{Zysk Operacyjny (EBIT)}}{\\text{Przychody}} \\times 100\\%$
  * Wskazuje na efektywność kosztów stałych i zarządu.
- **FCF TTM (Free Cash Flow Trailing Twelve Months):**
  * Wzór: $\\text{Operating Cash Flow} - \\text{Capital Expenditures (CapEx)}$
  * Realna gotówka wygenerowana w ciągu ostatnich 12 miesięcy.
- **Net Debt (Dług Netto):**
  * Wzór: $\\text{Zadłużenie Całkowite (Krótko- i Długoterminowe)} - \\text{Gotówka i Ekwiwalenty}$
  * Ujemna wartość oznacza nadwyżkę gotówki netto.
- **Net Debt / FCF (Lata spłaty długu):**
  * Wzór: $\\frac{\\text{Dług Netto}}{\\text{FCF TTM}}$
  * Określa w ile lat firma spłaciłaby dług, przeznaczając na to całą gotówkę. Norma Buffetta: < 2.5–3.0 lat.
- **Current Ratio (Płynność Bieżąca):**
  * Wzór: $\\frac{\\text{Aktywa Obrotowe}}{\\text{Zobowiązania Krótkoterminowe}}$
  * Bezpieczny poziom to > 1.2–1.5. Wartość < 1.0 oznacza zagrożenie zatorami płatniczymi.
- **Altman Z-Score:**
  * Wieloczynnikowy model ekonometryczny przewidujący prawdopodobieństwo bankructwa firmy w ciągu 2 lat.
  * Z > 3.0: Strefa Bezpieczna (Safe Zone).
  * 1.8 < Z < 3.0: Strefa Szara (Grey Zone).
  * Z < 1.8: Strefa Zagrożenia (Distress Zone).
- **P/E (Price to Earnings / C/Z):**
  * Kurs akcji / Zysk na akcję (EPS). Pokazuje ile lat zysków płacimy za firmę.
- **P/FCF (Cena do Wolnych Przepływów):**
  * Kurs akcji / FCF na akcję. Trudniejszy do sfałszowania księgowo odpowiednik P/E.
- **Dividend Yield (Stopa Dywidendy):**
  * Roczna dywidenda na akcję / Aktualny kurs.
- **Payout Ratio (Wskaźnik Wypłaty Dywidendy):**
  * Dywidenda całkowita / Zysk Netto. Bezpieczny poziom < 60% (dla REIT-ów do 90%).
- **CAGR Przychodów 5y (Compound Annual Growth Rate):**
  * Średnioroczna stopa wzrostu przychodów w ciągu ostatnich 5 lat.
"""
    },
    "firebase_architecture": {
        "id": "firebase_architecture",
        "title": "Architektura Danych, Firebase Firestore i Bezpieczeństwo",
        "category": "Infrastructure",
        "keywords": ["firebase", "firestore", "chmura", "zapis", "synchronizacja", "auth", "google sign in"],
        "summary": "Mechanizm trwałego przechowywania danych użytkownika w chmurze Google Firebase Firestore Native.",
        "content": """
### 10. Architektura Danych i Integracja z Google Cloud Firebase

Aplikacja BUFFET łączy zalety lokalnego buforowania z bezpieczną architekturą chmurową:

#### Integracja z Firebase:
- **Dedykowany Projekt:** `buffet` (`buffet-3620c`) w regionie `europe-west1` (Frankfurt / Europa Zachodnia).
- **Baza Danych:** Google Cloud Firestore w trybie Native.
- **Kolekcja użytkowników:** `buffet_users/{uid}`.
- **Zawartość dokumentu użytkownika w chmurze:**
  * Stan konta gotówkowego i historia zrealizowanych zleceń Paper Trading.
  * Otwarte pozycje akcyjne z cenami zakupu i wielkościami.
  * Indywidualna konfiguracja parametrów Money Management (limity pozycji, stop loss, rezerwa).
  * Lista obserwowanych spółek (Watchlist).
- **Uwierzytelnianie (Firebase Auth):**
  * 1-klikowe logowanie przez konto Google (OAuth popup).
  * Rejestracja i logowanie adresem e-mail i hasłem.
  * Tryb Gościa (praca na pamięci lokalnej z możliwością późniejszego przypięcia konta).
- **Bezpieczeństwo Poświadczeń:**
  * Klucze administracyjne (`firebase-adminsdk.json`) są zabezpieczone po stronie backendu i wykluczone z repozytorium Gita.
"""
    }
}

def get_full_knowledge_document() -> str:
    """Zwraca kompletny dokument wiedzy o aplikacji w formacie Markdown."""
    parts = ["# ENCYKLOPEDIA I BANK WIEDZY APLIKACJI BUFFET (przemokoduje.com)\n"]
    for topic in KNOWLEDGE_TOPICS.values():
        parts.append(topic["content"])
        parts.append("\n---\n")
    return "\n".join(parts)

def get_topics_list() -> List[Dict[str, Any]]:
    """Zwraca metadane wszystkich tematów w banku wiedzy."""
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "category": t["category"],
            "summary": t["summary"],
            "keywords": t["keywords"]
        }
        for t in KNOWLEDGE_TOPICS.values()
    ]

def get_topic_by_id(topic_id: str) -> Optional[Dict[str, Any]]:
    """Zwraca pełny temat z banku wiedzy po jego identyfikatorze."""
    return KNOWLEDGE_TOPICS.get(topic_id)

import re

def find_relevant_knowledge(query: str) -> List[Dict[str, Any]]:
    """Wyszukuje najbardziej pasujące sekcje banku wiedzy dla danego zapytania."""
    q = query.lower()
    matches = []
    for topic in KNOWLEDGE_TOPICS.values():
        score = 0
        for kw in topic["keywords"]:
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, q):
                score += 5 + len(kw)
        if any(re.search(r'\b' + re.escape(word) + r'\b', q) for word in topic["title"].lower().split() if len(word) > 3):
            score += 2
        if score > 0:
            matches.append((score, topic))
    
    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches]
