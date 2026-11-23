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
Wiedza o aplikacji BUFFET (część 4 ekosystemu przemokoduje.com):
- GŁÓWNE MOTTO: 'Reguła 1: Nigdy nie trać pieniędzy. Reguła 2: Zawsze pamiętaj o punkcie pierwszym.' (Warren Buffett).
- 4 FILTRY BUFFETTA:
  1. Trwała fosa ekonomiczna (Economic Moat): ROIC > 12-15%, marża brutto > 40% (dowód pricing power).
  2. Bezpieczny bilans (Reguła nr 1): Net Debt / FCF < 3.0 lata, Current Ratio > 1.2, Altman Z-Score > 3.0.
  3. Uczciwy i kompetentny zarząd: ROE > 15%, skupy akcji (buybacks), brak rozwodnienia akcji (SBC).
  4. Margines Bezpieczeństwa (Margin of Safety): Wycena Intrinsic Value liczona 10-letnim modelem DCF na bazie Zysku Właścicielskiego (Owner Earnings = FCF skorygowany o CapEx). Kupujemy tylko przy dyskoncie min. 15-20% względem ceny rynkowej.
- BUFFETT SCORE (0-100):
  - 80-100: STRONG_BUY (Klasa Buffetta, wysoka jakość, duży margines bezpieczeństwa).
  - 65-79: BUY (Dobra spółka, uczciwa wycena).
  - 50-64: HOLD (Solidny biznes, ale brak marginesu bezpieczeństwa).
  - 0-49: AVOID (Słabe zwroty z kapitału lub nadmierny dług).
- MODUŁY APLIKACJI:
  - Portfel Demo (Audyt 1R): Forward-testing skuteczności vs S&P 500, wskaźnik Alfa Buffetta.
  - Money Management: Kapitał domyślny $100 000, domyślna pozycja 10%, max w 1 spółce 25%, rezerwa gotówki 15%, Stop Loss 15%, Take Profit 40%.
  - Screener Buffetta: 3 koszyki (US Quality, S&P 500 Value, Dywidendowi Arystokraci), automatyczny skan EOD po zamknięciu sesji USA (~22:15 PL) oraz alerty intraday co 15 minut.
  - Karta Wyceny & AI (Deep Dive): Wycena DCF, checklist 4 Zasad Buffetta, newsy rynkowe i analiza sentymentu Gemini AI.
  - Firebase Cloud Sync: Pełna synchronizacja stanu użytkownika (portfel, pozycje, MM, zlecenia, watchlist) w kolekcji `buffet_users/{uid}`.
