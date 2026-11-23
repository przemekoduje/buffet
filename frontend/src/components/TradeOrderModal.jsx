import React, { useState, useEffect } from 'react';
import {
  X,
  Sliders,
  ShieldCheck,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Wallet,
  Check,
} from 'lucide-react';

function fmtUsd(val) {
  return `$${Number(val || 0).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function fmtSignedCash(val) {
  const num = Number(val || 0);
  return `${num >= 0 ? '+' : '-'}$${Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function TradeOrderModal({
  order, // { mode: 'BUY' | 'SELL', ticker, company_name, current_price, holding? }
  portfolioSummary,
  onClose,
  onExecuteBuy,
  onExecuteSell,
  onSaveMM,
}) {
  const isBuy = order?.mode === 'BUY';
  const mm = portfolioSummary?.mm_config || {};
  const totalEquity = Number(portfolioSummary?.total_portfolio_value || mm.initial_capital || 100000);
  const cashBalance = Number(portfolioSummary?.cash_balance || 0);
  const holdings = portfolioSummary?.holdings || [];
  const existingHolding =
    order?.holding || holdings.find((h) => h.ticker === order?.ticker) || null;

  const price = Number(order?.current_price || existingHolding?.current_price || 0);

  // Order inputs
  const [amountUsd, setAmountUsd] = useState('');
  const [sellShares, setSellShares] = useState('');
  const [slPct, setSlPct] = useState('');
  const [tpPct, setTpPct] = useState('');
  const [note, setNote] = useState('');

  // Inline MM editor inside modal
  const [showMMEdit, setShowMMEdit] = useState(false);
  const [mmDraft, setMmDraft] = useState(null);
  const [mmSaving, setMmSaving] = useState(false);
  const [mmSavedMsg, setMmSavedMsg] = useState(null);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!order) return;
    setError(null);
    setMmSavedMsg(null);
    setShowMMEdit(false);

    if (order.mode === 'BUY') {
      const suggested = mm.suggested_order_usd || Math.round(totalEquity * ((mm.default_position_pct || 10) / 100));
      setAmountUsd(String(Math.max(Math.round(suggested), 0)));
      setSlPct(String(mm.default_stop_loss_pct ?? 15));
      setTpPct(String(mm.default_take_profit_pct ?? 35));
      setNote(existingHolding ? 'Dokupienie pozycji wg MM' : 'Otwarcie pozycji wg MM');
    } else if (existingHolding) {
      setSellShares(String(existingHolding.shares));
      setNote('Zamknięcie pozycji');
    }

    setMmDraft({
      default_position_pct: mm.default_position_pct ?? 10,
      max_position_pct: mm.max_position_pct ?? 20,
      max_positions: mm.max_positions ?? 15,
      min_cash_reserve_pct: mm.min_cash_reserve_pct ?? 10,
      default_stop_loss_pct: mm.default_stop_loss_pct ?? 15,
      default_take_profit_pct: mm.default_take_profit_pct ?? 35,
      commission_pct: mm.commission_pct ?? 0,
      allow_fractional_shares: mm.allow_fractional_shares ?? true,
    });
  }, [order]);

  if (!order) return null;

  const commissionPct = Number(mm.commission_pct || 0);
  const minReserveUsd = totalEquity * ((mm.min_cash_reserve_pct || 0) / 100);
  const investableCash = Math.max(cashBalance - minReserveUsd, 0);

  // Live BUY preview calculations
  const parsedAmount = Math.max(Number(amountUsd) || 0, 0);
  const estBuyShares =
    price > 0
      ? mm.allow_fractional_shares === false
        ? Math.floor(parsedAmount / price)
        : Number((parsedAmount / price).toFixed(4))
      : 0;
  const actualBuyGross = estBuyShares * price;
  const buyCommission = actualBuyGross * (commissionPct / 100);
  const buyTotalCost = actualBuyGross + buyCommission;
  const existingVal = existingHolding ? existingHolding.current_price * existingHolding.shares : 0;
  const newPositionWeightPct = totalEquity > 0 ? ((existingVal + actualBuyGross) / totalEquity) * 100 : 0;
  const cashAfterBuy = cashBalance - buyTotalCost;
  const cashAfterBuyPct = totalEquity > 0 ? (cashAfterBuy / totalEquity) * 100 : 0;

  const slPricePreview =
    price > 0 && Number(slPct) > 0 ? (price * (1 - Number(slPct) / 100)).toFixed(2) : null;
  const tpPricePreview =
    price > 0 && Number(tpPct) > 0 ? (price * (1 + Number(tpPct) / 100)).toFixed(2) : null;

  const mmWarnings = [];
  if (isBuy) {
    if (!existingHolding && holdings.length >= (mm.max_positions || 15)) {
      mmWarnings.push(`Osiągnięto limit otwartych pozycji (${holdings.length}/${mm.max_positions}).`);
    }
    if (buyTotalCost > cashBalance + 0.01) {
      mmWarnings.push(`Brak wystarczającej gotówki (potrzeba ${fmtUsd(buyTotalCost)}, saldo ${fmtUsd(cashBalance)}).`);
    } else if (cashAfterBuy + 0.01 < minReserveUsd && (mm.min_cash_reserve_pct || 0) > 0) {
      mmWarnings.push(
        `Naruszenie rezerwy gotówki MM (${mm.min_cash_reserve_pct}% = ${fmtUsd(minReserveUsd)}). Max dostępna kwota: ${fmtUsd(investableCash)}.`
      );
    }
    if (newPositionWeightPct > (mm.max_position_pct || 20) + 0.25) {
      mmWarnings.push(
        `Przekroczony limit w 1 spółce (${newPositionWeightPct.toFixed(1)}% > ${mm.max_position_pct}%).`
      );
    }
  }

  // Live SELL preview calculations
  const maxSellShares = Number(existingHolding?.shares || 0);
  const parsedSellShares = Math.min(Math.max(Number(sellShares) || 0, 0), maxSellShares);
  const sellGross = parsedSellShares * price;
  const sellCommission = sellGross * (commissionPct / 100);
  const sellNet = sellGross - sellCommission;
  const sellCostBasis = parsedSellShares * Number(existingHolding?.entry_price || 0);
  const estRealizedPnl = sellNet - sellCostBasis;
  const estRealizedPnlPct = sellCostBasis > 0 ? (estRealizedPnl / sellCostBasis) * 100 : 0;
  const cashAfterSell = cashBalance + sellNet;
  const cashAfterSellPct = totalEquity > 0 ? (cashAfterSell / totalEquity) * 100 : 100;
  const isFullClose = parsedSellShares >= maxSellShares - 1e-6;

  const handleSaveMMInline = async () => {
    if (!mmDraft) return;
    setMmSaving(true);
    setError(null);
    try {
      await onSaveMM({
        default_position_pct: Number(mmDraft.default_position_pct),
        max_position_pct: Number(mmDraft.max_position_pct),
        max_positions: Number(mmDraft.max_positions),
        min_cash_reserve_pct: Number(mmDraft.min_cash_reserve_pct),
        default_stop_loss_pct: Number(mmDraft.default_stop_loss_pct),
        default_take_profit_pct: Number(mmDraft.default_take_profit_pct),
        commission_pct: Number(mmDraft.commission_pct),
        allow_fractional_shares: Boolean(mmDraft.allow_fractional_shares),
      });
      if (isBuy) {
        setSlPct(String(mmDraft.default_stop_loss_pct));
        setTpPct(String(mmDraft.default_take_profit_pct));
      }
      setMmSavedMsg('Zaktualizowano reguły MM konta.');
      setTimeout(() => setMmSavedMsg(null), 3000);
    } catch (err) {
      setError(err.message || 'Błąd zapisu ustawień MM');
    } finally {
      setMmSaving(false);
    }
  };

  const handleConfirm = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (isBuy) {
        await onExecuteBuy({
          ticker: order.ticker,
          amount_usd: parsedAmount,
          stop_loss_pct: slPct !== '' ? Number(slPct) : null,
          take_profit_pct: tpPct !== '' ? Number(tpPct) : null,
          note: note.trim() || (existingHolding ? 'Dokupienie pozycji' : 'Zakup wg MM'),
        });
      } else {
        if (!existingHolding) throw new Error('Brak otwartej pozycji do sprzedaży.');
        await onExecuteSell(existingHolding.id, isFullClose ? null : parsedSellShares, note.trim());
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Nie udało się zrealizować zlecenia.');
    } finally {
      setSubmitting(false);
    }
  };

  const setBuyPctPreset = (pct) => {
    const maxForTicker = Math.max(totalEquity * ((mm.max_position_pct || 20) / 100) - existingVal, 0);
    const desired = totalEquity * (pct / 100);
    const safe = Math.min(desired, investableCash, maxForTicker);
    setAmountUsd(String(Math.max(Math.floor(safe), 0)));
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[1px] flex items-center justify-center p-4 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white border border-neutral-200 rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden my-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          className={`px-5 py-4 border-b flex items-center justify-between ${
            isBuy ? 'bg-emerald-50/60 border-emerald-100' : 'bg-rose-50/60 border-rose-100'
          }`}
        >
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                  isBuy ? 'bg-emerald-700 text-white' : 'bg-rose-700 text-white'
                }`}
              >
                {isBuy ? (existingHolding ? 'ZLECENIE DOKUPIENIA (BUY)' : 'ZLECENIE KUPNA (BUY)') : 'ZAMKNIĘCIE / SPRZEDAŻ (SELL)'}
              </span>
              <span className="font-mono font-bold text-base text-neutral-900">{order.ticker}</span>
              <span className="text-xs font-mono text-neutral-600">@ {fmtUsd(price)}</span>
            </div>
            <div className="text-xs text-neutral-500 mt-0.5">{order.company_name || order.ticker}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-neutral-500 hover:text-neutral-900 hover:bg-white/80 rounded-lg cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleConfirm} className="p-5 space-y-4">
          {/* Account & MM Summary Strip */}
          <div className="grid grid-cols-3 gap-2.5 bg-neutral-50 border border-neutral-200 rounded-xl p-3 text-[11px] font-mono">
            <div>
              <div className="text-neutral-400">Kapitał (Equity)</div>
              <div className="font-bold text-neutral-900">{fmtUsd(totalEquity)}</div>
            </div>
            <div>
              <div className="text-neutral-400">Wolna gotówka</div>
              <div className="font-bold text-neutral-900">{fmtUsd(cashBalance)}</div>
            </div>
            <div>
              <div className="text-neutral-400">Ponad rezerwę ({mm.min_cash_reserve_pct}%)</div>
              <div className="font-bold text-emerald-700">{fmtUsd(investableCash)}</div>
            </div>
          </div>

          {/* BUY FORM */}
          {isBuy ? (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-mono font-semibold text-neutral-700">
                    Kwota zlecenia (USD)
                  </label>
                  <div className="flex items-center gap-1">
                    {[5, mm.default_position_pct || 10, 15].map((pct, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setBuyPctPreset(pct)}
                        className="px-2 py-0.5 text-[10px] font-mono bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded cursor-pointer"
                      >
                        {pct}%
                      </button>
                    ))}
                    <button
                      type="button"
                      onClick={() => setBuyPctPreset(mm.max_position_pct || 20)}
                      className="px-2 py-0.5 text-[10px] font-mono bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded cursor-pointer"
                    >
                      Max MM
                    </button>
                  </div>
                </div>
                <input
                  type="number"
                  min="1"
                  step="10"
                  required
                  value={amountUsd}
                  onChange={(e) => setAmountUsd(e.target.value)}
                  className="w-full border border-neutral-300 rounded-lg px-3 py-2 font-mono text-sm font-bold text-neutral-900 focus:outline-none focus:ring-1 focus:ring-neutral-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block font-mono text-neutral-600 mb-1">
                    Stop-Loss (%) {slPricePreview && <span className="text-rose-600">→ ${slPricePreview}</span>}
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="80"
                    step="1"
                    value={slPct}
                    onChange={(e) => setSlPct(e.target.value)}
                    className="w-full border border-neutral-300 rounded-lg px-3 py-1.5 font-mono"
                  />
                </div>
                <div>
                  <label className="block font-mono text-neutral-600 mb-1">
                    Take-Profit (%) {tpPricePreview && <span className="text-emerald-700">→ ${tpPricePreview}</span>}
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="500"
                    step="1"
                    value={tpPct}
                    onChange={(e) => setTpPct(e.target.value)}
                    className="w-full border border-neutral-300 rounded-lg px-3 py-1.5 font-mono"
                  />
                </div>
              </div>

              {/* Live BUY Impact Summary */}
              <div className="bg-neutral-50 border border-neutral-200 rounded-xl p-3.5 space-y-1.5 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-neutral-500">Szacowana liczba akcji:</span>
                  <strong className="text-neutral-900">{estBuyShares} szt.</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Wartość zlecenia + prowizja ({commissionPct}%):</span>
                  <strong className="text-neutral-900">{fmtUsd(buyTotalCost)}</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Waga {order.ticker} po zakupie (limit {mm.max_position_pct}%):</span>
                  <strong
                    className={
                      newPositionWeightPct > (mm.max_position_pct || 20) + 0.25
                        ? 'text-rose-700'
                        : 'text-emerald-700'
                    }
                  >
                    {newPositionWeightPct.toFixed(1)}%
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Gotówka po transakcji (rezerwa {mm.min_cash_reserve_pct}%):</span>
                  <strong className={cashAfterBuy < minReserveUsd ? 'text-rose-700' : 'text-neutral-900'}>
                    {fmtUsd(cashAfterBuy)} ({cashAfterBuyPct.toFixed(1)}%)
                  </strong>
                </div>
              </div>
            </div>
          ) : (
            /* SELL FORM */
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-mono font-semibold text-neutral-700">
                    Liczba akcji do sprzedaży (posiadasz: {maxSellShares})
                  </label>
                  <div className="flex items-center gap-1">
                    {[25, 50, 75, 100].map((pct) => (
                      <button
                        key={pct}
                        type="button"
                        onClick={() => {
                          const qty =
                            pct === 100
                              ? maxSellShares
                              : mm.allow_fractional_shares === false
                              ? Math.max(Math.floor((maxSellShares * pct) / 100), 1)
                              : Number(((maxSellShares * pct) / 100).toFixed(4));
                          setSellShares(String(qty));
                          setNote(pct === 100 ? 'Zamknięcie całej pozycji' : `Częściowa sprzedaż (${pct}%)`);
                        }}
                        className={`px-2 py-0.5 text-[10px] font-mono rounded cursor-pointer ${
                          pct === 100
                            ? 'bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-200'
                            : 'bg-neutral-100 hover:bg-neutral-200 text-neutral-700'
                        }`}
                      >
                        {pct === 100 ? '100% (Zamknij)' : `${pct}%`}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  type="number"
                  min="0.0001"
                  max={maxSellShares}
                  step="any"
                  required
                  value={sellShares}
                  onChange={(e) => setSellShares(e.target.value)}
                  className="w-full border border-neutral-300 rounded-lg px-3 py-2 font-mono text-sm font-bold text-neutral-900 focus:outline-none focus:ring-1 focus:ring-neutral-900"
                />
              </div>

              {/* Live SELL Impact Summary */}
              <div className="bg-neutral-50 border border-neutral-200 rounded-xl p-3.5 space-y-1.5 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-neutral-500">Średnia cena zakupu → Kurs sprzedaży:</span>
                  <strong className="text-neutral-900">
                    {fmtUsd(existingHolding?.entry_price)} → {fmtUsd(price)}
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Wpływ gotówki netto (po prowizji {commissionPct}%):</span>
                  <strong className="text-neutral-900">{fmtUsd(sellNet)}</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Zrealizowany wynik (P&L):</span>
                  <strong
                    className={`inline-flex items-center gap-0.5 ${
                      estRealizedPnl >= 0 ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    {estRealizedPnl >= 0 ? (
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    ) : (
                      <ArrowDownRight className="w-3.5 h-3.5" />
                    )}
                    {fmtSignedCash(estRealizedPnl)} ({estRealizedPnlPct >= 0 ? '+' : ''}
                    {estRealizedPnlPct.toFixed(2)}%)
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Saldo gotówki po sprzedaży:</span>
                  <strong className="text-emerald-700">
                    {fmtUsd(cashAfterSell)} ({cashAfterSellPct.toFixed(1)}% portfela)
                  </strong>
                </div>
              </div>
            </div>
          )}

          {/* Note input */}
          <div>
            <label className="block text-xs font-mono text-neutral-600 mb-1">Notatka do dziennika transakcji</label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Powód decyzji (np. duży margines bezpieczeństwa, realizacja TP, SL)..."
              className="w-full border border-neutral-300 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900"
            />
          </div>

          {/* Expandable MM Settings Adjuster right inside the modal */}
          <div className="border border-neutral-200 rounded-xl overflow-hidden">
            <button
              type="button"
              onClick={() => setShowMMEdit((v) => !v)}
              className="w-full px-3.5 py-2.5 bg-neutral-50 hover:bg-neutral-100 flex items-center justify-between text-xs font-mono text-neutral-700 cursor-pointer"
            >
              <span className="inline-flex items-center gap-1.5 font-semibold">
                <Sliders className="w-3.5 h-3.5" />
                Dostosuj reguły Money Management przed zatwierdzeniem
              </span>
              <span className="text-[10px] text-neutral-500">{showMMEdit ? 'Zwiń' : 'Rozwiń'}</span>
            </button>

            {showMMEdit && mmDraft && (
              <div className="p-3.5 space-y-3 bg-white border-t border-neutral-200 text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  <div>
                    <label className="block font-mono text-[10px] text-neutral-500 mb-0.5">Domyślna poz. (%)</label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={mmDraft.default_position_pct}
                      onChange={(e) => setMmDraft({ ...mmDraft, default_position_pct: e.target.value })}
                      className="w-full border border-neutral-300 rounded px-2 py-1 font-mono text-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[10px] text-neutral-500 mb-0.5">Max w 1 spółce (%)</label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={mmDraft.max_position_pct}
                      onChange={(e) => setMmDraft({ ...mmDraft, max_position_pct: e.target.value })}
                      className="w-full border border-neutral-300 rounded px-2 py-1 font-mono text-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[10px] text-neutral-500 mb-0.5">Min. rezerwa (%)</label>
                    <input
                      type="number"
                      min="0"
                      max="90"
                      value={mmDraft.min_cash_reserve_pct}
                      onChange={(e) => setMmDraft({ ...mmDraft, min_cash_reserve_pct: e.target.value })}
                      className="w-full border border-neutral-300 rounded px-2 py-1 font-mono text-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[10px] text-neutral-500 mb-0.5">Max pozycji</label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={mmDraft.max_positions}
                      onChange={(e) => setMmDraft({ ...mmDraft, max_positions: e.target.value })}
                      className="w-full border border-neutral-300 rounded px-2 py-1 font-mono text-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[10px] text-neutral-500 mb-0.5">Domyślny SL (%)</label>
                    <input
                      type="number"
                      min="0"
                      max="80"
                      value={mmDraft.default_stop_loss_pct}
                      onChange={(e) => setMmDraft({ ...mmDraft, default_stop_loss_pct: e.target.value })}
                      className="w-full border border-neutral-300 rounded px-2 py-1 font-mono text-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[10px] text-neutral-500 mb-0.5">Domyślny TP (%)</label>
                    <input
                      type="number"
                      min="0"
                      max="500"
                      value={mmDraft.default_take_profit_pct}
                      onChange={(e) => setMmDraft({ ...mmDraft, default_take_profit_pct: e.target.value })}
                      className="w-full border border-neutral-300 rounded px-2 py-1 font-mono text-xs"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-emerald-700 font-mono">{mmSavedMsg || ''}</span>
                  <button
                    type="button"
                    onClick={handleSaveMMInline}
                    disabled={mmSaving}
                    className="px-3 py-1.5 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-[11px] font-medium inline-flex items-center gap-1 cursor-pointer disabled:opacity-50"
                  >
                    <Check className="w-3 h-3" />
                    {mmSaving ? 'Zapisywanie...' : 'Zastosuj nowe MM'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* MM Warnings */}
          {mmWarnings.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 space-y-1">
              {mmWarnings.map((w, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800">
              {error}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2 border-t border-neutral-100">
            <span className="inline-flex items-center gap-1 text-[11px] text-neutral-500 font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              Wirtualny kapitał (Paper Trading)
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-2 text-xs text-neutral-600 hover:text-neutral-900 rounded-lg cursor-pointer"
              >
                Anuluj
              </button>
              <button
                type="submit"
                disabled={submitting || (isBuy ? estBuyShares <= 0 : parsedSellShares <= 0)}
                className={`px-4 py-2 text-white rounded-lg text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50 inline-flex items-center gap-1.5 ${
                  isBuy
                    ? 'bg-emerald-700 hover:bg-emerald-800'
                    : 'bg-rose-700 hover:bg-rose-800'
                }`}
              >
                <Wallet className="w-3.5 h-3.5" />
                {submitting
                  ? 'Realizuję...'
                  : isBuy
                  ? `Zatwierdź KUP (${order.ticker})`
                  : isFullClose
                  ? `Zatwierdź ZAMKNIĘCIE (${order.ticker})`
                  : `Zatwierdź SPRZEDAŻ (${parsedSellShares} szt.)`}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
