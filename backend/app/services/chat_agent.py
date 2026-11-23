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

## 2. CZTERY FILTRY WARRENA BUFFETTA
1. **Trwała fosa ekonomiczna (Economic Moat):** ROIC >= 12-18% oraz Marża Brutto >= 40-45% (dowód Pricing Power).
2. **Bezpieczny bilans (Reguła nr 1):** Net Debt / FCF < 2.5 roku (max 4.0 lata), Current Ratio > 1.2.
3. **Uczciwy i kompetentny zarząd:** Wysoki ROE >= 15-18%, mądra alokacja kapitału, regularne skupy akcji (Buybacks) przy niskich wycenach.
4. **Margines Bezpieczeństwa (Margin of Safety - MoS):** 10-letni DCF na bazie Znormalizowanego Zysku Właścicielskiego (Owner Earnings) z dyskontem min. 15-30%.

## 3. MODEL WYCENY: NORMALIZOWANY OWNER EARNINGS & 10-LETNI DCF
- Wzór Buffetta: Owner Earnings = Zysk Netto + Amortyzacja (D&A) - Roczne Wydatki Inwestycyjne Utrzymaniowe (Maintenance CapEx).
- Dynamiczne założenia 10-letniego DCF:
  * Lata 1-5: 5-letni CAGR przychodów * 0.85 (max 11% dla firm >$500 mld, max 13% dla firm >$200 mld, max 7% dla finansów).
  * Lata 6-10: Fade-down do 60% tempa z lat 1-5 (pomiędzy 3.0% a 8.0%).
  * Wartość Rezydualna: Model Gordona ze stopą wieczystą gt = 3.0% (tempo wzrostu PKB).
  * Stopa Dyskontowa: Stały koszt alternatywny kapitału Buffetta (9.0% dla bezpiecznych, 9.5% średnich, 10.5% podwyższonego długu).
  * Korekta o bilans: Equity Value = PV(Przepływy 1-10) + PV(Wartość Rezydualna) - Dług Netto.
  * Margines Bezpieczeństwa: MoS = ((Wartość Wewnętrzna - Kurs) / Wartość Wewnętrzna) * 100%.

## 4. METODOLOGIA BUFFETT SCORE (0 - 100 PKT)
1. ROIC (max 20 pkt): >=18% (20 pkt), 12-18% (14 pkt), <12% (4 pkt).
2. ROE (max 15 pkt): >=18% (15 pkt), 12-18% (10 pkt), <12% (2 pkt).
3. Marża Brutto (max 15 pkt): >=45% (15 pkt), 30-45% (10 pkt), <30% (3 pkt).
4. Bezpieczeństwo Zadłużenia (max 20 pkt): Gotówka netto (20 pkt), <=2.5 roku FCF (18 pkt), 2.5-4.0 lat (10 pkt), >4.0 lat (0 pkt).
5. Margines Bezpieczeństwa (max 20 pkt): MoS >=30% (20 pkt), 15-30% (14 pkt), 0-15% (8 pkt), <0% (0 pkt).
6. Wzrost Przychodów (max 10 pkt): CAGR >=8% (10 pkt), 3-8% (6 pkt), <3% (2 pkt).

