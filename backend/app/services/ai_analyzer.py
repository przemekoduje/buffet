import os
import httpx
from typing import Dict, Any
from app.config import settings
from app.providers.base import FundamentalData

class AIAnalyzer:
    """
    Moduł analizy jakościowej w stylu Warrena Buffetta:
    - Ocena fosy ekonomicznej (Moat)
    - Weryfikacja zarządu i alokacji kapitału
    - Ścisła weryfikacja Reguły 1: 'Nigdy nie trać pieniędzy'
    """

    @classmethod
    async def analyze_company(cls, data: FundamentalData, eval_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Jeśli podano klucz GEMINI_API_KEY, odpytuje Gemini 1.5/2.5.
        W przeciwnym razie generuje precyzyjny, strukturalny 'Memoriał Inwestycyjny Buffetta'
        w oparciu o reguły heurystyczne.
        """
        gemini_key = settings.GEMINI_API_KEY
        if gemini_key:
            try:
                return await cls._query_gemini(data, eval_result, gemini_key)
            except Exception as e:
                print(f"[Gemini API fallback] {e}")

        # Inteligentny generator heurystyczny (w stylu Buffetta)
        return cls._generate_buffett_memo(data, eval_result)

    @classmethod
    async def _query_gemini(cls, data: FundamentalData, eval_result: Dict[str, Any], api_key: str) -> Dict[str, str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = f"""
Jesteś wirtualnym Warrenem Buffettem i Charlim Mungerem. Oceń spółkę {data.company_name} ({data.ticker}).
Pamiętaj o dwóch najważniejszych zasadach:
1. Nigdy nie trać pieniędzy.
2. Nigdy nie zapominaj o regule numer 1.

Dane spółki:
- Cena: ${data.current_price} | Wycena Intrinsic Value: ${eval_result['intrinsic_value']}
- Margines bezpieczeństwa: {eval_result['margin_of_safety_pct']}%
- ROIC: {data.roic_pct}% | ROE: {data.roe_pct}%
- Marża brutto: {data.gross_margin_pct}% | Zadłużenie/FCF: {data.net_debt_to_fcf}
- Buffett Score: {eval_result['buffett_score']}/100

Zwróć odpowiedź w 3 sekcjach JSON z kluczami:
1. thesis: (Główna teza inwestycyjna, czy to wspaniały biznes w rozsądnej cenie?)
2. moat: (Analiza fosy ekonomicznej: pricing power, bariery wejścia, marka)
3. rule_1_risks: (Krytyczna ocena ryzyka utraty kapitału - co może pójść nie tak?)
Napisz to po polsku, w eleganckim, wyważonym stylu Buffetta.
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                import json
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                return {
                    "thesis": parsed.get("thesis", ""),
                    "moat": parsed.get("moat", ""),
                    "rule_1_risks": parsed.get("rule_1_risks", "")
                }
        raise Exception("Gemini response error")

    @classmethod
    def _generate_buffett_memo(cls, data: FundamentalData, eval_result: Dict[str, Any]) -> Dict[str, str]:
        score = eval_result["buffett_score"]
        mos = eval_result["margin_of_safety_pct"]
        roic = data.roic_pct
        gm = data.gross_margin_pct
        debt_fcf = data.net_debt_to_fcf

        # Teza
        if score >= 75 and mos > 15:
            thesis = (
                f"Wybitne przedsiębiorstwo handlujące ze znaczącym dyskontem ({mos}% marginesu bezpieczeństwa). "
                f"Generuje ${data.free_cash_flow_ttm/1e9:.1f} mld gotówki rocznie przy znakomitym ROIC ({roic}%). "
                f"Zarząd alokuje kapitał z korzyścią dla akcjonariuszy. Idealny kandydat do długoterminowego portfela w myśl zasady 'Kup wspaniałą firmę w uczciwej cenie'."
            )
        elif score >= 55:
            thesis = (
                f"Solidny biznes o ugruntowanej pozycji, lecz obecna wycena rynkowa (${data.current_price}) "
                f"odzwierciedla większość jego zalet (margines bezpieczeństwa: {mos}%). Wymaga cierpliwości i oczekiwania na rynkową przecenę."
            )
        else:
            thesis = (
                f"Biznes niespełniający rygorystycznych kryteriów Berkshire Hathaway. Słabe zwroty z kapitału lub "
                f"zbyt wysokie ryzyko bilansowe nie zapewniają odpowiedniej poduszki ochronnej dla kapitału."
            )

        # Fosa (Moat)
        if gm >= 50:
            moat = (
                f"Nadzwyczajna fosa ekonomiczna (Marża brutto {gm}%). Firma posiada potężny 'pricing power' "
                f"— może podnosić ceny bez obawy o odpływ klientów. Działa jak punkt poboru opłat (tollbooth) w swojej branży."
            )
        elif gm >= 35:
            moat = (
                f"Stabilna fosa ekonomiczna (Marża brutto {gm}%). Silna marka i baza lojalnych klientów "
                f"zapewniają obronę przed konkurencją, choć presja rynkowa wymaga stałych nakładów kapitałowych."
            )
        else:
            moat = (
                f"Wąska lub zanikająca fosa (Marża brutto {gm}%). Produkt nosi znamiona towaru masowego (commodity), "
                f"gdzie konkurencja cenowa ogranicza długoterminową rentowność kapitału."
            )

        # Reguła 1: Nie trać pieniędzy
        if debt_fcf == 0:
            debt_status = "Spółka posiada zerowy dług netto i obfitą poduszkę gotówkową, co całkowicie eliminuje ryzyko niewypłacalności."
        elif debt_fcf <= 2.5:
            debt_status = f"Zadłużenie ({debt_fcf:.1f}x FCF) jest całkowicie bezpieczne i może być spłacone z niecałych trzech lat zysków gotówkowych."
        else:
            debt_status = f"Uwaga: Zadłużenie ({debt_fcf:.1f}x FCF) przekracza zalecany limit Buffetta (<3x) i stanowi istotny czynnik ryzyka w okresie recesji."

        val_risk = "Niedoszacowanie rynkowe chroni kapitał przed trwałym uszczerbkiem." if mos >= 15 else "Brak marginesu bezpieczeństwa oznacza, że jakiekolwiek spowolnienie może wywołać dotkliwą korektę kursu."

        rule_1_risks = f"{debt_status} {val_risk} Płynność bieżąca: {data.current_ratio}x. Altman Z-Score: {data.altman_z_score or 'N/A'}."

        return {
            "thesis": thesis,
            "moat": moat,
            "rule_1_risks": rule_1_risks
        }
