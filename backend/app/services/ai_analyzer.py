import json
import re
import time
import httpx
from typing import Dict, Any, List, Optional, Tuple
from app.config import settings
from app.providers.base import FundamentalData

_AI_CACHE: Dict[str, Tuple[float, Dict[str, str]]] = {}
AI_CACHE_TTL_SEC = 1800  # 30 minut


class AIAnalyzer:
    """
    Moduł analizy jakościowej w stylu Warrena Buffetta:
    - Odpytuje Gemini API (domyślnie gemini-2.5-flash z fallbackiem na gemini-2.0-flash)
    - Jeśli brak klucza GEMINI_API_KEY lub wystąpi błąd sieciowy, korzysta z deterministycznego
      generatora memoriałów Buffetta i jawnie zwraca status źródła (ai_source).
    """

    @classmethod
    async def analyze_company(
        cls,
        data: FundamentalData,
        eval_result: Dict[str, Any],
        force_refresh: bool = False,
        news: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        gemini_key = (settings.GEMINI_API_KEY or "").strip()
        iv_key = round(float(eval_result.get("intrinsic_value", 0.0)), 2)
        news_list = news or []
        news_sig = len(news_list)
        cache_key = f"{data.ticker}:{data.source}:{bool(gemini_key)}:{settings.GEMINI_MODEL}:{iv_key}:n{news_sig}"
        now = time.time()

        if not force_refresh and cache_key in _AI_CACHE:
            ts, cached = _AI_CACHE[cache_key]
            if now - ts < AI_CACHE_TTL_SEC:
                return cached

        if gemini_key:
            last_error = ""
            models_to_try = [settings.GEMINI_MODEL]
            for fallback_model in ("gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.5-flash"):
                if fallback_model not in models_to_try:
                    models_to_try.append(fallback_model)

            for model_name in models_to_try:
                try:
                    res = await cls._query_gemini(data, eval_result, gemini_key, model_name, news_list)
                    _AI_CACHE[cache_key] = (now, res)
                    return res
                except Exception as e:
                    last_error = str(e)
                    print(f"[Gemini API {model_name} error] {e}")

            memo = cls._generate_buffett_memo(data, eval_result)
            memo["ai_source"] = "heuristic"
            memo["ai_model"] = "buffett-heuristic"
            memo["news_sentiment"] = "NEUTRAL"
            memo["news_impact"] = "Brak analizy AI newsów (błąd połączenia z Gemini) — sprawdź nagłówki poniżej ręcznie."
            memo["ai_note"] = f"Błąd Gemini API — użyto analizy heurystycznej ({last_error[:120]})"
            return memo

        memo = cls._generate_buffett_memo(data, eval_result)
        memo["ai_source"] = "heuristic"
        memo["ai_model"] = "buffett-heuristic"
        memo["news_sentiment"] = "NEUTRAL"
        memo["news_impact"] = "Dodaj klucz Gemini API, aby AI automatycznie oceniało wpływ bieżących newsów rynkowych na tezę inwestycyjną."
        memo["ai_note"] = "Brak klucza GEMINI_API_KEY — dodaj klucz w zakładce 'Dostawcy & Koszty', aby uruchomić analizę Gemini AI."
        _AI_CACHE[cache_key] = (now, memo)
        return memo

    @classmethod
    async def _query_gemini(
        cls,
        data: FundamentalData,
        eval_result: Dict[str, Any],
        api_key: str,
        model_name: str,
        news: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        fcf_hist_str = ", ".join(f"${v/1e9:.2f} mld" for v in data.fcf_history_5y) if data.fcf_history_5y else "brak danych"

        news_items = (news or [])[:6]
        if news_items:
            news_block = "\n".join(
                f"- [{n.get('published_at', '')} | {n.get('publisher', '')}] {n.get('title', '')}"
                + (f" — {n.get('summary', '')[:140]}" if n.get("summary") else "")
                for n in news_items
            )
        else:
            news_block = "- Brak bieżących nagłówków prasowych z Yahoo Finance."

        prompt = f"""
Jesteś Warrenem Buffettem i Charliem Mungerem przygotowującymi zwięzły, konkretny memoriał inwestycyjny dla spółki {data.company_name} ({data.ticker}) z sektora {data.sector} / {data.industry}.
Pamiętaj o dwóch najważniejszych zasadach:
1. Nigdy nie trać pieniędzy.
2. Nigdy nie zapominaj o regule numer 1.

Realne dane finansowe spółki (źródło: {data.source}):
- Aktualna cena akcji: ${data.current_price} | Kapitalizacja: ${data.market_cap/1e9:.1f} mld
- Wartość wewnętrzna DCF (Owner Earnings): ${eval_result['intrinsic_value']}
- Margines bezpieczeństwa: {eval_result['margin_of_safety_pct']}%
- Buffett Score: {eval_result['buffett_score']}/100 | Rekomendacja modelu: {eval_result['recommendation']}
- ROIC: {data.roic_pct}% | ROE: {data.roe_pct}%
- Marża brutto: {data.gross_margin_pct}% | Marża operacyjna: {data.operating_margin_pct}%
- Wieloletni CAGR przychodów: {data.revenue_growth_5y_cagr}%
- Free Cash Flow TTM: ${data.free_cash_flow_ttm/1e9:.2f} mld | Historia FCF: [{fcf_hist_str}]
- Gotówka: ${data.total_cash/1e9:.2f} mld | Dług netto: ${data.net_debt/1e9:.2f} mld | Dług netto / FCF: {data.net_debt_to_fcf}x
- Płynność bieżąca (Current Ratio): {data.current_ratio}x | Altman Z-Score: {data.altman_z_score if data.altman_z_score is not None else 'brak'}
- P/E: {data.pe_ratio} | Stopa dywidendy: {data.dividend_yield_pct}% | Beta: {data.beta}
- Ostrzeżenia Reguły 1: {', '.join(eval_result['rule_1_warnings']) if eval_result['rule_1_warnings'] else 'brak'}

Najnowsze newsy rynkowe o spółce (z Yahoo Finance):
{news_block}

Zwróć wyłącznie poprawny obiekt JSON z dokładnie 5 kluczami tekstowymi (po polsku, konkretnie, z odwołaniem do powyższych liczb i newsów, bez ogólników).
WAŻNE: Wszystkie liczby (zwłaszcza cenę ${data.current_price}, wartość wewnętrzną DCF ${eval_result['intrinsic_value']} oraz margines bezpieczeństwa {eval_result['margin_of_safety_pct']}%) przepisz DOKŁADNIE 1:1 bez zaokrąglania ani zmieniania cyfr!
1. "thesis": Główna teza inwestycyjna (3-4 zdania) — czy to wspaniały biznes w rozsądnej cenie?
2. "moat": Analiza fosy ekonomicznej (3-4 zdania) — pricing power, bariery wejścia, przewaga konkurencyjna i jakość zwrotu z kapitału.
3. "rule_1_risks": Audyt Reguły 1 (3-4 zdania) — krytyczna ocena ryzyka trwałej utraty kapitału, bilansu, wyceny i tego, co może pójść nie tak (uwzględnij ewentualne zagrożenia z newsów).
4. "news_sentiment": Dokładnie jedna wartość z: "POSITIVE", "NEUTRAL", "NEGATIVE" — sentyment bieżących wiadomości.
5. "news_impact": Krótka ocena wpływu newsów (2-3 zdania) — czy bieżące nagłówki to krótkoterminowy szum rynkowy, czy realny katalizator / zagrożenie fundamentalne?
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        }
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

            body = resp.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Usuń ewentualne ogrodzenie ```json ... ```
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(text)

            exact_iv = f"${eval_result['intrinsic_value']}"
            iv_pattern = re.compile(
                r"((?:wartoś[ćc]\w*\s+wewnętrzn\w*|wycen\w*\s+DCF|DCF)[^$]{0,35}?)\$\d+(?:[.,]\d+)?",
                re.IGNORECASE,
            )

            def _enforce_dcf(s: str) -> str:
                if not s:
                    return s
                return iv_pattern.sub(rf"\1{exact_iv}", s)

            raw_sent = str(parsed.get("news_sentiment", "NEUTRAL")).upper().strip()
            if raw_sent not in ("POSITIVE", "NEUTRAL", "NEGATIVE"):
                raw_sent = "NEUTRAL"

            return {
                "thesis": _enforce_dcf(parsed.get("thesis", "")),
                "moat": _enforce_dcf(parsed.get("moat", "")),
                "rule_1_risks": _enforce_dcf(parsed.get("rule_1_risks", "")),
                "news_sentiment": raw_sent,
                "news_impact": _enforce_dcf(parsed.get("news_impact", "")),
                "ai_source": "gemini",
                "ai_model": model_name,
                "ai_note": (
                    f"Wygenerowano na żywo przez {model_name} na podstawie realnych danych ({data.source}) "
                    f"oraz {len(news_items)} bieżących newsów rynkowych."
                ),
            }

    @classmethod
    def _generate_buffett_memo(cls, data: FundamentalData, eval_result: Dict[str, Any]) -> Dict[str, str]:
        score = eval_result["buffett_score"]
        mos = eval_result["margin_of_safety_pct"]
        roic = data.roic_pct
        gm = data.gross_margin_pct
        debt_fcf = data.net_debt_to_fcf

        if score >= 75 and mos > 15:
            thesis = (
                f"Wybitne przedsiębiorstwo handlujące ze znaczącym dyskontem ({mos}% marginesu bezpieczeństwa). "
                f"Generuje ${data.free_cash_flow_ttm/1e9:.2f} mld gotówki rocznie przy znakomitym ROIC ({roic}%). "
                f"Zarząd alokuje kapitał z korzyścią dla akcjonariuszy. Idealny kandydat do długoterminowego portfela w myśl zasady 'Kup wspaniałą firmę w uczciwej cenie'."
            )
        elif score >= 55:
            thesis = (
                f"Solidny biznes o ugruntowanej pozycji, lecz obecna wycena rynkowa (${data.current_price}) "
                f"odzwierciedla większość jego zalet (margines bezpieczeństwa: {mos}%). Wymaga cierpliwości i oczekiwania na rynkową przecenę."
            )
        else:
            thesis = (
                f"Biznes niespełniający rygorystycznych kryteriów Berkshire Hathaway (Buffett Score: {score}/100). "
                f"Niewystarczające zwroty z kapitału lub brak marginesu bezpieczeństwa ({mos}%) nie zapewniają odpowiedniej poduszki ochronnej dla kapitału."
            )

        if gm >= 50:
            moat = (
                f"Nadzwyczajna fosa ekonomiczna (Marża brutto {gm}%, ROIC {roic}%). Firma posiada silny 'pricing power' "
                f"— może podnosić ceny bez obawy o odpływ klientów. Działa jak punkt poboru opłat (tollbooth) w swojej branży."
            )
        elif gm >= 35:
            moat = (
                f"Stabilna fosa ekonomiczna (Marża brutto {gm}%, ROIC {roic}%). Silna marka i baza lojalnych klientów "
                f"zapewniają obronę przed konkurencją, choć presja rynkowa wymaga stałej dyscypliny kapitałowej."
            )
        else:
            moat = (
                f"Wąska lub zanikająca fosa (Marża brutto {gm}%). Produkt nosi znamiona towaru masowego (commodity), "
                f"gdzie konkurencja cenowa ogranicza długoterminową rentowność kapitału."
            )

        if debt_fcf == 0:
            debt_status = "Spółka posiada zerowy dług netto i obfitą poduszkę gotówkową, co całkowicie eliminuje ryzyko niewypłacalności."
        elif debt_fcf <= 2.5:
            debt_status = f"Zadłużenie ({debt_fcf:.1f}x FCF) jest bezpieczne i może być spłacone z niecałych trzech lat wolnych przepływów."
        else:
            debt_status = f"Uwaga: Zadłużenie ({debt_fcf:.1f}x FCF) przekracza zalecany limit Buffetta (<3x) i stanowi istotny czynnik ryzyka w okresie recesji."

        val_risk = (
            "Niedoszacowanie rynkowe chroni kapitał przed trwałym uszczerbkiem."
            if mos >= 15
            else "Brak marginesu bezpieczeństwa oznacza, że spowolnienie wyników może wywołać dotkliwą korektę kursu."
        )

        altman_str = f"{data.altman_z_score}" if data.altman_z_score is not None else "N/A"
        rule_1_risks = f"{debt_status} {val_risk} Płynność bieżąca: {data.current_ratio}x. Altman Z-Score: {altman_str}."

        return {
            "thesis": thesis,
            "moat": moat,
            "rule_1_risks": rule_1_risks,
        }
