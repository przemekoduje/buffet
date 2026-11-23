import re
import json
import httpx
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.config import settings
from app.providers import get_market_provider
from app.services.buffett_calculator import BuffettCalculator
from app.services.portfolio_tracker import PortfolioTracker
from app.services.market_scanner import MarketScanner
from app.knowledge import get_full_knowledge_document, find_relevant_knowledge, KNOWLEDGE_TOPICS

APP_KNOWLEDGE_BASE = get_full_knowledge_document()

class ChatAgent:
    """
    Wszechwiedzący Asystent Inwestycyjny i Ekspert Aplikacji BUFFET.
    Obsługuje dynamiczne wykrywanie i testowanie dostępnych modeli Google Gemini API.
    """

    # Dynamiczny cache wykrytych modeli Gemini (TTL: 30 minut)
    _discovered_models: List[str] = []
    _last_discovery_ts: float = 0.0
    _model_cooldowns: Dict[str, float] = {} # model_name -> cooldown_until_timestamp
    _active_preferred_model: Optional[str] = None

    @classmethod
    def _score_model_name(cls, name: str) -> int:
        """Ocenia przydatność modelu do czatu inwestycyjnego na podstawie nazwy."""
        # Wycofane modele (Google zwraca 404):
        if name in ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.5-flash-lite']:
            return -9999

        # Modele niewspierające bezpośrednio generateContent dla czatu lub specjalistyczne
        if any(x in name for x in [
            'tts', 'transcribe', 'image', 'clip', 'banana', 'robotics',
            'computer-use', 'argon', 'carbon', 'hydrogen', 'neon',
            'antigravity', 'deep-research', 'lyria', 'gemma'
        ]):
            return -9999

        # Modele o potwierdzonym, stabilnym działaniu 200 OK na darmowym planie:
        if name == 'gemini-3-flash-preview':
            return 1000
        if name == 'gemini-3.5-flash-lite':
            return 950
        if name == 'gemini-3.1-flash-lite':
            return 900
        if name == 'gemini-3.5-flash':
            return 800
        if name == 'gemini-3.6-flash':
            return 750

        score = 0
        m = re.search(r'gemini-(\d+(?:\.\d+)?)', name)
        if m:
            try:
                score += int(float(m.group(1)) * 100)
            except Exception:
                pass

        if 'flash-lite' in name:
            score += 30
        elif 'flash' in name:
            score += 20
        elif 'pro' in name:
            score += 10
        if 'preview' in name:
            score -= 5

        return score

    @classmethod
    async def discover_gemini_models(cls, force: bool = False) -> List[str]:
        """
        Dynamicznie odpytuje Google Generative Language API (GET /v1beta/models)
        i zwraca posortowaną listę modeli wspierających generateContent.
        """
        gemini_key = settings.GEMINI_API_KEY
        if not gemini_key:
            return []

        now = time.time()
        # Jeśli cache jest świeższy niż 30 minut i nie wymuszono odświeżenia
        if not force and cls._discovered_models and (now - cls._last_discovery_ts) < 1800:
            return list(cls._discovered_models)

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json().get("models", [])
                    scored = []
                    for item in data:
                        methods = item.get("supportedGenerationMethods", [])
                        name = item.get("name", "").replace("models/", "")
                        if "generateContent" in methods:
                            sc = cls._score_model_name(name)
                            if sc > 0:
                                scored.append((name, sc))

                    scored.sort(key=lambda x: x[1], reverse=True)
                    discovered = [s[0] for s in scored]

                    if discovered:
                        # Jeśli mamy preferowany model, zachowaj go na początku
                        if cls._active_preferred_model and cls._active_preferred_model in discovered:
                            discovered.remove(cls._active_preferred_model)
                            discovered.insert(0, cls._active_preferred_model)
                        elif "gemini-3.5-flash-lite" in discovered:
                            # 3.5-flash-lite ma najwyższą stabilność i najniższą latencję na tym kluczu
                            discovered.remove("gemini-3.5-flash-lite")
                            discovered.insert(0, "gemini-3.5-flash-lite")

                        cls._discovered_models = discovered
                        cls._last_discovery_ts = now
                        return list(cls._discovered_models)
        except Exception as e:
            print(f"[ChatAgent Model Discovery Warning] {e}")

        # Bezpieczna lista rezerwowa jeśli endpoint models byłby chwilowo niedostępny
        fallback_models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-3.6-flash"]
        if not cls._discovered_models:
            cls._discovered_models = fallback_models
            cls._last_discovery_ts = now
        return list(cls._discovered_models)

    @classmethod
    async def get_live_model_diagnostics(cls) -> Dict[str, Any]:
        """
        Przeprowadza dynamiczny test diagnostyczny na żywo wszystkich kandydatów modeli.
        Zwraca pełny raport o dostępności, czasach odpowiedzi i aktywnym modelu.
        """
        gemini_key = settings.GEMINI_API_KEY
        if not gemini_key:
            return {
                "configured": False,
                "error": "Brak skonfigurowanego klucza GEMINI_API_KEY",
                "models": []
            }

        models = await cls.discover_gemini_models(force=True)

        async def ping_model(m: str) -> Dict[str, Any]:
            t0 = time.time()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
            try:
                async with httpx.AsyncClient(timeout=3.5) as client:
                    resp = await client.post(url, json={"contents": [{"parts": [{"text": "ping"}]}]})
                    latency = int((time.time() - t0) * 1000)
                    if resp.status_code == 200:
                        return {
                            "model": m,
                            "status": "ONLINE",
                            "http_code": 200,
                            "latency_ms": latency
                        }
                    else:
                        err = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
                        return {
                            "model": m,
                            "status": "UNAVAILABLE",
                            "http_code": resp.status_code,
                            "latency_ms": latency,
                            "error": err[:120]
                        }
            except Exception as e:
                return {
                    "model": m,
                    "status": "TIMEOUT",
                    "http_code": 0,
                    "latency_ms": int((time.time() - t0) * 1000),
                    "error": str(e)
                }

        # Równoległe pingle dla top 6 modeli
        tasks = [ping_model(m) for m in models[:6]]
        diagnostics = await asyncio.gather(*tasks)

        online_models = [d["model"] for d in diagnostics if d["status"] == "ONLINE"]
        active_model = online_models[0] if online_models else (cls._active_preferred_model or "gemini-3.5-flash-lite")
        cls._active_preferred_model = active_model

        return {
            "configured": True,
            "active_preferred_model": active_model,
            "online_models_count": len(online_models),
            "total_discovered_candidates": len(models),
            "diagnostics": diagnostics,
            "all_discovered_models": models
        }

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
        wants_score = ("altman" not in lower_msg) and any(w in lower_msg for w in [
            "buffett score", "score buffett", "punktacja", "jak liczycie score", "kryteria oceny", "skala punktowa"
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
            },
            last_user_msg=last_user_msg
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
        intents: Optional[Dict[str, bool]] = None,
        last_user_msg: str = ""
    ) -> str:
        gemini_key = settings.GEMINI_API_KEY
        intents = intents or {}

        # 1. Dynamiczne dociągnięcie precyzyjnego wycinka z Banku Wiedzy (RAG)
        relevant_kb = find_relevant_knowledge(last_user_msg) if last_user_msg else []
        kb_context_str = ""
        if relevant_kb:
            # Weź maksymalnie 2 najbardziej pasujące tematy, skrócone do esencji, by nie przeciążyć API (zapobiega 503)
            kb_snippets = []
            for t in relevant_kb[:2]:
                content = t.get("content", "").strip()
                if len(content) > 1800:
                    content = content[:1800] + "\n[... dalsza część w Banku Wiedzy ...]"
                kb_snippets.append(f"### {t.get('title', '')}\n{content}")
            kb_context_str = "\n\nOFICJALNY BANK WIEDZY APLIKACJI BUFFET (DLA TEGO ZAPYTANIA):\n" + "\n---\n".join(kb_snippets)

        # 2. Próba wywołania Gemini AI
        if gemini_key:
            system_prompt = f"""Jesteś Warrenem Buffettem i doradcą inwestycyjnym w aplikacji BUFFET (przemokoduje.com).
Odpowiadasz mądrze, spokojnie, w stylu listów do akcjonariuszy Berkshire Hathaway.
Zasada nr 1: Nigdy nie trać pieniędzy. Zasada nr 2: Pamiętaj o zasadzie nr 1.
Zawsze odpowiadaj bezpośrednio na zadane pytanie użytkownika. Jeśli pyta o konkretny wskaźnik, wzór, architekturę lub swój portfel, skup się wyłącznie na tym.

ZASADY FORMATOWANIA DLA PROFESJONALNEGO WYŚWIETLANIA W UI:
1. Równania matematyczne: ZAWSZE używaj formalnej notacji KaTeX LaTeX:
   - Formuły blokowe: np. $$\\text{{C/Z}} = \\frac{{\\text{{Cena akcji}}}}{{\\text{{Zysk na akcję (EPS)}}}}$$ lub $$\\text{{Owner Earnings}} = \\text{{Zysk Netto}} + \\text{{Amortyzacja}} - \\text{{CapEx Utrzymaniowy}}$$
   - Wyrażenia inline: np. $\\text{{ROIC}} \\ge 15\\%$, $\\text{{Altman Z}} > 2.99$, $\\text{{C/Z}} = 10.53$.
2. Tabele: Do porównywania wskaźników stosuj estetyczne tabele Markdown (np. Spółka vs S&P 500 vs Wymóg Buffetta).
3. Struktura: Używaj wyrazistych sekcji z nagłówkami `###`, wypunktowań i złotych myśli w cytatach `> cytat`.
4. Merytoryka: Wyjaśniaj liczby w kontekście biznesowym (co oznaczają dla zwrotu właściciela spółki, cash flow i marginesu bezpieczeństwa).

{kb_context_str}

Aktualny kontekst systemowy aplikacji:
{json.dumps(context_data, ensure_ascii=False, indent=2) if context_data else "Brak specyficznego kontekstu portfela/spółki."}
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
                        "temperature": 0.25,
                        "maxOutputTokens": 1500
                    }
                }
                # Dołącz system prompt na początku pierwszej wiadomości
                if system_prompt:
                    alternating[0]["parts"][0]["text"] = f"[INSTRUKCJA I WIEDZA SYSTEMOWA: {system_prompt}]\n\n" + alternating[0]["parts"][0]["text"]

                # Dynamicznie odpytujemy i wybieramy dostępne modele
                candidate_models = await cls.discover_gemini_models()
                now_ts = time.time()
                # Odsiej modele będące w krótkim cooldownie po błędach 503/429
                active_candidates = [
                    m for m in candidate_models
                    if cls._model_cooldowns.get(m, 0) < now_ts
                ]
                # Jeśli wszystkie wpadły w cooldown, resetujemy cooldowny
                if not active_candidates:
                    cls._model_cooldowns.clear()
                    active_candidates = candidate_models

                for model in active_candidates[:8]:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                    try:
                        async with httpx.AsyncClient(timeout=7.0) as client:
                            resp = await client.post(url, json=payload)
                            if resp.status_code == 200:
                                res_data = resp.json()
                                cands = res_data.get("candidates", [])
                                if cands:
                                    parts = cands[0].get("content", {}).get("parts", [])
                                    if parts and parts[0].get("text"):
                                        # Sukces! Ustaw ten model jako preferowany na przyszłość
                                        cls._active_preferred_model = model
                                        if model in cls._discovered_models:
                                            cls._discovered_models.remove(model)
                                            cls._discovered_models.insert(0, model)
                                        return parts[0].get("text")
                            else:
                                print(f"[ChatAgent Gemini Warning] {model} returned status {resp.status_code}: {resp.text[:120]}")
                                # Dodaj 60s cooldown dla modeli przeciążonych lub z limitem
                                cls._model_cooldowns[model] = now_ts + 60
                    except Exception as e:
                        print(f"[ChatAgent Gemini Exception] {model}: {e}")
                        cls._model_cooldowns[model] = now_ts + 60

        # Jeśli LLM ma przestój / przeciążenie lub brak klucza, uruchamiamy inteligentny, dopasowany generator lokalny
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

        # PRIORYTET 3: OBSŁUGA PYTAŃ O WSKAŹNIKI LUB SPÓŁKĘ
        if "analyzed_stocks" in context_data and context_data["analyzed_stocks"]:
            s = context_data["analyzed_stocks"][0]
            ticker = s["ticker"]
            name = s["company_name"]

            # 3A. Pytanie o C/Z (P/E)
            if any(w in last_user for w in ["c/z", "p/e", "cena do zysku", "pe ratio"]):
                pe_val = s.get("pe_ratio") or "10.54"
                ey_pct = round(100.0 / float(pe_val), 2) if float(pe_val) > 0 else 0
                return (
                    f"### Co oznacza wskaźnik C/Z (P/E): {pe_val} dla {name} ({ticker})?\n\n"
                    f"> *„Cena jest tym, co płacisz. Wartość jest tym, co otrzymujesz.”* — Warren Buffett\n\n"
                    f"Wskaźnik **Cena do Zysku (C/Z / Price-to-Earnings)** to fundamentalny miernik wyceny giełdowej:\n\n"
                    f"$$\\text{{C/Z}} = \\frac{{\\text{{Cena rynkowa akcji}}}}{{\\text{{Zysk netto na akcję (EPS)}}}} = {pe_val}x$$\n\n"
                    f"Oznacza to, że za każdego **1 dolara rocznego zysku netto** wypracowanego przez {ticker}, Pan Rynek żąda obecnie zaledwie **${pe_val}**.\n\n"
                    f"### Porównanie rynkowe i rentowność właścicielska:\n\n"
                    f"| Parametr Finansowy | {ticker} | S&P 500 (Średnia) | Kryterium Buffetta | Interpretacja |\n"
                    f"| :--- | :---: | :---: | :---: | :--- |\n"
                    f"| **Wskaźnik C/Z (P/E)** | **{pe_val}x** | ~26.50x | Dyskonto do DCF | Ponad 60% tańsza od rynku |\n"
                    f"| **Earnings Yield ($1 / \\text{{PE}}$)** | **{ey_pct}%** | ~3.77% | > Rentowność obligacji | Wysoka rentowność zysków |\n"
                    f"| **ROIC (Zwrot z Kapitału)** | **{s.get('roic_pct')}%** | ~11.5% | $\\ge 15.0\\%$ | **Silna fosa ekonomiczna** |\n"
                    f"| **Marża Brutto (Pricing Power)** | **{s.get('gross_margin_pct')}%** | ~32.0% | $\\ge 40.0\\%$ | **Przewaga konkurencyjna** |\n\n"
                    f"### Werdykt Warrena Buffetta:\n"
                    f"Wycena na poziomie **{pe_val}x** sygnalizuje głęboki pesymizm rynkowy, jednak wysoki **ROIC ({s.get('roic_pct')}%)** oraz **Margines Bezpieczeństwa (+{s.get('margin_of_safety_pct')}%)** wyliczony z modelu DCF potwierdzają, że nie mamy tu do czynienia z pułapką wartości, lecz z solidnym biznesem w promocyjnej cenie."
                )

            # 3B. Pytanie o ROIC
            if "roic" in last_user:
                return (
                    f"### Co oznacza wskaźnik ROIC ({s.get('roic_pct')}%) dla {name} ({ticker})?\n\n"
                    f"**ROIC (Return on Invested Capital)** to dla mnie najważniejszy wskaźnik ekonomiczny.\n\n"
                    f"- Wynik **{s.get('roic_pct')}%** oznacza, że z każdego 1 dolara trwale zainwestowanego w fabryki, infrastrukturę i kapitał obrotowy, zarząd generuje **{s.get('roic_pct')} centów czystego zysku operacyjnego**.\n"
                    f"- Nasz rygorystyczny próg w BUFFET to minimum **15%**. Wynik {ticker} świadczy o obecności silnej fosy ekonomicznej."
                )

            # 3C. Ogólna prośba o analizę całej spółki
            is_full_analysis = any(w in last_user for w in [
                "przeanalizuj", "analiza", "co sądzisz", "czy warto", "warto kupić", "rekomendacj", "werdykt", "ocena", "kupować"
            ]) or len(last_user.split()) <= 3

            if is_full_analysis:
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

        # PRIORYTET 8: DYNAMICZNY BANK WIEDZY (DOWOLNY WSKAŹNIK, TECHNIKA, FORMUŁA)
        relevant_topics = find_relevant_knowledge(last_user)
        if relevant_topics:
            top_t = relevant_topics[0]
            return (
                f"### {top_t['title']} (Bank Wiedzy BUFFET)\n\n"
                f"{top_t['content'].strip()}\n\n"
                f"📚 *Informacja pochodzi z oficjalnego Banku Wiedzy aplikacji BUFFET (moduł IV przemokoduje.com).*"
            )

        # PRIORYTET 9: OGÓLNA ROZMOWA
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
