import React, { useState, useEffect } from 'react';
import { ShieldAlert, CheckCircle2, XCircle, Plus, Sparkles, RefreshCw, Key, Newspaper, ExternalLink } from 'lucide-react';

export default function DeepDiveView({
  ticker,
  activeProvider,
  portfolioSummary,
  onOpenOrderModal,
  onOpenSettings,
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshingAI, setRefreshingAI] = useState(false);
  const [message, setMessage] = useState(null);

  const existingHolding = (portfolioSummary?.holdings || []).find((h) => h.ticker === ticker) || null;

  const loadAnalysis = (refreshAi = false) => {
    if (!ticker) return;
    if (refreshAi) {
      setRefreshingAI(true);
    } else {
      setLoading(true);
    }
    setMessage(null);
    fetch(`/api/analysis/${ticker}?provider_name=${activeProvider || 'yfinance'}&refresh_ai=${refreshAi}`)
      .then((res) => {
        if (!res.ok) throw new Error('Nie znaleziono danych spółki');
        return res.json();
      })
      .then((res) => {
        setData(res);
      })
      .catch((err) => {
        console.error(err);
        setMessage({ type: 'error', text: err.message });
      })
      .finally(() => {
        setLoading(false);
        setRefreshingAI(false);
      });
  };

  useEffect(() => {
    loadAnalysis(false);
  }, [ticker, activeProvider]);

  if (loading || !data) {
    return (
      <div className="py-24 text-center text-neutral-500 font-mono text-sm">
        Pobieranie realnych sprawozdań finansowych i generowanie memoriału AI dla {ticker}...
      </div>
    );
  }

  const { fundamental, valuation, ai_memo, buffett_principles, news = [] } = data;
  const isUndervalued = valuation.margin_of_safety_pct > 0;
  const isLiveGemini = ai_memo.ai_source === 'gemini';

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Info */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-xl font-bold font-mono text-neutral-900">{fundamental.ticker}</span>
            <span className="text-xs bg-neutral-100 text-neutral-600 px-2 py-0.5 rounded font-medium border border-neutral-200">
              {fundamental.sector} &bull; {fundamental.industry}
            </span>
            <span className="text-[10px] font-mono uppercase bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded">
              Dane: {fundamental.source}
            </span>
          </div>
          <h2 className="text-2xl font-serif font-bold text-neutral-900">{fundamental.company_name}</h2>
          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-neutral-500 mt-2">
            <span>Kapitalizacja: ${(fundamental.market_cap / 1e9).toFixed(1)} mld</span>
            <span>&bull;</span>
            <span>C/Z (P/E): {fundamental.pe_ratio}</span>
            <span>&bull;</span>
            <span>Dywidenda: {fundamental.dividend_yield_pct}%</span>
            <span>&bull;</span>
            <span>Owner Earnings: ${(valuation.owner_earnings_ttm / 1000).toFixed(2)} mld</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-end md:items-center gap-3">
          <div className="text-right">
            <div className="text-[11px] font-mono text-neutral-400 uppercase">Aktualny Kurs</div>
            <div className="text-2xl font-serif font-bold text-neutral-900">${fundamental.current_price}</div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() =>
                onOpenOrderModal({
                  mode: 'BUY',
                  ticker: fundamental.ticker,
                  company_name: fundamental.company_name,
                  current_price: fundamental.current_price,
                  holding: existingHolding,
                })
              }
              className="px-4 py-2.5 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-xs font-medium transition-all shadow-xs flex items-center gap-2 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>{existingHolding ? 'Dokup (MM)' : 'Kup (Paper Trading)'}</span>
            </button>
            {existingHolding && (
              <button
                onClick={() =>
                  onOpenOrderModal({
                    mode: 'SELL',
                    ticker: fundamental.ticker,
                    company_name: fundamental.company_name,
                    current_price: fundamental.current_price,
                    holding: existingHolding,
                  })
                }
                className="px-3.5 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg text-xs font-medium transition-all cursor-pointer"
              >
                Sprzedaj / Zamknij
              </button>
            )}
          </div>
        </div>
      </div>

      {message && (
        <div
          className={`p-4 rounded-lg text-xs border ${message.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
        >
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
            Wyliczona na bazie 10-letniej projekcji Zysku Właścicielskiego (Owner Earnings) &bull;{' '}
            {valuation.owner_earnings_method || '10-letnia projekcja Owner Earnings'}
          </p>
          {valuation.dcf_assumptions && (
            <div className="text-[10px] font-mono text-neutral-400 mt-1.5">
              r={valuation.dcf_assumptions.discount_rate_pct}% &bull; g1-5={valuation.dcf_assumptions.growth_y1_5_pct}% &bull; g6-10={valuation.dcf_assumptions.growth_y6_10_pct}% &bull; term={valuation.dcf_assumptions.terminal_growth_pct}%
            </div>
          )}
        </div>

        <div className={`border rounded-xl p-5 shadow-xs ${isUndervalued ? 'bg-emerald-50/50 border-emerald-200' : 'bg-neutral-50 border-neutral-200'}`}>
          <div className="text-xs font-mono text-neutral-500 uppercase">Margines Bezpieczeństwa</div>
          <div className={`text-3xl font-serif font-bold mt-1 ${isUndervalued ? 'text-emerald-700' : 'text-neutral-700'}`}>
            {isUndervalued ? `+${valuation.margin_of_safety_pct}%` : `${valuation.margin_of_safety_pct}%`}
          </div>
          <p className="text-[11px] text-neutral-600 mt-1">
            {isUndervalued
              ? 'Kurs dyskontuje ryzyko — poduszka ochronna kapitału.'
              : 'Brak marginesu — ryzyko zakupu powyżej wartości wewnętrznej.'}
          </p>
        </div>

        <div className="bg-white border border-neutral-200 rounded-xl p-5 shadow-xs">
          <div className="text-xs font-mono text-neutral-500 uppercase">Buffett Score</div>
          <div className="text-3xl font-serif font-bold text-neutral-900 mt-1 flex items-center gap-2">
            {valuation.buffett_score}
            <span className="text-xs font-mono font-normal text-neutral-400">/ 100</span>
          </div>
          <div className="mt-1">
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${valuation.recommendation === 'STRONG_BUY'
                  ? 'bg-emerald-100 text-emerald-800'
                  : valuation.recommendation === 'BUY'
                    ? 'bg-blue-100 text-blue-800'
                    : valuation.recommendation === 'HOLD'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-neutral-100 text-neutral-600'
                }`}
            >
              Rekomendacja: {valuation.recommendation}
            </span>
          </div>
        </div>
      </div>

      {/* AI Warren Buffett Memo */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-600" />
            <h3 className="text-sm font-serif font-bold text-neutral-900">
              Memoriał Inwestycyjny AI (Głos Warrena Buffetta)
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${isLiveGemini
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border border-amber-200'
                }`}
            >
              {isLiveGemini ? `AI Live: ${ai_memo.ai_model}` : 'Tryb heurystyczny (brak klucza Gemini)'}
            </span>
            {!isLiveGemini && onOpenSettings && (
              <button
                onClick={onOpenSettings}
                className="text-[11px] font-mono px-2 py-0.5 bg-neutral-900 hover:bg-neutral-800 text-white rounded flex items-center gap-1 cursor-pointer"
              >
                <Key className="w-3 h-3" />
                Dodaj klucz AI
              </button>
            )}
            <button
              onClick={() => loadAnalysis(true)}
              disabled={refreshingAI}
              title="Wygeneruj ponownie analizę AI"
              className="p-1.5 text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 rounded transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshingAI ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {ai_memo.ai_note && (
          <div className="text-[11px] font-mono text-neutral-500 bg-neutral-50 border border-neutral-100 rounded-lg px-3 py-2">
            {ai_memo.ai_note}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-1">
            <h4 className="text-xs font-mono font-bold text-neutral-700 uppercase">Teza Inwestycyjna</h4>
            <p className="text-xs text-neutral-600 leading-relaxed font-sans">{ai_memo.thesis}</p>
          </div>

          <div className="space-y-1">
            <h4 className="text-xs font-mono font-bold text-neutral-700 uppercase">Fosa Ekonomiczna (Moat)</h4>
            <p className="text-xs text-neutral-600 leading-relaxed font-sans">{ai_memo.moat}</p>
          </div>

          <div className="space-y-1">
            <h4 className="text-xs font-mono font-bold uppercase flex items-center gap-1 text-amber-800">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
              <span>Reguła 1: Audyt Ryzyka</span>
            </h4>
            <p className="text-xs text-neutral-600 leading-relaxed font-sans">{ai_memo.rule_1_risks}</p>
          </div>
        </div>

        {ai_memo.news_impact && (
          <div className="pt-4 border-t border-neutral-100 flex flex-col sm:flex-row sm:items-start justify-between gap-3">
            <div className="space-y-1 flex-1">
              <div className="flex items-center gap-2">
                <Newspaper className="w-3.5 h-3.5 text-neutral-600" />
                <h4 className="text-xs font-mono font-bold text-neutral-700 uppercase">
                  Wpływ Bieżących Newsów Rynkowych (Ocena AI)
                </h4>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                    ai_memo.news_sentiment === 'POSITIVE'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : ai_memo.news_sentiment === 'NEGATIVE'
                      ? 'bg-rose-50 text-rose-700 border-rose-200'
                      : 'bg-neutral-100 text-neutral-700 border-neutral-200'
                  }`}
                >
                  Sentyment: {ai_memo.news_sentiment === 'POSITIVE' ? 'POZYTYWNY' : ai_memo.news_sentiment === 'NEGATIVE' ? 'NEGATYWNY' : 'NEUTRALNY'}
                </span>
              </div>
              <p className="text-xs text-neutral-600 leading-relaxed">{ai_memo.news_impact}</p>
            </div>
          </div>
        )}
      </div>

      {/* Latest Market News */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-neutral-700" />
            <h3 className="text-sm font-serif font-bold text-neutral-900">
              Ostatnie Newsy Rynkowe — {fundamental.ticker}
            </h3>
          </div>
          <span className="text-[11px] font-mono text-neutral-500">
            Źródło: Yahoo Finance ({news.length} wiadomości)
          </span>
        </div>

        {news.length === 0 ? (
          <p className="text-xs text-neutral-500">Brak bieżących nagłówków prasowych dla tej spółki.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {news.map((item, idx) => (
              <a
                key={idx}
                href={item.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="group border border-neutral-100 hover:border-neutral-300 rounded-lg p-3.5 bg-neutral-50/40 hover:bg-neutral-50 transition-all flex flex-col justify-between gap-2"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-xs font-semibold text-neutral-900 group-hover:underline leading-snug">
                      {item.title}
                    </h4>
                    <ExternalLink className="w-3.5 h-3.5 text-neutral-400 group-hover:text-neutral-700 shrink-0 mt-0.5" />
                  </div>
                  {item.summary && (
                    <p className="text-[11px] text-neutral-600 mt-1 line-clamp-2 leading-relaxed">
                      {item.summary}
                    </p>
                  )}
                </div>
                <div className="flex items-center justify-between text-[10px] font-mono text-neutral-400 pt-1">
                  <span>{item.publisher}</span>
                  <span>{item.published_at}</span>
                </div>
              </a>
            ))}
          </div>
        )}
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
