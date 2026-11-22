import React, { useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { TrendingUp, ShieldAlert, CheckCircle2, ArrowUpRight, ArrowDownRight, Clock, Trash2, Award } from 'lucide-react';

export default function PortfolioView({ summary, onSelectTicker, onRemoveHolding, loading }) {
  const [activeSubTab, setActiveSubTab] = useState('overview');

  if (loading || !summary) {
    return (
      <div className="py-20 text-center text-neutral-500 font-mono text-sm">
        Ładowanie danych portfela demonstracyjnego...
      </div>
    );
  }

  const {
    total_portfolio_value,
    total_invested,
    total_pnl_cash,
    total_pnl_pct,
    benchmark_sp500_pnl_pct,
    alpha_pct,
    positions_count,
    holdings,
    equity_curve,
    rule_1_compliance
  } = summary;

  return (
    <div className="space-y-6">
      {/* Intro Card */}
      <div className="bg-white border border-neutral-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-neutral-500 uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            1-Roczny Audyt Forward-Test (Konto Demo Admina)
          </div>
          <h2 className="text-xl font-serif font-bold text-neutral-900">
            Weryfikacja Skuteczności Modelu Buffetta
          </h2>
          <p className="text-xs text-neutral-600 max-w-2xl mt-1">
            Wszystkie rekomendacje są rejestrowane w bazie z niezmiennym znacznikiem czasu i audytowane codziennie względem benchmarku S&P 500.
          </p>
        </div>
        <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-3 text-right">
          <div className="text-[11px] font-mono text-neutral-500 uppercase">Zasada #1: Ochrona Kapitału</div>
          <div className="text-xs font-medium text-emerald-700 flex items-center gap-1.5 justify-end mt-0.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>{rule_1_compliance}</span>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-neutral-200 rounded-xl p-4 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase">Wartość Portfela Demo</div>
          <div className="text-2xl font-serif font-bold text-neutral-900 mt-1">
            ${total_portfolio_value?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">
            Wkład bazowy: ${total_invested?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>

        <div className="bg-white border border-neutral-200 rounded-xl p-4 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase">Wynik Portfela (P&L)</div>
          <div className={`text-2xl font-serif font-bold mt-1 flex items-center gap-1 ${total_pnl_pct >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
            {total_pnl_pct >= 0 ? '+' : ''}{total_pnl_pct}%
            <span className="text-xs font-sans font-normal text-neutral-500">
              (${total_pnl_cash >= 0 ? '+' : ''}{total_pnl_cash})
            </span>
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">
            Pozycje aktywne: {positions_count} spółki
          </div>
        </div>

        <div className="bg-white border border-neutral-200 rounded-xl p-4 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase">Benchmark S&P 500</div>
          <div className="text-2xl font-serif font-bold text-neutral-700 mt-1">
            +{benchmark_sp500_pnl_pct}%
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">
            Średni zwrot rynku w tym samym okresie
          </div>
        </div>

        <div className="bg-white border border-neutral-200 rounded-xl p-4 shadow-xs bg-amber-50/40">
          <div className="text-xs font-mono text-amber-900/80 uppercase font-semibold flex items-center justify-between">
            <span>Alfa Buffetta</span>
            <Award className="w-3.5 h-3.5 text-amber-600" />
          </div>
          <div className="text-2xl font-serif font-bold text-neutral-900 mt-1">
            +{alpha_pct}%
          </div>
          <div className="text-[11px] text-emerald-700 font-medium mt-1">
            Pobicie indeksu rynkowego
          </div>
        </div>
      </div>

      {/* Chart: Equity Curve vs S&P 500 */}
      <div className="bg-white border border-neutral-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 mb-4">
          <div>
            <h3 className="text-sm font-serif font-bold text-neutral-900">
              Krzywa Zwrotu: Portfel Buffetta vs S&P 500 (Ostatnie 90 dni)
            </h3>
            <p className="text-xs text-neutral-500">
              Audytowane zmiany wartości od momentu wygenerowania pierwszych sygnałów inwestycyjnych
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="flex items-center gap-1.5 text-neutral-900">
              <span className="w-3 h-0.5 bg-neutral-950 inline-block"></span> Portfel Buffetta
            </span>
            <span className="flex items-center gap-1.5 text-neutral-500">
              <span className="w-3 h-0.5 bg-neutral-400 inline-block border-dashed"></span> S&P 500
            </span>
          </div>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={equity_curve} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" stroke="#999" fontSize={11} tickLine={false} />
              <YAxis stroke="#999" fontSize={11} tickFormatter={(val) => `+${val}%`} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e5e5e5', borderRadius: '8px', fontSize: '12px' }}
                formatter={(val, name) => [`+${val}%`, name === 'portfolio_return' ? 'Portfel Buffetta' : 'S&P 500']}
              />
              <Line type="monotone" dataKey="portfolio_return" stroke="#171717" strokeWidth={2.5} dot={{ r: 3, fill: '#171717' }} />
              <Line type="monotone" dataKey="benchmark_return" stroke="#9ca3af" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Holdings Table */}
      <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-xs">
        <div className="px-5 py-4 border-b border-neutral-200 flex justify-between items-center bg-neutral-50/50">
          <div>
            <h3 className="text-sm font-serif font-bold text-neutral-900">Otwarte Pozycje w Portfelu Demo</h3>
            <p className="text-xs text-neutral-500">Wyselekcjonowane spółki podlegające 1-rocznemu audytowi</p>
          </div>
          <span className="text-xs font-mono text-neutral-500 bg-white border border-neutral-200 px-2 py-1 rounded">
            {holdings.length} aktywne
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50/80 font-mono text-neutral-500 uppercase">
                <th className="py-3 px-4 font-semibold">Ticker / Spółka</th>
                <th className="py-3 px-4 font-semibold text-right">Kurs Zakupu</th>
                <th className="py-3 px-4 font-semibold text-right">Aktualny Kurs</th>
                <th className="py-3 px-4 font-semibold text-right">Wycena DCF</th>
                <th className="py-3 px-4 font-semibold text-right">Zwrot Pozycji</th>
                <th className="py-3 px-4 font-semibold text-right">S&P 500</th>
                <th className="py-3 px-4 font-semibold text-right">Przewaga (Alfa)</th>
                <th className="py-3 px-4 text-center">Akcje</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {holdings.map((h) => {
                const alpha = roundNumber(h.pnl_pct - h.benchmark_pnl_pct);
                return (
                  <tr key={h.id} className="hover:bg-neutral-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-neutral-900 font-mono text-sm cursor-pointer hover:underline" onClick={() => onSelectTicker(h.ticker)}>
                        {h.ticker}
                      </div>
                      <div className="text-[11px] text-neutral-500 truncate max-w-[180px]">{h.company_name}</div>
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-neutral-600">${h.entry_price}</td>
                    <td className="py-3 px-4 text-right font-mono font-medium text-neutral-900">${h.current_price}</td>
                    <td className="py-3 px-4 text-right font-mono text-neutral-600">${h.intrinsic_value}</td>
                    <td className="py-3 px-4 text-right font-mono">
                      <span className={`inline-flex items-center gap-0.5 font-bold ${h.pnl_pct >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                        {h.pnl_pct >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                        {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-neutral-500">
                      +{h.benchmark_pnl_pct}%
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-neutral-900">
                      {alpha >= 0 ? `+${alpha}%` : `${alpha}%`}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => onSelectTicker(h.ticker)}
                          className="px-2 py-1 text-[11px] bg-neutral-100 hover:bg-neutral-200 text-neutral-800 rounded font-medium transition-colors"
                        >
                          Analiza
                        </button>
                        <button
                          onClick={() => onRemoveHolding(h.id)}
                          title="Usuń z portfela demo"
                          className="p-1 text-neutral-400 hover:text-rose-600 rounded transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
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

function roundNumber(num) {
  return Math.round(num * 100) / 100;
}
