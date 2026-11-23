import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import {
  TrendingUp,
  ShieldCheck,
  Award,
  DollarSign,
  BarChart3,
  Percent,
  CheckCircle2,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';

/**
 * Visual Stock Snapshot Card rendered inside the message if stock data is attached.
 */
function StockVisualSnapshot({ stock, onActionClick }) {
  if (!stock) return null;

  const currentPrice = Number(stock.current_price || 0);
  const intrinsicVal = Number(stock.intrinsic_value || 0);
  const mos = Number(stock.margin_of_safety_pct || 0);
  const pe = Number(stock.pe_ratio || 0);
  const roic = Number(stock.roic_pct || 0);
  const grossMargin = Number(stock.gross_margin_pct || 0);
  const score = Number(stock.buffett_score || 0);
  const rec = stock.recommendation || 'HOLD';

  const isCheap = mos > 0;
  const isHighMoat = roic >= 15 && grossMargin >= 40;

  // Max value for comparative bar scaling
  const maxVal = Math.max(currentPrice, intrinsicVal, 1) * 1.15;
  const currentWidthPct = Math.min(100, Math.round((currentPrice / maxVal) * 100));
  const intrinsicWidthPct = Math.min(100, Math.round((intrinsicVal / maxVal) * 100));

  return (
    <div className="my-3.5 bg-neutral-900 text-white rounded-xl p-3.5 border border-neutral-800 shadow-md">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-neutral-800 mb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-amber-400 text-neutral-950 font-mono font-bold flex items-center justify-center text-xs">
            {stock.ticker}
          </div>
          <div>
            <h4 className="text-xs font-bold text-white leading-tight">
              {stock.company_name}
            </h4>
            <span className="text-[10px] text-neutral-400 font-mono">
              Sektor: {stock.sector || 'Finanse / Tech'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
              rec === 'STRONG_BUY'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : rec === 'BUY'
                ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            }`}
          >
            {rec}
          </span>
          <span className="text-[10px] bg-neutral-800 text-amber-300 border border-neutral-700 px-1.5 py-0.5 rounded font-mono font-bold">
            Score {score}/100
          </span>
        </div>
      </div>

      {/* Comparative Valuation Bar: Price vs Intrinsic Value */}
      <div className="mb-3 bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/80">
        <div className="flex justify-between items-center text-[10px] font-mono text-neutral-400 mb-1.5">
          <span>WYCENA DCF VS KURS RYNKOWY</span>
          <span className={isCheap ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
            Margines: {mos > 0 ? `+${mos}%` : `${mos}%`}
          </span>
        </div>

        {/* Current Price Bar */}
        <div className="mb-1.5">
          <div className="flex justify-between text-[10px] mb-0.5">
            <span className="text-neutral-400">Kurs Rynkowy:</span>
            <span className="font-mono font-semibold text-white">${currentPrice.toFixed(2)}</span>
          </div>
          <div className="w-full bg-neutral-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-amber-400 h-full rounded-full transition-all duration-500"
              style={{ width: `${currentWidthPct}%` }}
            />
          </div>
        </div>

        {/* Intrinsic Value Bar */}
        <div>
          <div className="flex justify-between text-[10px] mb-0.5">
            <span className="text-neutral-400">Wartość Wewnętrzna (DCF):</span>
            <span className="font-mono font-semibold text-emerald-400">${intrinsicVal.toFixed(2)}</span>
          </div>
          <div className="w-full bg-neutral-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${intrinsicWidthPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Key Multiples Matrix */}
      <div className="grid grid-cols-3 gap-2 text-center text-[10px]">
        {/* P/E */}
        <div className="bg-neutral-800/50 p-2 rounded-lg border border-neutral-700/50">
          <span className="text-neutral-400 block mb-0.5">C/Z (P/E)</span>
          <span className="text-xs font-mono font-bold text-white">
            {pe > 0 ? `${pe.toFixed(2)}x` : 'N/A'}
          </span>
          <span className="text-[9px] block text-emerald-400 mt-0.5">
            {pe < 18 ? 'Głębokie dyskonto' : 'Wycena rynkowa'}
          </span>
        </div>

        {/* ROIC */}
        <div className="bg-neutral-800/50 p-2 rounded-lg border border-neutral-700/50">
          <span className="text-neutral-400 block mb-0.5">ROIC (Fosa)</span>
          <span
            className={`text-xs font-mono font-bold ${
              roic >= 15 ? 'text-emerald-400' : 'text-neutral-200'
            }`}
          >
            {roic.toFixed(1)}%
          </span>
          <span className="text-[9px] block text-neutral-400 mt-0.5">
            {roic >= 15 ? 'Próg min. 15% ✓' : 'Poniżej progu'}
          </span>
        </div>

        {/* Gross Margin */}
        <div className="bg-neutral-800/50 p-2 rounded-lg border border-neutral-700/50">
          <span className="text-neutral-400 block mb-0.5">Marża Brutto</span>
          <span
            className={`text-xs font-mono font-bold ${
              grossMargin >= 40 ? 'text-emerald-400' : 'text-neutral-200'
            }`}
          >
            {grossMargin.toFixed(1)}%
          </span>
          <span className="text-[9px] block text-neutral-400 mt-0.5">
            {grossMargin >= 40 ? 'Pricing Power ✓' : 'Średnia'}
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * Enhanced Message Renderer with KaTeX, styled headings, quotes, tables, and stock snapshots.
 */
export default function ChatMessageContent({ content, dataUsed, onActionClick }) {
  const stock = dataUsed?.analyzed_stocks?.[0];

  return (
    <div className="chat-message-content space-y-2 text-neutral-900 leading-relaxed text-xs">
      {/* Markdown Content with KaTeX Math Rendering */}
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          h1: ({ node, ...props }) => (
            <h1 className="text-sm font-serif font-bold text-neutral-900 border-b border-amber-200 pb-1 mt-3 mb-2 flex items-center gap-1.5" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-xs font-serif font-bold text-neutral-900 border-b border-neutral-100 pb-1 mt-2.5 mb-1.5" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-xs font-sans font-bold text-neutral-900 text-amber-900 mt-2 mb-1 flex items-center gap-1" {...props} />
          ),
          p: ({ node, ...props }) => (
            <p className="mb-2 leading-relaxed text-neutral-800" {...props} />
          ),
          strong: ({ node, ...props }) => (
            <strong className="font-semibold text-neutral-950 bg-amber-50/80 px-1 py-0.2 rounded" {...props} />
          ),
          em: ({ node, ...props }) => (
            <em className="italic text-neutral-700" {...props} />
          ),
          blockquote: ({ node, ...props }) => (
            <blockquote className="my-2.5 pl-3 border-l-2 border-amber-500 bg-amber-50/60 py-1.5 pr-2 rounded-r-lg italic text-[11px] text-neutral-800 shadow-2xs" {...props} />
          ),
          ul: ({ node, ...props }) => (
            <ul className="list-disc pl-4 space-y-1 mb-2 text-neutral-800 marker:text-amber-500" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal pl-4 space-y-1 mb-2 text-neutral-800 marker:font-bold marker:text-amber-700" {...props} />
          ),
          li: ({ node, ...props }) => (
            <li className="leading-snug" {...props} />
          ),
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-2.5 rounded-lg border border-neutral-200 shadow-2xs">
              <table className="min-w-full text-[11px] divide-y divide-neutral-200 text-left" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-neutral-100 font-mono font-semibold text-neutral-800" {...props} />
          ),
          tbody: ({ node, ...props }) => (
            <tbody className="divide-y divide-neutral-100 bg-white" {...props} />
          ),
          tr: ({ node, ...props }) => (
            <tr className="hover:bg-neutral-50/80 transition-colors" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="px-2.5 py-1.5 font-medium text-neutral-700" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="px-2.5 py-1.5 font-mono text-neutral-800" {...props} />
          ),
          code: ({ node, inline, ...props }) => (
            inline ? (
              <code className="font-mono text-[11px] bg-neutral-100 text-amber-900 border border-neutral-200 px-1 py-0.2 rounded" {...props} />
            ) : (
              <pre className="p-2.5 bg-neutral-900 text-neutral-100 rounded-lg overflow-x-auto font-mono text-[11px] my-2 border border-neutral-800" {...props} />
            )
          )
        }}
      >
        {content}
      </ReactMarkdown>

      {/* Embedded Visual Metric Card if stock data is available */}
      {stock && (
        <StockVisualSnapshot stock={stock} onActionClick={onActionClick} />
      )}
    </div>
  );
}