## 5. MODUŁ PORTFEL PAPER TRADING & MONEY MANAGEMENT
- Wirtualny kapitał startowy: $100 000 USD.
- Pozycja 10%, max alokacja w 1 spółkę 20-25%, max 10-15 spółek w portfelu.
- Rezerwa gotówkowa: minimum 10-15% w gotówce na okazje rynkowe.
- Stop Loss 15%, Take Profit 35-40%.
- Alfa Buffetta: Stopa Zwrotu Portfela (%) - Średnia Stopa Zwrotu S&P 500 (%).
"""

class ChatAgent:
    """
    Wszechwiedzący Asystent Inwestycyjny i Ekspert Aplikacji BUFFET.
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
        # Ignoruj pojedyncze litery jak "A" lub "B" jeśli nie ma kropki
        found = [c for c in candidates if c in known_stocks and (len(c) > 1 or "." in c)]
        
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
                last_user_msg = m.get("content", "").strip()
                break

        lower_msg = last_user_msg.lower()

        # 1. Rozpoznawanie intencji użytkownika
        wants_portfolio = any(w in lower_msg for w in [
            "portfel", "portfolio", "moim portfelu", "mój portfel", "mojego portfela",
            "konto", "pozycje", "gotówk", "p&l", "zysk", "strat", "alfa", "ile mam", "stan konta"
        ])
        wants_screener = any(w in lower_msg for w in [
            "okazj", "rekomendacj", "co kupić", "ranking", "screener", "tanie", "niedowartościowan", "promocj"
        ])
        wants_owner_earnings = any(w in lower_msg for w in [
            "owner earnings", "zysk właścicielski", "właścicielsk", "capex"
        ])
        wants_score = any(w in lower_msg for w in [
            "buffett score", "score", "punktacja", "jak liczycie score", "kryteria oceny", "skala"
        ])
        wants_dcf = any(w in lower_msg for w in [
            "dcf", "wycen", "intrinsic value", "wartość wewnętrzna", "stopa dyskontowa"
        ])
        wants_mm = any(w in lower_msg for w in [
            "money management", "zarządzanie kapitałem", "rezerwa", "stop loss", "take profit", "wielkość pozycji"
        ])

        context_data: Dict[str, Any] = {}

        # 2. Obsługa portfela
        if (wants_portfolio or "portfel" in lower_msg) and db:
            summary = PortfolioTracker.get_portfolio_summary(db)
            raw_holdings = summary.get("holdings") or []
            context_data["user_portfolio"] = {
                "total_portfolio_value": summary.get("total_portfolio_value", 100000.0),
                "cash_balance": summary.get("cash_balance", 100000.0),
                "total_pnl_pct": summary.get("total_pnl_pct", 0.0),
                "alpha_pct": summary.get("alpha_pct", 0.0),
                "positions_count": summary.get("positions_count", len(raw_holdings)),
                "rule_1_compliance": summary.get("rule_1_compliance", "100%"),
                "holdings": [
                    {
                        "ticker": h.get("ticker") if isinstance(h, dict) else getattr(h, "ticker", ""),
                        "company_name": h.get("company_name") if isinstance(h, dict) else getattr(h, "company_name", ""),
                        "shares": h.get("shares") if isinstance(h, dict) else getattr(h, "shares", 0),
                        "entry_price": h.get("entry_price") if isinstance(h, dict) else getattr(h, "entry_price", 0),
                        "current_price": h.get("current_price") if isinstance(h, dict) else getattr(h, "current_price", 0),
                        "pnl_pct": h.get("unrealized_pnl_pct") or (h.get("pnl_pct") if isinstance(h, dict) else getattr(h, "pnl_pct", 0.0)),
                        "weight_pct": h.get("weight_pct") if isinstance(h, dict) else getattr(h, "weight_pct", 0.0)
                    }
                    for h in raw_holdings
                ],
                "mm_rules": summary.get("mm_config", {})
            }

        # 3. Obsługa Screenera
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

        # 4. Obsługa tickerów spółek (tylko gdy użytkownik wprost pyta o spółkę)
        explicit_tickers = cls._extract_tickers(last_user_msg)
        refers_to_active = any(w in lower_msg for w in ["ta spółka", "tej spółk", "jej", "kurs", "wycen", "kupić", "sprzedać", "fosa", "margines", "czy warto"])
        
        tickers_to_fetch = list(explicit_tickers)
        if not wants_portfolio and not wants_screener and not wants_owner_earnings and not wants_score and not wants_dcf and not wants_mm:
            if context_ticker and context_ticker not in tickers_to_fetch:
                if refers_to_active or len(lower_msg.split()) <= 4:
                    tickers_to_fetch.append(context_ticker)

        provider = get_market_provider()
        stocks_info = []
        for t in tickers_to_fetch[:3]:
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

        # 5. Generowanie odpowiedzi (z modelem LLM lub precyzyjnym fallbackiem)
        reply = await cls._generate_ai_response(
            messages=messages,
            context_data=context_data,
            custom_data=custom_data,
            intents={
                "wants_portfolio": wants_portfolio,
                "wants_screener": wants_screener,
                "wants_owner_earnings": wants_owner_earnings,
                "wants_score": wants_score,
                "wants_dcf": wants_dcf,
                "wants_mm": wants_mm,
                "explicit_stock": bool(explicit_tickers)
            }
        )

        # 6. Sugerowane akcje dla interfejsu
        suggested_actions = []
        if wants_portfolio:
            suggested_actions.append({"label": "Otwórz Portfel Paper Trading", "action": "NAVIGATE_TAB", "tab": "portfolio"})
        if wants_screener:
            suggested_actions.append({"label": "Przejdź do Screenera", "action": "NAVIGATE_TAB", "tab": "screener"})
        if stocks_info:
            top_t = stocks_info[0]["ticker"]
            suggested_actions.append({"label": f"Otwórz Deep Dive {top_t}", "action": "OPEN_TICKER", "ticker": top_t})
            if stocks_info[0]["margin_of_safety_pct"] > 0:
                suggested_actions.append({"label": f"Zlecenie KUP {top_t}", "action": "ORDER_BUY", "ticker": top_t})

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
        custom_data: Optional[str] = None,
        intents: Optional[Dict[str, bool]] = None
    ) -> str:
        gemini_key = settings.GEMINI_API_KEY
        intents = intents or {}

        # Próba wywołania Gemini AI
        if gemini_key:
            system_prompt = f"""Jesteś Warrenem Buffettem i doradcą inwestycyjnym w aplikacji BUFFET (przemokoduje.com).
Odpowiadasz mądrze, spokojnie, w stylu listów do akcjonariuszy Berkshire Hathaway.
Zasada nr 1: Nigdy nie trać pieniędzy. Zasada nr 2: Pamiętaj o zasadzie nr 1.

Aktualny kontekst systemowy pobrany dla tego zapytania:
{json.dumps(context_data, ensure_ascii=False, indent=2) if context_data else "Brak specyficznego kontekstu."}
{f"Dane od użytkownika: {custom_data}" if custom_data else ""}
"""
            raw_contents = []
            for m in messages:
                role = "user" if m.get("role") == "user" else "model"
                txt = m.get("content", "").strip()
                if txt:
                    raw_contents.append({"role": role, "parts": [{"text": txt}]})

            while raw_contents and raw_contents[0]["role"] != "user":
                raw_contents.pop(0)

            alternating = []
            last_role = None
            for c in raw_contents:
                if c["role"] != last_role:
                    alternating.append(c)
                    last_role = c["role"]
                else:
                    alternating[-1]["parts"][0]["text"] += "\n\n" + c["parts"][0]["text"]

            if alternating:
                payload = {
                    "contents": alternating,
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1500
                    }
                }
                # Dołącz systemInstruction jako system prompt w pierwszej wiadomości jeśli API wspiera
                if system_prompt:
                    alternating[0]["parts"][0]["text"] = f"[INSTRUKCJA SYSTEMOWA: {system_prompt}]\n\n" + alternating[0]["parts"][0]["text"]

                models = ["gemini-3.5-flash-lite", "gemini-flash-latest"]
                for model in models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                    try:
                        async with httpx.AsyncClient(timeout=4.0) as client:
                            resp = await client.post(url, json=payload)
                            if resp.status_code == 200:
                                res_data = resp.json()
                                cands = res_data.get("candidates", [])
                                if cands:
                                    parts = cands[0].get("content", {}).get("parts", [])
                                    if parts and parts[0].get("text"):
                                        return parts[0].get("text")
                    except Exception:
                        pass

        # Jeśli LLM ma przestój / przeciążenie, uruchamiamy inteligentny, dopasowany generator lokalny
        return cls._generate_fallback_response(messages, context_data, custom_data, intents)

    @classmethod
    def _generate_fallback_response(
        cls,
        messages: List[Dict[str, str]],
        context_data: Dict[str, Any],
        custom_data: Optional[str],
        intents: Dict[str, bool]
    ) -> str:
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "").lower()
                break

        # PRIORYTET 1: PYTANIE O PORTFEL UŻYTKOWNIKA
        if intents.get("wants_portfolio") or "user_portfolio" in context_data:
            p = context_data.get("user_portfolio", {})
            total_val = p.get("total_portfolio_value", 100000.0)
            cash = p.get("cash_balance", 100000.0)
            pnl = p.get("total_pnl_pct", 0.0)
            alpha = p.get("alpha_pct", 0.0)
            holdings = p.get("holdings", [])
            pos_cnt = p.get("positions_count", len(holdings))
            cash_pct = round((cash / total_val) * 100, 1) if total_val > 0 else 100.0

            holdings_str = ""
            if holdings:
                holdings_str = "\n".join([
                    f"- **{h['ticker']}** ({h.get('company_name', h['ticker'])}): {h.get('shares', 0):.2f} akcji | Kurs wejścia: ${h.get('entry_price', 0):.2f} | Bieżący: ${h.get('current_price', 0):.2f} | Wynik: **{'+' if h.get('pnl_pct', 0) >= 0 else ''}{h.get('pnl_pct', 0):.2f}%** (Waga w portfelu: {h.get('weight_pct', 0)}%)"
                    for h in holdings
                ])
            else:
                holdings_str = "*Brak otwartych pozycji akcyjnych — 100% kapitału spoczywa bezpiecznie w gotówce.*"

            cash_comment = (
                f"Utrzymujesz **{cash_pct}% gotówki** (${cash:,.2f}). To wspaniała dyscyplina. "
                f"W Berkshire zawsze powtarzam: *gotówka to jak tlen — doceniasz jej wartość dopiero wtedy, gdy zaczyna jej brakować*. Masz 'suchy proch' na okazje rynkowe."
                if cash_pct >= 15 else
                f"Twoja rezerwa gotówkowa wynosi **{cash_pct}%**, co jest poniżej naszego progu 15%. Pamiętaj, aby nie inwestować 100% kapitału — rynki potrafią zaskoczyć."
            )

            return (
                f"### Audyt Twojego Portfela Inwestycyjnego (Paper Trading)\n\n"
                f"*„Pierwsza zasada inwestowania: Nigdy nie trać pieniędzy. Druga zasada: Nigdy nie zapominaj o pierwszej.”*\n\n"
                f"Oto podsumowanie Twojej alokacji i dyscypliny kapitałowej:\n\n"
                f"- **Wartość całkowita portfela:** **${total_val:,.2f}**\n"
                f"- **Dostępna gotówka:** **${cash:,.2f}** ({cash_pct}% całego kapitału)\n"
                f"- **Skumulowany P&L portfela:** **{'+' if pnl >= 0 else ''}{pnl:.2f}%**\n"
                f"- **Alfa Buffetta (przewaga nad S&P 500):** **{'+' if alpha >= 0 else ''}{alpha:.2f}%**\n"
                f"- **Liczba aktywnych pozycji:** **{pos_cnt}**\n\n"
                f"📊 **Twoje Otwarte Pozycje:**\n"
                f"{holdings_str}\n\n"
                f"🛡️ **Mój Komentarz i Wskazówki Warrena Buffetta:**\n"
                f"{cash_comment}\n\n"
                f"Pamiętaj o zasadzie Money Management: nie alokuj więcej niż 10-20% kapitału w jedną spółkę i trzymaj się spółek o wysokim Buffett Score (>=70) z solidną fosą ekonomiczną."
            )

        # PRIORYTET 2: PYTANIE O SCREENER / OKAZJE RYNKOWE
        if intents.get("wants_screener") or "top_screener_opportunities" in context_data:
            opps = context_data.get("top_screener_opportunities", [])
            if opps:
                lines = [
                    f"- **{o['ticker']}** ({o['company_name']}): Score **{o['buffett_score']}/100**, Margines Bezpieczeństwa: **+{o['margin_of_safety_pct']}%**, Kurs: ${o['current_price']} (Wycena DCF: ${o['intrinsic_value']}) — Rekomendacja: **{o['recommendation']}**"
                    for o in opps
                ]
                opps_str = "\n".join(lines)
            else:
                opps_str = "- Przejdź do zakładki Screener i uruchom Skan Sesyjny EOD, aby zaktualizować ranking spółek."

            return (
                f"### Najlepsze Okazje Inwestycyjne wg Modelu Buffetta:\n\n"
                f"Oto spółki o najwyższej jakości fundamentalnej i zadowalającym marginesie bezpieczeństwa wyselekcjonowane przez nasz skaner z bazy:\n\n"
                f"{opps_str}\n\n"
                f"💡 **Rada Buffetta:** Każda z tych spółek łączy wysoką stopę zwrotu z kapitału (ROIC) z dyskontem do wartości wewnętrznej. "
                f"Nie kupuj ich jednak na raz — zbadaj ich bilanse i kupuj wtedy, gdy rynek panikuje."
            )

        # PRIORYTET 3: ANALIZA KONKRETNEJ SPÓŁKI
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

        # PRIORYTET 4: OWNER EARNINGS
        if intents.get("wants_owner_earnings"):
            return (
                "### Czym jest Owner Earnings (Zysk Właścicielski)?\n\n"
                "*„Kiedy z Charliem analizujemy sprawozdania, nie patrzymy na zysk netto ani na modną EBITDA. Patrzymy na realną gotówkę, którą właściciel może wyciągnąć ze spółki bez uszczerbku dla jej zdolności operacyjnych.”* — Warren Buffett\n\n"
                "**Wzór Buffetta:**\n"
                "$$\\text{Owner Earnings} = \\text{Zysk Netto} + \\text{Amortyzacja (D&A)} - \\text{CapEx Utrzymaniowy (Maintenance CapEx)}$$\n\n"
                "**Jak liczymy to w aplikacji BUFFET:**\n"
                "1. **Baza FCF:** Standardowo opieramy się na Free Cash Flow TTM (Operating Cash Flow minus Całkowity CapEx).\n"
                "2. **Inteligentna Normalizacja:** Jeśli firma (np. technologiczna) ponosi gigantyczny CapEx rozwojowy na AI lub miała jednorazowy odpis, nasz algorytm wygładza wynik 5-letnią średnią historyczną lub bierze 70% zysku netto, aby nie karać biznesu za inwestycje w przyszłą fosę."
            )

        # PRIORYTET 5: BUFFETT SCORE
        if intents.get("wants_score"):
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

        # PRIORYTET 6: DCF I WYCENA
        if intents.get("wants_dcf"):
            return (
                "### Model Wyceny DCF w Aplikacji BUFFET\n\n"
                "Stosujemy konserwatywny, 10-letni model zdyskontowanych przepływów pieniężnych:\n"
                "- **Lata 1-5:** Wzrost oparty o 5-letni CAGR przychodów (z limitem max 11-13% dla mega-capów, aby uniknąć huraoptymizmu).\n"
                "- **Lata 6-10:** Spowolnienie tempa do 60% z lat 1-5 (efekt konkurencji rynkowej).\n"
                "- **Wartość Rezydualna:** Model Gordona z wieczystą stopą wzrostu $g = 3.0\\%$ (tempo wzrostu PKB).\n"
                "- **Stopa Dyskontowa:** Stały koszt alternatywny kapitału Buffetta: 9.0% dla spółek bezpiecznych, 9.5-10.5% dla bardziej zadłużonych.\n"
                "- **Korekta o Dług Netto:** Od wartości firmy odejmujemy dług netto (lub dodajemy gotówkę netto), dzieląc wynik przez liczbę wyemitowanych akcji."
            )

        # PRIORYTET 7: MONEY MANAGEMENT
        if intents.get("wants_mm"):
            return (
                "### Zasady Money Management w Aplikacji BUFFET\n\n"
                "Dyscyplina to różnica pomiędzy inwestorem a hazardzistą:\n"
                "- **Wirtualny Kapitał Startowy:** $100 000 USD.\n"
                "- **Wielkość Pozycji:** Domyślnie 10% kapitału (max 20-25% w jednej spółce — zasada rozsądnej koncentracji).\n"
                "- **Rezerwa Gotówkowa:** Zawsze utrzymujemy minimum 10-15% w gotówce na wypadek gwałtownych przecen rynkowych.\n"
                "- **Stop Loss / Take Profit:** Zlecenia obronne 15% poniżej ceny wejścia oraz realizacja zysków przy +35-40%.\n"
                "- **Alfa Buffetta:** Mierzymy zysk portfela ponad benchmark S&P 500."
            )

        # PRIORYTET 8: OGÓLNA ROZMOWA
        return (
            "Witaj! Jestem Twoim wirtualnym doradcą w stylu **Warrena Buffetta** i **Charliego Mungera**, wbudowanym w aplikację **BUFFET** (moduł IV przemokoduje.com).\n\n"
            "Znam każdy element systemu na wylot. Możesz mnie zapytać o:\n"
            "1. **Stan Twojego portfela:** Wpisz *„Co sądzisz o moim portfelu?”*, a prześwietlę Twoje pozycje, rezerwę gotówkową i Alfę względem S&P 500.\n"
            "2. **Szczegóły dowolnego wskaźnika:** ROIC, ROE, marżę brutto, dług netto/FCF, current ratio czy wskaźniki płynności.\n"
            "3. **Wycenę spółki:** Jak liczymy Owner Earnings i 10-letni DCF z wartością rezydualną.\n"
            "4. **Punktację Buffett Score (0-100):** Dokładną wagę każdego z 6 kryteriów oceny spółki.\n"
            "5. **Audyt dowolnej spółki (np. Apple, Coca-Cola, Google):** Podaj ticker, a zbadam jej fosę i margines bezpieczeństwa.\n"
            "6. **Okazje ze Screenera:** Wpisz *„Pokaż najlepsze okazje”*, a wyselekcjonuję najtańsze spółki z najwyższym Score.\n\n"
            "O czym chciałbyś porozmawiać?"
        )