"""

class ChatAgent:
    """
    Inteligentny Asystent Inwestycyjny i Ekspert Aplikacji BUFFET.
    Zna aplikację na wylot, pobiera twarde dane rynkowe w locie i doradza jak Warren Buffett.
    """

    @classmethod
    def _extract_tickers(cls, text: str) -> List[str]:
        """Wykrywa tickery giełdowe w zapytaniu użytkownika (np. AAPL, KO, BRK.B)."""
        # Znajdź wielkie litery 1-5 znaków
        candidates = re.findall(r'\b[A-Z]{1,5}(?:\.[A-Z])?\b', text)
        known_stocks = {
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "BRK.B", "BRK.A", "KO", "PEP", "V", "MA",
            "JNJ", "PG", "COST", "TGT", "NVDA", "MCD", "DIS", "WMT", "NKE", "IBM", "UNH", "XOM",
            "CVX", "HD", "LOW", "CAT", "JPM", "BAC", "TSLA", "META"
        }
        found = [c for c in candidates if c in known_stocks]
        # Sprawdź też znane nazwy firm
        lower = text.lower()
        name_map = {
            "apple": "AAPL", "coca cola": "KO", "coca-cola": "KO", "berkshire": "BRK.B",
            "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL", "visa": "V",
            "target": "TGT", "walmart": "WMT", "johnson": "JNJ", "costco": "COST", "amazon": "AMZN",
            "nvidia": "NVDA", "mcdonald": "MCD"
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

        # 1. Zbieranie kontekstu danych
        context_data: Dict[str, Any] = {}
        tickers = cls._extract_tickers(last_user_msg)
        if context_ticker and context_ticker not in tickers:
            tickers.append(context_ticker)

        provider = get_market_provider()

        # Pobierz dane dla wykrytych spółek
        stocks_info = []
        for t in tickers[:3]: # Max 3 spółki na raz
            fund = provider.get_ticker_data(t)
            if fund:
                eval_res = BuffettCalculator.evaluate(fund)
                try:
                    news = provider.get_ticker_news(t, limit=4) or []
                except Exception:
                    news = []
                stocks_info.append({
                    "ticker": fund.ticker,
                    "company_name": fund.company_name,
                    "sector": fund.sector,
                    "current_price": fund.current_price,
                    "intrinsic_value": eval_res["intrinsic_value"],
                    "margin_of_safety_pct": eval_res["margin_of_safety_pct"],
                    "buffett_score": eval_res["buffett_score"],
                    "recommendation": eval_res["recommendation"],
                    "roic_pct": fund.roic_pct,
                    "roe_pct": fund.roe_pct,
                    "gross_margin_pct": fund.gross_margin_pct,
                    "net_debt_to_fcf": fund.net_debt_to_fcf,
                    "pe_ratio": fund.pe_ratio,
                    "rule_1_risk": eval_res["rule_number_one_risk"],
                    "rule_1_warnings": eval_res["rule_1_warnings"],
                    "recent_news": [n.get("title") for n in news[:3]]
                })
        if stocks_info:
            context_data["analyzed_stocks"] = stocks_info

        # Sprawdź czy pytanie dotyczy portfela lub stanu konta
        wants_portfolio = any(w in last_user_msg.lower() for w in ["portfel", "portfolio", "konto", "pozycje", "gotówka", "p&l", "zysk", "strata", "alfa"])
        if wants_portfolio and db:
            summary = PortfolioTracker.get_portfolio_summary(db)
            context_data["user_portfolio"] = {
                "total_portfolio_value": summary.get("total_portfolio_value"),
                "cash_balance": summary.get("cash_balance"),
                "total_pnl_pct": summary.get("total_pnl_pct"),
                "alpha_pct": summary.get("alpha_pct"),
                "positions_count": summary.get("positions_count"),
                "holdings": [
                    {
                        "ticker": h.ticker,
                        "shares": h.shares,
                        "entry_price": h.entry_price,
                        "current_price": h.current_price,
                        "pnl_pct": h.pnl_pct,
                        "weight_pct": h.weight_pct
                    }
                    for h in (summary.get("holdings") or [])
                ],
                "mm_rules": summary.get("mm_config")
            }

        # Sprawdź czy pytanie dotyczy rekomendacji / screenera / okazji rynkowych
        wants_screener = any(w in last_user_msg.lower() for w in ["okazj", "rekomendacj", "co kupić", "ranking", "screener", "tanie", "niedowartościowan"])
        if wants_screener and db:
            scan_res = MarketScanner.get_all_scan_results(db)
            top_stocks = sorted(
                [s for s in scan_res if s.get("buffett_score", 0) >= 65],
                key=lambda x: x.get("buffett_score", 0),
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

        # 2. Generowanie odpowiedzi (Gemini AI z pełnym kontekstem lub inteligentny fallback)
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
        gemini_model = settings.GEMINI_MODEL or "gemini-flash-lite-latest"

        system_instruction = f"""
Jesteś Wybitnym Doradcą Inwestycyjnym i Mędrcem Rynkowym w stylu Warrena Buffetta i Charliego Mungera, wbudowanym bezpośrednio w aplikację BUFFET (przemokoduje.com).

TWOJA ROLA I ZASADY:
1. Znasz całą aplikację BUFFET na wylot (filozofia, 4 filtry, DCF, Owner Earnings, wskaźniki, portfel demo, Money Management, alerty i skaner).
2. Twoją nadrzędną zasadą jest ZASADA NR 1: "Nigdy nie trać pieniędzy. Zasada 2: Nigdy nie zapominaj o regule nr 1".
3. Udzielasz odpowiedzi w sposób pewny, precyzyjny, oparty o twarde liczby (ROIC, marże, zadłużenie/FCF, margines bezpieczeństwa), ale jednocześnie ciepły, mentorski i błyskotliwy jak listy Buffetta do akcjonariuszy Berkshire Hathaway.
4. Gdy użytkownik pyta o spółkę, korzystasz z dostarczonych w kontekście twardych danych i weryfikujesz jej fosę ekonomiczną (Moat) oraz margines bezpieczeństwa.
5. Jeśli użytkownik dostarczył własne dane lub raporty, analizujesz je rygorystycznie pod kątem wiarygodności zysków i bezpieczeństwa kapitału.

BAZA WIEDZY O APLIKACJI BUFFET:
{APP_KNOWLEDGE_BASE}

AKTUALNE DANE SYSTEMOWE POBRANE W LOCIE:
{json.dumps(context_data, ensure_ascii=False, indent=2) if context_data else "Brak specyficznego kontekstu spółki - odpowiedz ogólnie z wiedzy Buffetta."}

