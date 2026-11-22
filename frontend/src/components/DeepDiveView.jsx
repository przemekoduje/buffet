import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, ArrowUpRight, Plus, Sparkles, Building2, HelpCircle } from 'lucide-react';

export default function DeepDiveView({ ticker, onAddToDemo, onBackToScreener }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    fetch(`/api/analysis/${ticker}`)
      .then((res) => res.json())
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [ticker]);

  const handleAdd = async () => {
    setAdding(true);
    try {
      const res = await onAddToDemo(ticker);
      setMessage({ type: 'success', text: res.message || 'Dodano spółkę do portfela audytowego!' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Błąd dodawania do portfela.' });
    } finally {
      setAdding(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="py-24 text-center text-neutral-500 font-mono text-sm">
        Pobieranie sprawozdań finansowych i generowanie memoriału AI dla {ticker}...
      </div>
    );
  }

  const { fundamental, valuation, ai_memo, buffett_principles } = data;
  const isUndervalued = valuation.margin_of_safety_pct > 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Info */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl font-bold font-mono text-neutral-900">{fundamental.ticker}</span>
            <span className="text-xs bg-neutral-100 text-neutral-600 px-2 py-0.5 rounded font-medium border border-neutral-200">
              {fundamental.sector} &bull; {fundamental.industry}
            </span>
          </div>
          <h2 className="text-2xl font-serif font-bold text-neutral-900">{fundamental.company_name}</h2>
          <div className="flex items-center gap-4 text-xs font-mono text-neutral-500 mt-2">
            <span>Kapitalizacja: ${(fundamental.market_cap / 1e9).toFixed(1)} mld</span>
            <span>&bull;</span>
            <span>C/Z (P/E): {fundamental.pe_ratio}</span>
            <span>&bull;</span>
            <span>Dywidenda: {fundamental.dividend_yield_pct}%</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-end md:items-center gap-3">
          <div className="text-right">
            <div className="text-[11px] font-mono text-neutral-400 uppercase">Aktualny Kurs</div>
            <div className="text-2xl font-serif font-bold text-neutral-900">${fundamental.current_price}</div>
          </div>
          <button
            onClick={handleAdd}
            disabled={adding}
            className="px-4 py-2.5 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-all shadow-xs flex items-center gap-2 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>{adding ? 'Zapisywanie...' : 'Dodaj do Portfela Demo'}</span>
          </button>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-lg text-xs border ${
          message.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-800'
        }`}>
          {message.text}
        </div>
      )}

      {/* Valuation & Margin of Safety Spotlight */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-neutral-200 rounded-xl p-5 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase">Wartość Wewnętrzna (DCF)</div>
          <div className="text-3xl font-serif font-bold text-neutral-900 mt-1">
            ${valuation.intrinsic_value}
          </div>
          <p className="text-[11px] text-neutral-500 mt-1">
            Wyliczona na bazie 10-letniej projekcji Zysku Właścicielskiego (Owner Earnings).
          </p>
        </div>

        <div className={`border rounded-xl p-5 shadow-xs ${isUndervalued ? 'bg-emerald-50/50 border-emerald-200' : 'bg-neutral-50 border-neutral-200'}`}>
          <div className="text-xs font-mono text-neutral-500 uppercase">Margines Bezpieczeństwa</div>
          <div className={`text-3xl font-serif font-bold mt-1 ${isUndervalued ? 'text-emerald-700' : 'text-neutral-700'}`}>
            {isUndervalued ? `+${valuation.margin_of_safety_pct}%` : `${valuation.margin_of_safety_pct}%`}
          </div>
          <p className="text-[11px] text-neutral-600 mt-1">
            {isUndervalued ? 'Kurs dyskontuje ryzyko — poduszka ochronna kapitału.' : 'Brak marginesu — ryzyko zakupu na szczycie wyceny.'}
          </p>
        </div>

        <div className="bg-white border border-neutral-200 rounded-xl p-5 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase">Buffett Score</div>
          <div className="text-3xl font-serif font-bold text-neutral-900 mt-1 flex items-center gap-2">
            {valuation.buffett_score}
            <span className="text-xs font-mono font-normal text-neutral-400">/ 100</span>
          </div>
          <div className="mt-1">
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              valuation.recommendation === 'STRONG_BUY' ? 'bg-emerald-100 text-emerald-800' :
              valuation.recommendation === 'BUY' ? 'bg-blue-100 text-blue-800' :
              valuation.recommendation === 'HOLD' ? 'bg-amber-100 text-amber-800' :
              'bg-neutral-100 text-neutral-600'
            }`}>
              Rekomendacja: {valuation.recommendation}
            </span>
          </div>
        </div>
      </div>

      {/* AI Warren Buffett Memo */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-600" />
            <h3 className="text-sm font-serif font-bold text-neutral-900">
              Memoriał Inwestycyjny AI (Głos Warrena Buffetta)
            </h3>
          </div>
          <span className="text-[11px] font-mono text-neutral-400">
            Analiza jakościowa sprawozdań & transkryptów
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-1">
            <h4 className="text-xs font-mono font-bold text-neutral-700 uppercase">Teza Inwestycyjna</h4>
            <p className="text-xs text-neutral-600 leading-relaxed font-sans">
              {ai_memo.thesis}
            </p>
          </div>

          <div className="space-y-1">
            <h4 className="text-xs font-mono font-bold text-neutral-700 uppercase">Fosa Ekonomiczna (Moat)</h4>
            <p className="text-xs text-neutral-600 leading-relaxed font-sans">
              {ai_memo.moat}
            </p>
          </div>

          <div className="space-y-1">
            <h4 className="text-xs font-mono font-bold text-neutral-700 uppercase flex items-center gap-1 text-amber-800">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
              <span>Reguła 1: Audyt Ryzyka</span>
            </h4>
            <p className="text-xs text-neutral-600 leading-relaxed font-sans">
              {ai_memo.rule_1_risks}
            </p>
          </div>
        </div>
      </div>

      {/* 4 Buffett Principles Checklist */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs">
        <h3 className="text-sm font-serif font-bold text-neutral-900 mb-4">
          Weryfikacja 4 Zasad Buffetta
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {buffett_principles.map((p, idx) => (
            <div key={idx} className="border border-neutral-100 rounded-lg p-3.5 bg-neutral-50/50 flex items-start gap-3">
              {p.satisfied ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-4 h-4 text-neutral-400 shrink-0 mt-0.5" />
              )}
              <div>
                <div className="text-xs font-bold text-neutral-900">{p.rule}</div>
                <div className="text-[11px] text-neutral-600 mt-0.5">{p.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
