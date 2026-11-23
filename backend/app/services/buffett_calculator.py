from typing import Dict, Any, Tuple
from app.providers.base import FundamentalData


class BuffettCalculator:
    """
    Silnik wyceny i oceny spółki według zasad Warrena Buffetta:
    1. Trwała fosa ekonomiczna (ROIC > 15%, Gross Margin > 40%)
    2. Bezpieczny bilans (Reguła 1: Net Debt / FCF < 3 lata)
    3. Wycena Intrinsic Value na bazie znormalizowanego Owner Earnings (dynamiczny 10-letni DCF)
    4. Margines Bezpieczeństwa (Margin of Safety min. 15-30%)
    """

    @staticmethod
    def calculate_owner_earnings(data: FundamentalData) -> Tuple[float, str]:
        """
        Znormalizowany Zysk Właścicielski (Owner Earnings):
        - Gdy FCF TTM jest dodatni i spójny z historią -> używa FCF TTM (wygładzonego przy ekstremalnych skokach).
        - Gdy FCF TTM jest ujemny lub jednorazowo zaniżony (np. ogromny CapEx rozwojowy AI jak w GOOGL
          albo jednorazowa ugoda podatkowa jak w KO) -> normalizuje średnią z dodatniego historycznego FCF
          lub konserwatywną częścią zysku netto (70% Net Income).
        """
        pos_hist = [x for x in (data.fcf_history_5y or []) if x > 0]
        avg_hist_fcf = (sum(pos_hist) / len(pos_hist)) if pos_hist else 0.0
        fcf_ttm = data.free_cash_flow_ttm
        ni_ttm = data.net_income_ttm

        if fcf_ttm <= 0:
            if avg_hist_fcf > 0:
                # Jeśli firma ma wysoki zysk netto, ale przejściowo ujemny FCF przez CapEx rozwojowy
                if ni_ttm > avg_hist_fcf:
                    norm = 0.65 * avg_hist_fcf + 0.35 * (ni_ttm * 0.60)
                    return max(norm, avg_hist_fcf), "Znormalizowany (historia FCF + zysk netto — wysoki CapEx)"
                return avg_hist_fcf, "Średni historyczny FCF (przejściowo ujemny FCF TTM)"
            if ni_ttm > 0:
                return ni_ttm * 0.70, "Szacunek z zysku netto (70% Net Income)"
            return 0.0, "Brak dodatnich przepływów"

        # Jednorazowe zaniżenie FCF TTM (np. spłata podatku / chwilowy CapEx)
        if avg_hist_fcf > 0 and fcf_ttm < 0.65 * avg_hist_fcf and ni_ttm > avg_hist_fcf:
            norm = 0.70 * avg_hist_fcf + 0.30 * (ni_ttm * 0.75)
            return norm, "Znormalizowany (wygładzony względem historii FCF i zysku netto)"

        # Jednorazowy ekstremalny skok FCF (np. wahania floatu ubezpieczeniowego w BRK.B)
        if avg_hist_fcf > 0 and fcf_ttm > 1.75 * avg_hist_fcf:
            norm = 0.55 * fcf_ttm + 0.45 * avg_hist_fcf
            return norm, "Wygładzony FCF (korekta jednorazowego skoku przepływów)"

        return fcf_ttm, "FCF TTM"

    @classmethod
    def get_dcf_assumptions(cls, data: FundamentalData) -> Dict[str, float]:
        """
        Dobiera konserwatywne, ale dopasowane do biznesu założenia DCF:
        - Wzrost lata 1-5: oparty o wieloletni CAGR przychodów, ograniczony skalą firmy i sektorem
          (dla mega-capów >$300 mld max 12%, dla spółek finansowych/ubezpieczeniowych max 7%)
        - Wzrost lata 6-10: wygaszanie tempa (60% tempa z lat 1-5, ograniczone do [3%, 8%])
        - Stopa dyskontowa (hurdle rate Buffetta): 9.0% dla firm o niskim ryzyku bilansowym, 9.5-10.5% dla bardziej zadłużonych
        - Wzrost terminalny: 3.0% (długoterminowy nominalny wzrost PKB)
        """
        raw_cagr = max(data.revenue_growth_5y_cagr, 0.0) / 100.0
        is_financial = "financial" in (data.sector or "").lower() or "insurance" in (data.industry or "").lower()

        if is_financial:
            max_g1 = 0.07
        elif data.market_cap >= 500e9:
            max_g1 = 0.11
        elif data.market_cap >= 200e9:
            max_g1 = 0.13
        else:
            max_g1 = 0.16

        g_1_5 = min(max(raw_cagr * 0.85, 0.03), max_g1)
        g_6_10 = min(max(g_1_5 * 0.60, 0.03), 0.08)

        # Używamy znormalizowanego Owner Earnings zamiast surowego FCF TTM do oceny dźwigni,
        # aby jednorazowe zdarzenia (np. ugoda podatkowa KO) nie zawyżały sztucznie stopy dyskontowej.
        oe, _ = cls.calculate_owner_earnings(data)
        if data.net_debt <= 0:
            eff_debt_to_oe = 0.0
        elif oe > 0:
            eff_debt_to_oe = data.net_debt / oe
        else:
            eff_debt_to_oe = data.net_debt_to_fcf

        if eff_debt_to_oe <= 2.5 and data.gross_margin_pct >= 35:
            discount_rate = 0.09
        elif eff_debt_to_oe <= 4.0:
            discount_rate = 0.095
        else:
            discount_rate = 0.105

        terminal_growth = 0.03
        return {
            "discount_rate": discount_rate,
            "growth_1_5": round(g_1_5, 4),
            "growth_6_10": round(g_6_10, 4),
            "terminal_growth": terminal_growth,
        }

    @classmethod
    def calculate_dcf_intrinsic_value(
        cls,
        data: FundamentalData,
        discount_rate: float = None,
        growth_rate_years_1_5: float = None,
        growth_rate_years_6_10: float = None,
        terminal_growth_rate: float = None,
    ) -> float:
        """
        Klasyczna 10-letnia wycena DCF na bazie znormalizowanego Owner Earnings
        z korektą o dług netto / gotówkę netto (bez podwójnego liczenia gotówki).
        """
        owner_earnings, _ = cls.calculate_owner_earnings(data)
        if owner_earnings <= 0 or data.shares_outstanding <= 0:
            return 0.0

        assumptions = cls.get_dcf_assumptions(data)
        r = discount_rate if discount_rate is not None else assumptions["discount_rate"]
        g1 = growth_rate_years_1_5 if growth_rate_years_1_5 is not None else assumptions["growth_1_5"]
        g2 = growth_rate_years_6_10 if growth_rate_years_6_10 is not None else assumptions["growth_6_10"]
        gt = terminal_growth_rate if terminal_growth_rate is not None else assumptions["terminal_growth"]

        pv_cash_flows = 0.0
        current_cf = owner_earnings

        # Lata 1 - 5
        for year in range(1, 6):
            current_cf *= (1 + g1)
            pv_cash_flows += current_cf / ((1 + r) ** year)

        # Lata 6 - 10
        for year in range(6, 11):
            current_cf *= (1 + g2)
            pv_cash_flows += current_cf / ((1 + r) ** year)

        # Wartość rezydualna (Terminal Value wg Gordona)
        terminal_cf = current_cf * (1 + gt)
        if r <= gt:
            r = gt + 0.01
        terminal_value = terminal_cf / (r - gt)
        pv_terminal_value = terminal_value / ((1 + r) ** 10)

        # Całkowita wartość przedsiębiorstwa
        enterprise_intrinsic_val = pv_cash_flows + pv_terminal_value

        # Korekta o dług netto (Equity Value = EV - Net Debt; ujemny net_debt = gotówka netto)
        # Dla sektora finansowego / ubezpieczeniowego (np. BRK.B, JPM, CB) gotówka w bilansie
        # obejmuje float ubezpieczeniowy / kapitał regulacyjny, więc nie dodajemy jej w całości jako wolnej gotówki.
        is_financial = "financial" in (data.sector or "").lower() or "insurance" in (data.industry or "").lower()
        if is_financial and data.net_debt < 0:
            # Konserwatywnie uwzględniamy max 35% gotówki netto jako realną nadwyżkę ponad float/rezerwy
            equity_intrinsic_val = enterprise_intrinsic_val - (data.net_debt * 0.35)
        else:
            equity_intrinsic_val = enterprise_intrinsic_val - data.net_debt
        if equity_intrinsic_val <= 0:
            return 0.0

        per_share_value = equity_intrinsic_val / data.shares_outstanding
        return round(per_share_value, 2)

    @classmethod
    def evaluate(cls, data: FundamentalData) -> Dict[str, Any]:
        """
        Kompleksowy audyt spółki i wyliczenie Buffett Score (0-100)
        oraz Marginesu Bezpieczeństwa.
        """
        owner_earnings, oe_method = cls.calculate_owner_earnings(data)
        assumptions = cls.get_dcf_assumptions(data)
        intrinsic_value = cls.calculate_dcf_intrinsic_value(data)
        

        if intrinsic_value > 0:
            margin_of_safety_pct = round(((intrinsic_value - data.current_price) / intrinsic_value) * 100, 1)
        else:
            margin_of_safety_pct = -99.9

        # --- Buffett Score (0-100) ---
        score = 0
        score_breakdown = {}

        # 1. ROIC (Zwrot z zainwestowanego kapitału) - Max 20 pkt
        if data.roic_pct >= 18:
            score += 20
            score_breakdown["roic"] = {"pts": 20, "max": 20, "status": "EXCELLENT", "desc": f"Wybitny ROIC {data.roic_pct}% (>18%)"}
        elif data.roic_pct >= 12:
            score += 14
            score_breakdown["roic"] = {"pts": 14, "max": 20, "status": "GOOD", "desc": f"Solidny ROIC {data.roic_pct}%"}
        else:
            score += 4
            score_breakdown["roic"] = {"pts": 4, "max": 20, "status": "WEAK", "desc": f"Niski ROIC {data.roic_pct}% (<12%)"}

        # 2. ROE (Zwrot z kapitału własnego) - Max 15 pkt
        if data.roe_pct >= 18:
            score += 15
            score_breakdown["roe"] = {"pts": 15, "max": 15, "status": "EXCELLENT", "desc": f"Wysokie ROE {data.roe_pct}%"}
        elif data.roe_pct >= 12:
            score += 10
            score_breakdown["roe"] = {"pts": 10, "max": 15, "status": "GOOD", "desc": f"Przyzwoite ROE {data.roe_pct}%"}
        else:
            score += 2
            score_breakdown["roe"] = {"pts": 2, "max": 15, "status": "WEAK", "desc": f"Słabe ROE {data.roe_pct}%"}

        # 3. Marża Brutto (Pricing power - Fosa) - Max 15 pkt
        if data.gross_margin_pct >= 45:
            score += 15
            score_breakdown["pricing_power"] = {"pts": 15, "max": 15, "status": "STRONG_MOAT", "desc": f"Silna fosa: Marża brutto {data.gross_margin_pct}%"}
        elif data.gross_margin_pct >= 30:
            score += 10
            score_breakdown["pricing_power"] = {"pts": 10, "max": 15, "status": "MODERATE", "desc": f"Umiarkowana marża {data.gross_margin_pct}%"}
        else:
            score += 3
            score_breakdown["pricing_power"] = {"pts": 3, "max": 15, "status": "NO_MOAT", "desc": f"Brak fosy cenowej ({data.gross_margin_pct}%)"}

        # 4. Bezpieczeństwo zadłużenia (Net Debt / FCF) - Max 20 pkt
        if data.net_debt <= 0:
            score += 20
            score_breakdown["debt_safety"] = {"pts": 20, "max": 20, "status": "ZERO_DEBT", "desc": "Gotówka netto (Brak zadłużenia netto)"}
        elif data.net_debt_to_fcf <= 2.5:
            score += 18
            score_breakdown["debt_safety"] = {"pts": 18, "max": 20, "status": "SAFE", "desc": f"Bezpieczny dług ({data.net_debt_to_fcf:.1f} lat FCF)"}
        elif data.net_debt_to_fcf <= 4.0:
            score += 10
            score_breakdown["debt_safety"] = {"pts": 10, "max": 20, "status": "ACCEPTABLE", "desc": f"Znośny dług ({data.net_debt_to_fcf:.1f} lat FCF)"}
        else:
            score += 0
            score_breakdown["debt_safety"] = {"pts": 0, "max": 20, "status": "HIGH_RISK", "desc": f"Niebezpieczne zadłużenie ({data.net_debt_to_fcf:.1f} lat FCF)"}

        # 5. Margines Bezpieczeństwa (Cena vs Wartość Wewnętrzna) - Max 20 pkt
        if margin_of_safety_pct >= 30:
            score += 20
            score_breakdown["valuation"] = {"pts": 20, "max": 20, "status": "DEEP_DISCOUNT", "desc": f"Duże niedowartościowanie (+{margin_of_safety_pct}%)"}
        elif margin_of_safety_pct >= 15:
            score += 14
            score_breakdown["valuation"] = {"pts": 14, "max": 20, "status": "UNDERVALUED", "desc": f"Niedowartościowana (+{margin_of_safety_pct}%)"}
        elif margin_of_safety_pct >= 0:
            score += 8
            score_breakdown["valuation"] = {"pts": 8, "max": 20, "status": "FAIR_VALUE", "desc": "Uczciwie wyceniona (brak marginesu)"}
        else:
            score += 0
            score_breakdown["valuation"] = {"pts": 0, "max": 20, "status": "OVERVALUED", "desc": f"Przewartościowana ({margin_of_safety_pct}%)"}

        # 6. Stabilność wzrostu przychodów (wieloletni CAGR) - Max 10 pkt
        if data.revenue_growth_5y_cagr >= 8:
            score += 10
            score_breakdown["growth"] = {"pts": 10, "max": 10, "status": "CONSISTENT", "desc": f"Stabilny wzrost przychodów CAGR {data.revenue_growth_5y_cagr}%"}
        elif data.revenue_growth_5y_cagr >= 3:
            score += 6
            score_breakdown["growth"] = {"pts": 6, "max": 10, "status": "MODEST", "desc": f"Umiarkowany wzrost CAGR {data.revenue_growth_5y_cagr}%"}
        else:
            score += 2
            score_breakdown["growth"] = {"pts": 2, "max": 10, "status": "STAGNANT", "desc": "Stagnacja przychodów"}

        # --- Reguła 1: "Nigdy nie trać pieniędzy" ---
        rule_1_warnings = []
        if data.net_debt_to_fcf > 4.5:
            rule_1_warnings.append("Wysokie ryzyko zadłużenia — obsługa długu pochłonie ponad 4.5 lat wolnych przepływów!")
        if data.current_ratio < 1.0:
            rule_1_warnings.append("Wskaźnik płynności bieżącej poniżej 1.0 — ryzyko zatorów płatniczych.")
        if margin_of_safety_pct < -25:
            rule_1_warnings.append("Znaczące przewartościowanie — wysokie ryzyko spadku kursu.")
        if data.roic_pct < 8:
            rule_1_warnings.append("Niska rentowność kapitału — brak trwałej fosy ekonomicznej.")

        if len(rule_1_warnings) == 0:
            rule_1_risk_level = "LOW"
        elif len(rule_1_warnings) <= 2:
            rule_1_risk_level = "MODERATE"
        else:
            rule_1_risk_level = "HIGH"

        # Rekomendacja końcowa
        if score >= 80 and margin_of_safety_pct >= 20 and rule_1_risk_level == "LOW":
            recommendation = "STRONG_BUY"
        elif score >= 65 and margin_of_safety_pct >= 10:
            recommendation = "BUY"
        elif score >= 50 or margin_of_safety_pct >= -10:
            recommendation = "HOLD"
        else:
            recommendation = "AVOID"

        return {
            "intrinsic_value": intrinsic_value,
            "margin_of_safety_pct": margin_of_safety_pct,
            "buffett_score": score,
            "recommendation": recommendation,
            "rule_number_one_risk": rule_1_risk_level,
            "rule_1_warnings": rule_1_warnings,
            "score_breakdown": score_breakdown,
            "owner_earnings_ttm": round(owner_earnings / 1e6, 2),  # w mln $
            "owner_earnings_method": oe_method,
            "dcf_assumptions": {
                "discount_rate_pct": round(assumptions["discount_rate"] * 100, 1),
                "growth_y1_5_pct": round(assumptions["growth_1_5"] * 100, 1),
                "growth_y6_10_pct": round(assumptions["growth_6_10"] * 100, 1),
                "terminal_growth_pct": round(assumptions["terminal_growth"] * 100, 1),
            },
        }