DODATKOWE DANE OD UŻYTKOWNIKA (JEŚLI PODANE):
{custom_data or "Brak"}
"""

        if gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
                formatted_contents = []
                for m in messages:
                    role = "user" if m.get("role") == "user" else "model"
                    formatted_contents.append({
                        "role": role,
                        "parts": [{"text": m.get("content", "")}]
                    })

                payload = {
                    "systemInstruction": {"parts": [{"text": system_instruction}]},
                    "contents": formatted_contents,
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1500
                    }
                }

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "")
            except Exception as e:
                print(f"[ChatAgent Gemini Error, falling back to local reasoning] {e}")

        # Inteligentny lokalny generator odpowiedzi Buffetta
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

        # Scenariusz 1: Analiza konkretnej spółki
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

        # Scenariusz 2: Pytanie o portfel użytkownika
        if "user_portfolio" in context_data:
            p = context_data["user_portfolio"]
            return (
                f"### Przegląd Twojego Portfela Paper Trading\n\n"
                f"- **Wartość całkowita portfela:** **${p.get('total_portfolio_value', 0):,.2f}**\n"
                f"- **Dostępna gotówka:** **${p.get('cash_balance', 0):,.2f}**\n"
                f"- **Skumulowany P&L:** **{'+' if (p.get('total_pnl_pct') or 0) >= 0 else ''}{p.get('total_pnl_pct')}%**\n"
                f"- **Alfa Buffetta (przewaga nad S&P 500):** **{'+' if (p.get('alpha_pct') or 0) >= 0 else ''}{p.get('alpha_pct')}%**\n"
                f"- **Liczba otwartych pozycji:** **{p.get('positions_count', 0)}**\n\n"
                f"🛡️ **Komentarz dotyczący dyscypliny kapitałowej:**\n"
                f"Twoje pozycje są kontrolowane przez reguły Money Management. Pamiętaj, aby zawsze utrzymywać co najmniej {p.get('mm_rules', {}).get('min_cash_reserve_pct', 15)}% rezerwy gotówkowej na wypadek gwałtownych przecen rynkowych."
            )

        # Scenariusz 3: Okazje z rankingu screenera
        if "top_screener_opportunities" in context_data:
            opps = context_data["top_screener_opportunities"]
            lines = [f"- **{o['ticker']}** ({o['company_name']}): Score **{o['buffett_score']}/100**, Margines: **+{o['margin_of_safety_pct']}%**, Kurs: ${o['current_price']} (Wycena DCF: ${o['intrinsic_value']})" for o in opps]
            return (
                f"### Najlepsze Okazje Inwestycyjne wg Modelu Buffetta:\n\n"
                f"Oto spółki o najwyższej jakości fundamentalnej i zadowalającym marginesie bezpieczeństwa wyselekcjonowane przez nasz skaner:\n\n"
                + "\n".join(lines) +
                f"\n\nKażda z tych spółek spełnia rygorystyczne kryteria ochrony kapitału (Reguła nr 1). Możesz kliknąć ich karty w Screenerze, aby zobaczyć pełną analizę bilansów i transkryptów."
            )

        # Scenariusz 4: Ogólne pytanie o wiedzę i filozofię aplikacji
        return (
            f"Witaj! Jestem Twoim wirtualnym doradcą w stylu **Warrena Buffetta** i **Charliego Mungera**, wbudowanym w aplikację **BUFFET** (cz. 4 przemokoduje.com).\n\n"
            f"Znam każdy element systemu na wylot. Mogę dla Ciebie:\n"
            f"1. **Przeanalizować dowolną spółkę** pod kątem fosy ekonomicznej (ROIC, marża brutto) i marginesu bezpieczeństwa (10-letni DCF Owner Earnings) — wystarczy, że wpiszesz jej ticker (np. *„Co sądzisz o Apple?”* albo *„Przeanalizuj KO”*).\n"
            f"2. **Ocenić stan Twojego portfela** i sprawdzić przestrzeganie reguł Money Management oraz Alfę względem S&P 500.\n"
            f"3. **Prześwietlić zewnętrzne dane lub raporty** — wklej fragment sprawozdania finansowego, a powiem Ci, czy zarząd nie ukrywa zatorów lub zadłużenia.\n"
            f"4. **Wskazać najlepsze okazje z rynku** spośród spółek o najwyższym Buffett Score.\n\n"
            f"O jakiej spółce lub aspekcie rynku chciałbyś porozmawiać?"
        )
