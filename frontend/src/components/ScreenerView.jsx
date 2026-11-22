import React, { useState } from 'react';
import { Search, Filter, ArrowUpRight, ArrowDownRight, ShieldCheck, ShieldAlert, Sparkles, AlertCircle } from 'lucide-react';

export default function ScreenerView({ screenerData, onSelectTicker, onScanCustom, loading, activeProvider }) {
  const [minScore, setMinScore] = useState(0);
  const [undervaluedOnly, setUndervaluedOnly] = useState(false);
  const [searchTicker, setSearchTicker] = useState('');
  const [scanError, setScanError] = useState(null);

  const filteredItems = (screenerData?.items || []).filter((item) => {
    if (item.buffett_score < minScore) return false;
    if (undervaluedOnly && item.margin_of_safety_pct <= 0) return false;
    return true;
  });

  const handleCustomScan = async (e) => {
    e.preventDefault();
    if (!searchTicker.trim()) return;
    setScanError(null);
    try {
      await onScanCustom(searchTicker.trim().toUpperCase());
      setSearchTicker('');
    } catch (err) {
      setScanError(`Nie znaleziono symbolu ${searchTicker.toUpperCase()}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Bar with Filters & Search */}
      <div className="bg-white border border-neutral-200 rounded-xl p-5 shadow-xs flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4">
        <div>
          <h2 className="text-xl font-serif font-bold text-neutral-900">
            Screener Spółek Warrena Buffetta
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">
            Filtrowanie pod kątem trwałej fosy ekonomicznej (ROIC &gt; 12%), niskiego zadłużenia i dyskonta cenowego.
          </p>
        </div>

        {/* Live Search Custom Ticker */}
        <form onSubmit={handleCustomScan} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              placeholder="Wpisz dowolny ticker (np. MSFT, COST)..."
              value={searchTicker}
              onChange={(e) => setSearchTicker(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs border border-neutral-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-neutral-900 w-64 uppercase font-mono"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            Przeskanuj
          </button>
        </form>
      </div>

      {scanError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>{scanError}</span>
        </div>
      )}

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white border border-neutral-200 rounded-xl px-4 py-3 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-neutral-500 font-mono">Min. Buffett Score:</span>
            <select
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="border border-neutral-300 rounded px-2 py-1 text-xs focus:outline-none font-mono"
            >
              <option value={0}>Wszystkie (0+)</option>
              <option value={50}>Dobre (50+)</option>
              <option value={70}>Wysoka jakość (70+)</option>
              <option value={80}>Klasa Buffetta (80+)</option>
            </select>
          </div>

          <label className="flex items-center gap-2 cursor-pointer text-neutral-700 select-none">
            <input
              type="checkbox"
              checked={undervaluedOnly}
              onChange={(e) => setUndervaluedOnly(e.target.checked)}
              className="rounded border-neutral-300 text-neutral-900 focus:ring-0"
            />
            <span>Tylko z marginesem bezpieczeństwa (&gt; 0%)</span>
          </label>
        </div>

        <div className="text-neutral-500 font-mono text-[11px]">
          Znaleziono: <strong className="text-neutral-900">{filteredItems.length}</strong> spółek
        </div>
      </div>

      {/* Screener Table */}
      <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 font-mono text-neutral-500 uppercase">
                <th className="py-3 px-4 font-semibold">Spółka</th>
                <th className="py-3 px-4 font-semibold text-center">Buffett Score</th>
                <th className="py-3 px-4 font-semibold text-right">Aktualny Kurs</th>
                <th className="py-3 px-4 font-semibold text-right">Wartość Wewnętrzna (DCF)</th>
                <th className="py-3 px-4 font-semibold text-right">Margines Bezpieczeństwa</th>
                <th className="py-3 px-4 font-semibold text-right">ROIC (Fosa)</th>
                <th className="py-3 px-4 font-semibold text-right">Marża Brutto</th>
                <th className="py-3 px-4 font-semibold text-right">Zadłużenie / FCF</th>
                <th className="py-3 px-4 text-center">Reguła 1</th>
                <th className="py-3 px-4 text-center">Akcja</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filteredItems.map((item) => {
                const isUndervalued = item.margin_of_safety_pct > 0;
                return (
                  <tr key={item.ticker} className="hover:bg-neutral-50/70 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-neutral-900 font-mono text-sm cursor-pointer hover:underline" onClick={() => onSelectTicker(item.ticker)}>
                        {item.ticker}
                      </div>
                      <div className="text-[11px] text-neutral-500 truncate max-w-[160px]">{item.company_name}</div>
                    </td>

                    <td className="py-3 px-4 text-center">
                      <span className={`inline-block font-mono font-bold px-2 py-0.5 rounded text-xs ${
                        item.buffett_score >= 80 ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' :
                        item.buffett_score >= 65 ? 'bg-amber-100 text-amber-800 border border-amber-200' :
                        'bg-neutral-100 text-neutral-600'
                      }`}>
                        {item.buffett_score}/100
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right font-mono font-medium text-neutral-900">
                      ${item.current_price}
                    </td>

                    <td className="py-3 px-4 text-right font-mono text-neutral-700">
                      ${item.intrinsic_value}
                    </td>

                    <td className="py-3 px-4 text-right font-mono">
                      <span className={`font-bold inline-flex items-center gap-0.5 ${
                        isUndervalued ? 'text-emerald-700' : 'text-rose-700'
                      }`}>
                        {isUndervalued ? `+${item.margin_of_safety_pct}%` : `${item.margin_of_safety_pct}%`}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right font-mono">
                      <span className={item.roic_pct >= 15 ? 'text-neutral-900 font-semibold' : 'text-neutral-500'}>
                        {item.roic_pct}%
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right font-mono">
                      <span className={item.gross_margin_pct >= 40 ? 'text-emerald-700 font-medium' : 'text-neutral-600'}>
                        {item.gross_margin_pct}%
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right font-mono text-neutral-600">
                      {item.net_debt_to_fcf === 0 ? 'Brak długu' : `${item.net_debt_to_fcf}x`}
                    </td>

                    <td className="py-3 px-4 text-center">
                      {item.rule_number_one_risk === 'LOW' ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded-full">
                          <ShieldCheck className="w-3 h-3 text-emerald-600" /> Bezpieczna
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] text-amber-700 font-medium bg-amber-50 px-2 py-0.5 rounded-full">
                          <ShieldAlert className="w-3 h-3 text-amber-600" /> Ryzyko
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => onSelectTicker(item.ticker)}
                        className="px-2.5 py-1 text-xs bg-neutral-900 hover:bg-neutral-800 text-white rounded font-medium transition-colors flex items-center gap-1 mx-auto"
                      >
                        <Sparkles className="w-3 h-3" />
                        Analiza
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
