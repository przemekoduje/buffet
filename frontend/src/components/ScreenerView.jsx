import React, { useState } from 'react';
import {
  Search,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  AlertCircle,
  RefreshCw,
  Bell,
  Briefcase,
  Clock,
  TrendingDown,
  TrendingUp,
  Activity,
  Layers,
} from 'lucide-react';

const BASKET_LABELS = {
  us_quality: { label: 'US Quality', cls: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  sp500_value: { label: 'S&P 500 Value', cls: 'bg-amber-50 text-amber-800 border-amber-200' },
  dividend_aristocrats: { label: 'Arystokraci', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
};

const REC_STYLES = {
  STRONG_BUY: { label: 'STRONG BUY', cls: 'bg-emerald-700 text-white' },
  BUY: { label: 'BUY', cls: 'bg-emerald-100 text-emerald-800 border border-emerald-300' },
  HOLD: { label: 'HOLD', cls: 'bg-amber-50 text-amber-800 border border-amber-200' },
  AVOID: { label: 'AVOID', cls: 'bg-rose-50 text-rose-700 border border-rose-200' },
};

export default function ScreenerView({
  screenerData,
  onSelectTicker,
  onOpenOrderModal,
  onScanCustom,
  onRunEodScan,
  onCheckAlerts,
  loading,
  scanning,
  alertsChecking,
}) {
  const [activeBasket, setActiveBasket] = useState('all');
  const [minScore, setMinScore] = useState(0);
  const [undervaluedOnly, setUndervaluedOnly] = useState(false);
  const [buffettPicksOnly, setBuffettPicksOnly] = useState(false);
  const [hideInPortfolio, setHideInPortfolio] = useState(false);
  const [searchTicker, setSearchTicker] = useState('');
  const [scanError, setScanError] = useState(null);

  const items = screenerData?.items || [];
  const baskets = screenerData?.baskets || [];
  const alerts = screenerData?.alerts || [];
  const session = screenerData?.market_session;

  const filteredItems = items.filter((item) => {
    if (activeBasket !== 'all' && !(item.baskets || []).includes(activeBasket)) return false;
    if (item.buffett_score < minScore) return false;
    if (undervaluedOnly && item.margin_of_safety_pct <= 0) return false;
    if (buffettPicksOnly && !item.is_buffett_pick) return false;
    if (hideInPortfolio && item.in_paper_trading) return false;
    return true;
  });

  const inPortfolioCount = filteredItems.filter((i) => i.in_paper_trading).length;
  const buySignalsCount = filteredItems.filter((i) =>
    ['STRONG_BUY', 'BUY'].includes(i.recommendation)
  ).length;

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
      {/* Top Bar: Title, EOD Status & Custom Search */}
      <div className="bg-white border border-neutral-200 rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col lg:flex-row justify-between items-stretch lg:items-center gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-serif font-bold text-neutral-900">
                Screener Rynku Warrena Buffetta (EOD & Intraday)
              </h2>
              {session && (
                <span
                  className={`inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${
                    session.is_open
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-neutral-100 text-neutral-600 border-neutral-200'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      session.is_open ? 'bg-emerald-500 animate-pulse' : 'bg-neutral-400'
                    }`}
                  />
                  {session.label}
                </span>
              )}
            </div>
            <p className="text-xs text-neutral-500 mt-1">
              Automatyczny skan koszyków (<strong>US Quality</strong>, <strong>S&P 500 Value</strong>,{' '}
              <strong>Dywidendowi Arystokraci</strong>) po zamknięciu sesji USA ({session?.next_eod_schedule || '16:15 ET'}) oraz alerty sesyjne co 15 min.
            </p>
          </div>

          {/* Live Search Custom Ticker */}
          <form onSubmit={handleCustomScan} className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
              <input
                type="text"
                placeholder="Skanuj dowolny ticker (np. MSFT, PKO.WA)..."
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

        {/* EOD Metadata + Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-neutral-100 text-xs">
          <div className="flex flex-wrap items-center gap-4 text-neutral-500 font-mono text-[11px]">
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-neutral-400" />
              Ostatni skan EOD: <strong className="text-neutral-800">{screenerData?.last_scan_at || 'Brak'}</strong>
            </span>
            <span>
              Uniwersum: <strong className="text-neutral-800">{screenerData?.universe_total || items.length}</strong> spółek
            </span>
            <span>
              Rekomendacje BUY/STRONG BUY: <strong className="text-emerald-700">{buySignalsCount}</strong>
            </span>
            <span>
              W Paper Trading: <strong className="text-indigo-700">{inPortfolioCount}</strong>
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={onCheckAlerts}
              disabled={alertsChecking}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-neutral-300 bg-white hover:bg-neutral-50 text-neutral-800 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              <Bell className={`w-3.5 h-3.5 text-amber-600 ${alertsChecking ? 'animate-bounce' : ''}`} />
              {alertsChecking ? 'Sprawdzam sesję...' : 'Sprawdź alerty sesyjne'}
            </button>

            <button
              onClick={onRunEodScan}
              disabled={scanning}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
              {scanning ? 'Skanuję koszyki (~20s)...' : 'Skanuj rynek teraz (EOD)'}
            </button>
          </div>
        </div>
      </div>

      {scanError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>{scanError}</span>
        </div>
      )}

      {/* Intraday Alerts Section */}
      <div className="bg-white border border-neutral-200 rounded-xl p-5 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-amber-600" />
            <h3 className="text-sm font-serif font-bold text-neutral-900">
              Alerty Sesyjne (Intraday) — Ciekawe Zdarzenia Rynkowe
            </h3>
            <span className="text-[11px] font-mono bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded-full">
              {alerts.length}
            </span>
          </div>
          {session?.last_intraday_check && (
            <span className="text-[11px] font-mono text-neutral-400">
              Ostatni check: {session.last_intraday_check}
            </span>
          )}
        </div>

        {alerts.length === 0 ? (
          <p className="text-xs text-neutral-500">
            Brak istotnych anomalii sesyjnych (spadki okazjonalne &le; -2%, ruchy &ge; 3%, skoki wolumenu &ge; 1.75x). Kliknij <strong>„Sprawdź alerty sesyjne”</strong>, aby wykonać szybki skan bieżącej sesji.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {alerts.slice(0, 6).map((alert) => {
              const isDrop = alert.change_pct < 0;
              const isHigh = alert.severity === 'HIGH';
              return (
                <div
                  key={alert.id}
                  onClick={() => onSelectTicker(alert.ticker)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-xs ${
                    isHigh
                      ? 'bg-emerald-50/70 border-emerald-200 hover:border-emerald-400'
                      : alert.alert_type === 'VOLUME_SPIKE'
                      ? 'bg-indigo-50/50 border-indigo-200 hover:border-indigo-400'
                      : isDrop
                      ? 'bg-amber-50/60 border-amber-200 hover:border-amber-400'
                      : 'bg-neutral-50 border-neutral-200 hover:border-neutral-400'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-1.5">
                      {alert.alert_type === 'VOLUME_SPIKE' ? (
                        <Activity className="w-3.5 h-3.5 text-indigo-600" />
                      ) : isDrop ? (
                        <TrendingDown className="w-3.5 h-3.5 text-emerald-700" />
                      ) : (
                        <TrendingUp className="w-3.5 h-3.5 text-neutral-700" />
                      )}
                      <span className="font-mono font-bold text-xs text-neutral-900">
                        {alert.ticker}
                      </span>
                      <span
                        className={`font-mono text-[11px] font-semibold ${
                          isDrop ? 'text-rose-700' : 'text-emerald-700'
                        }`}
                      >
                        {alert.change_pct > 0 ? `+${alert.change_pct}%` : `${alert.change_pct}%`}
                      </span>
                    </div>
                    {alert.in_paper_trading && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono bg-indigo-100 text-indigo-800 px-1.5 py-0.5 rounded">
                        <Briefcase className="w-2.5 h-2.5" /> Paper
                      </span>
                    )}
                  </div>
                  <div className="text-xs font-semibold text-neutral-900 leading-snug">
                    {alert.title}
                  </div>
                  <p className="text-[11px] text-neutral-600 mt-1 line-clamp-2">
                    {alert.message}
                  </p>
                  <div className="flex items-center justify-between mt-2 text-[10px] font-mono text-neutral-400">
                    <span>Score: {alert.buffett_score}/100</span>
                    <span>{alert.created_at}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Curated Baskets Selector */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {(baskets.length > 0
          ? baskets
          : [
              { id: 'all', name: 'Wszystkie koszyki', subtitle: 'Pełne zestawienie', count: items.length },
              { id: 'us_quality', name: 'US Quality', subtitle: 'Fosa i wysokie ROIC', count: 0 },
              { id: 'sp500_value', name: 'S&P 500 Value', subtitle: 'Dyskonto i przepływy FCF', count: 0 },
              { id: 'dividend_aristocrats', name: 'Dywidendowi Arystokraci', subtitle: '25+ lat wzrostu dywidendy', count: 0 },
            ]
        ).map((b) => {
          const isSelected = activeBasket === b.id;
          return (
            <button
              key={b.id}
              onClick={() => setActiveBasket(b.id)}
              className={`text-left p-4 rounded-xl border transition-all cursor-pointer ${
                isSelected
                  ? 'bg-neutral-900 text-white border-neutral-900 shadow-sm'
                  : 'bg-white text-neutral-900 border-neutral-200 hover:border-neutral-400'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="inline-flex items-center gap-1.5 font-serif font-bold text-sm">
                  <Layers className={`w-3.5 h-3.5 ${isSelected ? 'text-amber-300' : 'text-neutral-500'}`} />
                  {b.name}
                </span>
                <span
                  className={`font-mono text-[11px] px-2 py-0.5 rounded-full ${
                    isSelected ? 'bg-neutral-800 text-amber-300' : 'bg-neutral-100 text-neutral-600'
                  }`}
                >
                  {b.count}
                </span>
              </div>
              <p className={`text-[11px] leading-snug ${isSelected ? 'text-neutral-300' : 'text-neutral-500'}`}>
                {b.subtitle}
              </p>
            </button>
          );
        })}
      </div>

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
              <option value={65}>Warte uwagi (65+)</option>
              <option value={80}>Klasa Buffetta (80+)</option>
            </select>
          </div>

          <label className="flex items-center gap-2 cursor-pointer text-neutral-700 select-none">
            <input
              type="checkbox"
              checked={buffettPicksOnly}
              onChange={(e) => setBuffettPicksOnly(e.target.checked)}
              className="rounded border-neutral-300 text-neutral-900 focus:ring-0"
            />
            <span>Tylko wybory Buffetta (BUY / Score &ge; 70)</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer text-neutral-700 select-none">
            <input
              type="checkbox"
              checked={undervaluedOnly}
              onChange={(e) => setUndervaluedOnly(e.target.checked)}
              className="rounded border-neutral-300 text-neutral-900 focus:ring-0"
            />
            <span>Tylko z marginesem (&gt; 0%)</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer text-neutral-700 select-none">
            <input
              type="checkbox"
              checked={hideInPortfolio}
              onChange={(e) => setHideInPortfolio(e.target.checked)}
              className="rounded border-neutral-300 text-neutral-900 focus:ring-0"
            />
            <span>Ukryj już w Paper Trading</span>
          </label>
        </div>

        <div className="text-neutral-500 font-mono text-[11px]">
          Wyświetlono: <strong className="text-neutral-900">{filteredItems.length}</strong> spółek
        </div>
      </div>

      {/* Screener Table */}
      <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-xs">
        {loading && items.length === 0 ? (
          <div className="p-10 text-center text-xs text-neutral-500 font-mono">
            Pobieranie i skanowanie koszyków rynkowych...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50 font-mono text-neutral-500 uppercase">
                  <th className="py-3 px-4 font-semibold">Spółka & Koszyk</th>
                  <th className="py-3 px-3 font-semibold text-center">Paper Trading</th>
                  <th className="py-3 px-3 font-semibold text-center">Rekomendacja</th>
                  <th className="py-3 px-3 font-semibold text-center">Score</th>
                  <th className="py-3 px-3 font-semibold text-right">Kurs</th>
                  <th className="py-3 px-3 font-semibold text-right">DCF</th>
                  <th className="py-3 px-3 font-semibold text-right">Margines</th>
                  <th className="py-3 px-3 font-semibold text-right">ROIC</th>
                  <th className="py-3 px-3 font-semibold text-right">Dług / FCF</th>
                  <th className="py-3 px-3 font-semibold text-center">Reguła 1</th>
                  <th className="py-3 px-4 font-semibold text-center">Akcja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {filteredItems.map((item) => {
                  const isUndervalued = item.margin_of_safety_pct > 0;
                  const rec = REC_STYLES[item.recommendation] || REC_STYLES.HOLD;
                  return (
                    <tr
                      key={item.ticker}
                      className={`hover:bg-neutral-50/70 transition-colors ${
                        item.in_paper_trading ? 'bg-indigo-50/20' : ''
                      }`}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span
                            className="font-bold text-neutral-900 font-mono text-sm cursor-pointer hover:underline"
                            onClick={() => onSelectTicker(item.ticker)}
                          >
                            {item.ticker}
                          </span>
                          {item.dividend_yield_pct >= 2.0 && (
                            <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                              Div {item.dividend_yield_pct}%
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-neutral-500 truncate max-w-[175px]">
                          {item.company_name}
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {(item.baskets || []).map((bId) => {
                            const bInfo = BASKET_LABELS[bId];
                            if (!bInfo) return null;
                            return (
                              <span
                                key={bId}
                                className={`text-[9px] font-mono px-1.5 py-0.2 rounded border ${bInfo.cls}`}
                              >
                                {bInfo.label}
                              </span>
                            );
                          })}
                        </div>
                      </td>

                      <td className="py-3 px-3 text-center">
                        {item.in_paper_trading ? (
                          <div className="inline-flex flex-col items-center">
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold bg-indigo-100 text-indigo-800 border border-indigo-200 px-2 py-0.5 rounded-full">
                              <Briefcase className="w-3 h-3" /> W PORTFELU
                            </span>
                            {item.paper_trading_pnl_pct !== null && (
                              <span
                                className={`text-[10px] font-mono mt-0.5 ${
                                  item.paper_trading_pnl_pct >= 0 ? 'text-emerald-700' : 'text-rose-700'
                                }`}
                              >
                                {item.paper_trading_pnl_pct >= 0 ? '+' : ''}
                                {item.paper_trading_pnl_pct}%
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-[10px] font-mono text-neutral-400">
                            Poza portfelem
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-3 text-center">
                        <span className={`inline-block font-mono font-bold px-2 py-0.5 rounded text-[10px] ${rec.cls}`}>
                          {rec.label}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-center">
                        <span
                          className={`inline-block font-mono font-bold px-2 py-0.5 rounded text-xs ${
                            item.buffett_score >= 80
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : item.buffett_score >= 65
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : 'bg-neutral-100 text-neutral-600'
                          }`}
                        >
                          {item.buffett_score}/100
                        </span>
                      </td>

                      <td className="py-3 px-3 text-right font-mono font-medium text-neutral-900">
                        ${item.current_price}
                      </td>

                      <td className="py-3 px-3 text-right font-mono text-neutral-700">
                        ${item.intrinsic_value}
                      </td>

                      <td className="py-3 px-3 text-right font-mono">
                        <span
                          className={`font-bold ${
                            isUndervalued ? 'text-emerald-700' : 'text-rose-700'
                          }`}
                        >
                          {isUndervalued ? `+${item.margin_of_safety_pct}%` : `${item.margin_of_safety_pct}%`}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-right font-mono">
                        <span className={item.roic_pct >= 15 ? 'text-neutral-900 font-semibold' : 'text-neutral-500'}>
                          {item.roic_pct}%
                        </span>
                      </td>

                      <td className="py-3 px-3 text-right font-mono text-neutral-600">
                        {item.net_debt_to_fcf === 0 ? 'Brak długu' : `${item.net_debt_to_fcf}x`}
                      </td>

                      <td className="py-3 px-3 text-center">
                        {item.rule_number_one_risk === 'LOW' ? (
                          <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded-full">
                            <ShieldCheck className="w-3 h-3 text-emerald-600" /> Bezpieczna
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 font-medium bg-amber-50 px-2 py-0.5 rounded-full">
                            <ShieldAlert className="w-3 h-3 text-amber-600" /> {item.rule_number_one_risk}
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() =>
                              onOpenOrderModal({
                                mode: 'BUY',
                                ticker: item.ticker,
                                company_name: item.company_name,
                                current_price: item.current_price,
                              })
                            }
                            className="px-2 py-1 text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded font-medium transition-colors cursor-pointer"
                          >
                            Kup
                          </button>
                          <button
                            onClick={() => onSelectTicker(item.ticker)}
                            className="px-2.5 py-1 text-xs bg-neutral-900 hover:bg-neutral-800 text-white rounded font-medium transition-colors flex items-center gap-1 cursor-pointer"
                          >
                            <Sparkles className="w-3 h-3" />
                            Analiza
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
