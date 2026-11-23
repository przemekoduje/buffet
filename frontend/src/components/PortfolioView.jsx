import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import {
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  Award,
  RefreshCw,
  Sliders,
  RotateCcw,
  Wallet,
  Plus,
  LogOut,
  History,
  AlertTriangle,
  Cloud,
  LogIn,
} from 'lucide-react';

function fmtSignedPct(val) {
  const num = Number(val || 0);
  return `${num >= 0 ? '+' : ''}${num}%`;
}

function fmtSignedCash(val) {
  const num = Number(val || 0);
  return `${num >= 0 ? '+' : '-'}$${Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function fmtUsd(val) {
  return `$${Number(val || 0).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function PortfolioView({
  summary,
  onSelectTicker,
  onOpenOrderModal,
  onSaveMM,
  onResetAccount,
  onRefresh,
  loading,
  refreshing,
  user,
  onOpenAuth,
  onManualSync,
  lastSyncTime,
}) {
  const [showMM, setShowMM] = useState(false);
  const [mmForm, setMmForm] = useState(null);
  const [mmSaving, setMmSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    if (summary?.mm_config) {
      setMmForm({
        initial_capital: summary.mm_config.initial_capital,
        default_position_pct: summary.mm_config.default_position_pct,
        max_position_pct: summary.mm_config.max_position_pct,
        max_positions: summary.mm_config.max_positions,
        min_cash_reserve_pct: summary.mm_config.min_cash_reserve_pct,
        default_stop_loss_pct: summary.mm_config.default_stop_loss_pct,
        default_take_profit_pct: summary.mm_config.default_take_profit_pct,
        commission_pct: summary.mm_config.commission_pct,
        allow_fractional_shares: summary.mm_config.allow_fractional_shares,
      });
    }
  }, [summary]);

  if (loading || !summary) {
    return (
      <div className="py-20 text-center text-neutral-500 font-mono text-sm">
        Pobieranie realnych kursów rynkowych i stanu konta Paper Trading...
      </div>
    );
  }

  const {
    initial_capital,
    total_portfolio_value,
    market_value,
    cash_balance,
    cash_pct,
    unrealized_pnl_cash,
    realized_pnl_cash,
    total_pnl_cash,
    total_pnl_pct,
    benchmark_sp500_pnl_pct,
    alpha_pct,
    positions_count,
    holdings = [],
    trades = [],
    equity_curve = [],
    rule_1_compliance,
    data_source,
    last_updated,
    mm_config,
  } = summary;

  const notify = (type, text) => {
    setFeedback({ type, text });
    setTimeout(() => setFeedback(null), 5000);
  };

  const handleSaveMMSubmit = async (e) => {
    e.preventDefault();
    setMmSaving(true);
    try {
      await onSaveMM({
        initial_capital: Number(mmForm.initial_capital),
        default_position_pct: Number(mmForm.default_position_pct),
        max_position_pct: Number(mmForm.max_position_pct),
        max_positions: Number(mmForm.max_positions),
        min_cash_reserve_pct: Number(mmForm.min_cash_reserve_pct),
        default_stop_loss_pct: Number(mmForm.default_stop_loss_pct),
        default_take_profit_pct: Number(mmForm.default_take_profit_pct),
        commission_pct: Number(mmForm.commission_pct),
        allow_fractional_shares: Boolean(mmForm.allow_fractional_shares),
      });
      notify('success', 'Zapisano ustawienia Money Management!');
    } catch (err) {
      notify('error', err.message);
    } finally {
      setMmSaving(false);
    }
  };

  const handleReset = async () => {
    const cap = Number(mmForm?.initial_capital || initial_capital || 100000);
    if (
      !window.confirm(
        `Czy na pewno wyzerować konto Paper Trading do czystej gotówki ${fmtUsd(cap)} (usunie otwarte pozycje i historię transakcji)?`
      )
    ) {
      return;
    }
    try {
      await onResetAccount(cap);
      notify('success', `Konto zresetowane do ${fmtUsd(cap)} (100% gotówka).`);
    } catch (err) {
      notify('error', err.message);
    }
  };

  const handleSell = (h) => {
    onOpenOrderModal({
      mode: 'SELL',
      ticker: h.ticker,
      company_name: h.company_name,
      current_price: h.current_price,
      holding: h,
    });
  };

  const handleQuickAdd = (h) => {
    onOpenOrderModal({
      mode: 'BUY',
      ticker: h.ticker,
      company_name: h.company_name,
      current_price: h.current_price,
      holding: h,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-white border border-neutral-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-neutral-500 uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            Konto Paper Trading (Wirtualny Kapitał) &bull; {(data_source || 'yfinance').toUpperCase()}
          </div>
          <h2 className="text-xl font-serif font-bold text-neutral-900">
            Portfel Inwestycyjny & Kontrola Money Management
          </h2>
          <p className="text-xs text-neutral-600 max-w-2xl mt-1">
            Kapitał początkowy: <strong>{fmtUsd(initial_capital)}</strong> &bull; Pozycja domyślna:{' '}
            <strong>{mm_config?.default_position_pct}%</strong> &bull; Max w 1 spółce:{' '}
            <strong>{mm_config?.max_position_pct}%</strong> &bull; Rezerwa gotówki:{' '}
            <strong>{mm_config?.min_cash_reserve_pct}%</strong>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {user ? (
            <button
              onClick={onManualSync}
              title={`Zapisano w Firebase (${lastSyncTime || 'chwilę temu'})`}
              className="px-2.5 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-mono font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Cloud className="w-3.5 h-3.5 text-emerald-600" />
              <span>Zapisano w chmurze</span>
            </button>
          ) : (
            <button
              onClick={onOpenAuth}
              title="Zaloguj się, aby zapisywać portfel w Google Firebase"
              className="px-2.5 py-2 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 border border-neutral-300 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <LogIn className="w-3.5 h-3.5 text-neutral-600" />
              <span>Zaloguj (Zapis Firebase)</span>
            </button>
          )}

          <button
            onClick={() => setShowMM((v) => !v)}
            className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer border ${
              showMM
                ? 'bg-neutral-900 text-white border-neutral-900'
                : 'bg-white hover:bg-neutral-50 text-neutral-800 border-neutral-300'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Ustawienia MM</span>
          </button>

          <button
            onClick={handleReset}
            className="px-3 py-2 bg-white hover:bg-rose-50 text-rose-700 border border-rose-200 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Resetuj konto</span>
          </button>

          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="px-3.5 py-2 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? 'Odświeżanie...' : 'Odśwież kursy'}</span>
          </button>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-3.5 rounded-lg text-xs border ${
            feedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {feedback.text}
        </div>
      )}

      {/* Collapsible Money Management Settings Panel */}
      {showMM && mmForm && (
        <form
          onSubmit={handleSaveMMSubmit}
          className="bg-white border border-neutral-300 rounded-xl p-5 shadow-xs space-y-4"
        >
          <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-neutral-800" />
              <h3 className="text-sm font-serif font-bold text-neutral-900">
                Reguły Money Management (Wirtualny Kapitał)
              </h3>
            </div>
            <span className="text-[11px] font-mono text-neutral-500">
              Dostępne do zakupu ponad rezerwę: <strong className="text-emerald-700">{fmtUsd(mm_config?.investable_cash_usd)}</strong>
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="block font-mono text-neutral-600 mb-1">Kapitał startowy ($)</label>
              <input
                type="number"
                min="1000"
                step="1000"
                value={mmForm.initial_capital}
                onChange={(e) => setMmForm({ ...mmForm, initial_capital: e.target.value })}
                className="w-full border border-neutral-300 rounded px-2.5 py-1.5 font-mono"
              />
            </div>

            <div>
              <label className="block font-mono text-neutral-600 mb-1">Domyślna pozycja (%)</label>
              <input
                type="number"
                min="1"
                max="100"
                step="1"
                value={mmForm.default_position_pct}
                onChange={(e) => setMmForm({ ...mmForm, default_position_pct: e.target.value })}
                className="w-full border border-neutral-300 rounded px-2.5 py-1.5 font-mono"
              />
            </div>

            <div>
              <label className="block font-mono text-neutral-600 mb-1">Max w 1 spółce (%)</label>
              <input
                type="number"
                min="1"
                max="100"
                step="1"
                value={mmForm.max_position_pct}
                onChange={(e) => setMmForm({ ...mmForm, max_position_pct: e.target.value })}
                className="w-full border border-neutral-300 rounded px-2.5 py-1.5 font-mono"
              />
            </div>

            <div>
              <label className="block font-mono text-neutral-600 mb-1">Max liczba pozycji</label>
              <input
                type="number"
                min="1"
                max="100"
                value={mmForm.max_positions}
                onChange={(e) => setMmForm({ ...mmForm, max_positions: e.target.value })}
                className="w-full border border-neutral-300 rounded px-2.5 py-1.5 font-mono"
              />
            </div>

            <div>
              <label className="block font-mono text-neutral-600 mb-1">Min. rezerwa gotówki (%)</label>
              <input
                type="number"
                min="0"
                max="90"
                step="1"
                value={mmForm.min_cash_reserve_pct}
                onChange={(e) => setMmForm({ ...mmForm, min_cash_reserve_pct: e.target.value })}
                className="w-full border border-neutral-300 rounded px-2.5 py-1.5 font-mono"
              />
            </div>

            <div>
              <label className="block font-mono text-neutral-600 mb-1">Domyślny Stop-Loss (%)</label>
              <input
                type="number"
                min="0"
                max="80"
                step="1"
                value={mmForm.default_stop_loss_pct}
                onChange={(e) => setMmForm({ ...mmForm, default_stop_loss_pct: e.target.value })}
                className="w-full border border-neutral-300 rounded px-2.5 py-1.5 font-mono"
              />
            </div>

            <div>
              <label className="block font-mono text-neutral-600 mb-1">Domyślny Take-Profit (%)</label>
              <input
                type="number"
                min="0"
                max="500"
                step="1"
                value={mmForm.default_take_profit_pct}
                onChange={(e) => setMmForm({ ...mmForm, default_take_profit_pct: e.target.value })}
                className="w-full border border-neutral-300 rounded px-2.5 py-1.5 font-mono"
              />
            </div>

            <div>
              <label className="block font-mono text-neutral-600 mb-1">Prowizja brokera (%)</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.05"
                value={mmForm.commission_pct}
                onChange={(e) => setMmForm({ ...mmForm, commission_pct: e.target.value })}
                className="w-full border border-neutral-300 rounded px-2.5 py-1.5 font-mono"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-neutral-100">
            <label className="flex items-center gap-2 text-xs text-neutral-700 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={mmForm.allow_fractional_shares}
                onChange={(e) => setMmForm({ ...mmForm, allow_fractional_shares: e.target.checked })}
                className="rounded border-neutral-300"
              />
              <span>Zezwalaj na akcje ułamkowe (dokładne dopasowanie kwoty MM)</span>
            </label>

            <button
              type="submit"
              disabled={mmSaving}
              className="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-xs font-medium cursor-pointer disabled:opacity-50"
            >
              {mmSaving ? 'Zapisywanie...' : 'Zapisz zasady MM'}
            </button>
          </div>
        </form>
      )}

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-neutral-200 rounded-xl p-4 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase flex items-center justify-between">
            <span>Kapitał Całkowity (Equity)</span>
            <Wallet className="w-3.5 h-3.5 text-neutral-400" />
          </div>
          <div className="text-2xl font-serif font-bold text-neutral-900 mt-1">
            {fmtUsd(total_portfolio_value)}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1 font-mono">
            Akcje: {fmtUsd(market_value)} &bull; Gotówka: {fmtUsd(cash_balance)} ({cash_pct}%)
          </div>
        </div>

        <div className="bg-white border border-neutral-200 rounded-xl p-4 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase">Wynik Całkowity (P&L)</div>
          <div
            className={`text-2xl font-serif font-bold mt-1 flex items-center gap-1.5 ${
              total_pnl_pct >= 0 ? 'text-emerald-700' : 'text-rose-700'
            }`}
          >
            {fmtSignedPct(total_pnl_pct)}
            <span className="text-xs font-sans font-normal text-neutral-500">
              ({fmtSignedCash(total_pnl_cash)})
            </span>
          </div>
          <div className="text-[11px] text-neutral-500 mt-1 font-mono">
            Otwarty: {fmtSignedCash(unrealized_pnl_cash)} &bull; Zreal.: {fmtSignedCash(realized_pnl_cash)}
          </div>
        </div>

        <div className="bg-white border border-neutral-200 rounded-xl p-4 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase">Gotówka & Limit MM</div>
          <div className="text-2xl font-serif font-bold text-neutral-900 mt-1">
            {fmtUsd(mm_config?.investable_cash_usd)}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1 font-mono">
            Rezerwa: {fmtUsd(mm_config?.min_reserve_usd)} &bull; Pozycje: {positions_count}/{mm_config?.max_positions}
          </div>
        </div>

        <div className="bg-white border border-neutral-200 rounded-xl p-4 shadow-xs bg-amber-50/40">
          <div className="text-xs font-mono text-amber-900/80 uppercase font-semibold flex items-center justify-between">
            <span>Alfa vs S&P 500</span>
            <Award className="w-3.5 h-3.5 text-amber-600" />
          </div>
          <div className={`text-2xl font-serif font-bold mt-1 ${alpha_pct >= 0 ? 'text-neutral-900' : 'text-rose-700'}`}>
            {fmtSignedPct(alpha_pct)}
          </div>
          <div className="text-[11px] text-neutral-600 mt-1 font-mono">
            S&P 500: {fmtSignedPct(benchmark_sp500_pnl_pct)} &bull; {last_updated}
          </div>
        </div>
      </div>

      {/* Equity Curve */}
      {equity_curve.length > 0 && (
        <div className="bg-white border border-neutral-200 rounded-xl p-5 shadow-xs">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 mb-4">
            <div>
              <h3 className="text-sm font-serif font-bold text-neutral-900">
                Krzywa Zwrotu: Portfel Buffetta vs S&P 500
              </h3>
              <p className="text-xs text-neutral-500 flex items-center gap-1.5 mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>{rule_1_compliance}</span>
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="flex items-center gap-1.5 text-neutral-900">
                <span className="w-3 h-0.5 bg-neutral-950 inline-block"></span> Portfel Buffetta
              </span>
              <span className="flex items-center gap-1.5 text-neutral-500">
                <span className="w-3 h-0.5 bg-neutral-400 inline-block border-dashed"></span> S&P 500 (^GSPC)
              </span>
            </div>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={equity_curve} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" stroke="#999" fontSize={11} tickLine={false} />
                <YAxis stroke="#999" fontSize={11} tickFormatter={(val) => `${val >= 0 ? '+' : ''}${val}%`} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e5e5e5', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(val, name) => [
                    `${Number(val) >= 0 ? '+' : ''}${val}%`,
                    name === 'portfolio_return' ? 'Portfel Buffetta' : 'S&P 500',
                  ]}
                />
                <Line type="monotone" dataKey="portfolio_return" stroke="#171717" strokeWidth={2.5} dot={{ r: 3, fill: '#171717' }} />
                <Line type="monotone" dataKey="benchmark_return" stroke="#9ca3af" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Open Positions Table */}
      <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-xs">
        <div className="px-5 py-4 border-b border-neutral-200 flex justify-between items-center bg-neutral-50/50">
          <div>
            <h3 className="text-sm font-serif font-bold text-neutral-900">Otwarte Pozycje (Paper Trading)</h3>
            <p className="text-xs text-neutral-500">
              Dokładna liczba akcji, waga w portfelu, poziomy SL/TP oraz realny P&L w USD i %
            </p>
          </div>
          <span className="text-xs font-mono text-neutral-500 bg-white border border-neutral-200 px-2 py-1 rounded">
            {holdings.length} / {mm_config?.max_positions} pozycji
          </span>
        </div>

        {holdings.length === 0 ? (
          <div className="p-10 text-center text-xs text-neutral-500 font-mono">
            Brak otwartych pozycji — 100% kapitału w gotówce ({fmtUsd(cash_balance)}). Przejdź do zakładki Screener lub Analiza, aby otworzyć pierwszą pozycję wg MM.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50/80 font-mono text-neutral-500 uppercase">
                  <th className="py-3 px-4 font-semibold">Spółka</th>
                  <th className="py-3 px-3 font-semibold text-right">Akcje</th>
                  <th className="py-3 px-3 font-semibold text-right">Śr. Zakup</th>
                  <th className="py-3 px-3 font-semibold text-right">Kurs Live</th>
                  <th className="py-3 px-3 font-semibold text-right">Wartość / Waga</th>
                  <th className="py-3 px-3 font-semibold text-right">SL / TP</th>
                  <th className="py-3 px-3 font-semibold text-right">P&L ($)</th>
                  <th className="py-3 px-3 font-semibold text-right">P&L (%)</th>
                  <th className="py-3 px-4 font-semibold text-center">Zlecenia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {holdings.map((h) => (
                  <tr key={h.id} className="hover:bg-neutral-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="font-bold text-neutral-900 font-mono text-sm cursor-pointer hover:underline"
                          onClick={() => onSelectTicker(h.ticker)}
                        >
                          {h.ticker}
                        </span>
                        {h.sl_triggered && (
                          <span className="inline-flex items-center gap-0.5 text-[10px] font-mono bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded">
                            <AlertTriangle className="w-2.5 h-2.5" /> SL!
                          </span>
                        )}
                        {h.tp_triggered && (
                          <span className="inline-flex items-center gap-0.5 text-[10px] font-mono bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded">
                            TP!
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-neutral-500 truncate max-w-[160px]">{h.company_name}</div>
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-neutral-800 font-medium">
                      {Number(h.shares).toFixed(h.shares % 1 === 0 ? 0 : 3)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-neutral-600">
                      ${h.entry_price}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-medium text-neutral-900">
                      ${h.current_price}
                    </td>
                    <td className="py-3 px-3 text-right font-mono">
                      <div className="font-semibold text-neutral-900">{fmtUsd(h.market_value)}</div>
                      <div className="text-[10px] text-neutral-400">{h.weight_pct}% portfela</div>
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-[11px]">
                      <div className={h.sl_triggered ? 'text-rose-700 font-bold' : 'text-neutral-500'}>
                        SL: {h.stop_loss_price ? `$${h.stop_loss_price}` : '—'}
                      </div>
                      <div className={h.tp_triggered ? 'text-emerald-700 font-bold' : 'text-neutral-400'}>
                        TP: {h.take_profit_price ? `$${h.take_profit_price}` : '—'}
                      </div>
                    </td>
                    <td className={`py-3 px-3 text-right font-mono font-semibold ${h.pnl_cash >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {fmtSignedCash(h.pnl_cash)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono">
                      <span className={`inline-flex items-center gap-0.5 font-bold ${h.pnl_pct >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                        {h.pnl_pct >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                        {fmtSignedPct(h.pnl_pct)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => handleQuickAdd(h)}
                          title="Dokup akcje (otwiera modal MM)"
                          className="px-2 py-1 text-[11px] bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded font-medium inline-flex items-center gap-0.5 cursor-pointer"
                        >
                          <Plus className="w-3 h-3" /> Kup
                        </button>
                        <button
                          onClick={() => handleSell(h)}
                          title="Sprzedaj / zamknij pozycję (otwiera modal MM)"
                          className="px-2 py-1 text-[11px] bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded font-medium inline-flex items-center gap-0.5 cursor-pointer"
                        >
                          <LogOut className="w-3 h-3" /> Sprzedaj
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Trade Ledger */}
      <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-xs">
        <div className="px-5 py-3.5 border-b border-neutral-200 flex items-center justify-between bg-neutral-50/50">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-neutral-600" />
            <h3 className="text-sm font-serif font-bold text-neutral-900">
              Dziennik Transakcji (Historia Zleceń BUY / SELL)
            </h3>
          </div>
          <span className="text-[11px] font-mono text-neutral-500">{trades.length} ostatnich</span>
        </div>

        {trades.length === 0 ? (
          <div className="p-6 text-center text-xs text-neutral-400 font-mono">
            Brak zapisanych transakcji.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50/60 font-mono text-neutral-500 uppercase text-[10px]">
                  <th className="py-2.5 px-4">Data</th>
                  <th className="py-2.5 px-3">Strona</th>
                  <th className="py-2.5 px-3">Spółka</th>
                  <th className="py-2.5 px-3 text-right">Akcje</th>
                  <th className="py-2.5 px-3 text-right">Cena</th>
                  <th className="py-2.5 px-3 text-right">Wartość</th>
                  <th className="py-2.5 px-3 text-right">Zreal. P&L</th>
                  <th className="py-2.5 px-4">Notatka</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 font-mono text-[11px]">
                {trades.map((t) => (
                  <tr key={t.id} className="hover:bg-neutral-50/70">
                    <td className="py-2.5 px-4 text-neutral-500">{t.executed_at}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          t.side === 'BUY'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {t.side}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-bold text-neutral-900">{t.ticker}</td>
                    <td className="py-2.5 px-3 text-right">{Number(t.shares).toFixed(t.shares % 1 === 0 ? 0 : 3)}</td>
                    <td className="py-2.5 px-3 text-right">${t.price}</td>
                    <td className="py-2.5 px-3 text-right">{fmtUsd(t.gross_value)}</td>
                    <td className="py-2.5 px-3 text-right">
                      {t.realized_pnl !== null && t.realized_pnl !== undefined ? (
                        <span className={t.realized_pnl >= 0 ? 'text-emerald-700 font-bold' : 'text-rose-700 font-bold'}>
                          {fmtSignedCash(t.realized_pnl)} ({fmtSignedPct(t.realized_pnl_pct)})
                        </span>
                      ) : (
                        <span className="text-neutral-400">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 font-sans text-neutral-500">{t.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
