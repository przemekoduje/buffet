import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquareQuote,
  Send,
  Sparkles,
  X,
  FileText,
  Trash2,
  Bot,
  User,
  ArrowRight,
  TrendingUp,
  Compass,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Loader2,
  Info,
  BookOpen
} from 'lucide-react';

export default function ChatAdvisorDrawer({
  isOpen,
  onClose,
  activeTicker,
  onSelectTicker,
  onOpenOrderModal,
  onNavigateTab
}) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Witaj! Jestem Twoim wirtualnym doradcą inwestycyjnym w stylu **Warrena Buffetta i Charliego Mungera**, wbudowanym bezpośrednio w aplikację **BUFFET**.\n\nZnam tę aplikację na wylot — możesz zapytać mnie o każdy wskaźnik, metodologię wyceny DCF, stan Twojego portfela lub poprosić o natychmiastową analizę fundamentalną dowolnej spółki (np. *„Przeanalizuj AAPL”*).\n\nMożesz też wkleić fragment raportu finansowego za pomocą przycisku *„+ Dodaj dane zewnętrzne”*. W czym mogę Ci doradzić?`
    }
  ]);
  const [input, setInput] = useState('');
  const [customData, setCustomData] = useState('');
  const [showCustomDataInput, setShowCustomDataInput] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showKnowledge, setShowKnowledge] = useState(false);
  const [knowledgeTopics, setKnowledgeTopics] = useState([]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    // Pobierz sugerowane pytania startowe
    fetch('/api/chat/suggestions')
      .then((res) => res.json())
      .then((data) => {
        if (data.suggestions) setSuggestions(data.suggestions);
      })
      .catch(() => {});

    // Pobierz tematy z Banku Wiedzy
    fetch('/api/chat/knowledge')
      .then((res) => res.json())
      .then((data) => {
        if (data.topics) setKnowledgeTopics(data.topics);
      })
      .catch(() => {});
  }, []);

  const handleSend = async (textToSend = input) => {
    const text = textToSend.trim();
    if (!text || loading) return;

    const userMsg = { role: 'user', content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const cleanMessages = newMessages.map((m) => ({
        role: m.role,
        content: m.content
      }));

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: cleanMessages,
          context_ticker: activeTicker || undefined,
          custom_data: customData.trim() || undefined
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        const errorDetail = errData?.detail || `Błąd serwera (${res.status})`;
        throw new Error(errorDetail);
      }
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          dataUsed: data.data_used,
          suggestedActions: data.suggested_actions
        }
      ]);

      // Wyczyść custom data po wysłaniu
      if (customData.trim()) {
        setCustomData('');
        setShowCustomDataInput(false);
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Przepraszam, wystąpił problem techniczny podczas pobierania danych: ${err.message}. Spróbuj ponownie za chwilę.`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = () => {
    if (!window.confirm('Czy wyczyścić historię rozmowy z doradcą?')) return;
    setMessages([
      {
        role: 'assistant',
        content: `Rozpoczęliśmy nową sesję. Znam wszystkie dane aplikacji BUFFET. Wpisz ticker spółki (np. *KO*, *BRK.B*, *AAPL*) lub zadaj dowolne pytanie inwestycyjne.`
      }
    ]);
  };

  const handleActionClick = (action) => {
    if (action.action === 'OPEN_TICKER' && onSelectTicker) {
      onSelectTicker(action.ticker);
    } else if (action.action === 'ORDER_BUY' && onOpenOrderModal) {
      onOpenOrderModal({
        mode: 'BUY',
        ticker: action.ticker,
        current_price: 100 // modal pobierze aktualny kurs
      });
    } else if (action.action === 'NAVIGATE_TAB' && onNavigateTab) {
      onNavigateTab(action.tab);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className={`fixed bottom-0 right-0 z-50 flex flex-col bg-white border-l border-t border-neutral-200 shadow-2xl transition-all duration-300 font-sans ${
        isExpanded
          ? 'w-full md:w-[750px] h-[92vh] rounded-tl-2xl'
          : 'w-full md:w-[480px] h-[650px] max-h-[85vh] rounded-tl-2xl'
      }`}
    >
      {/* Top Header */}
      <div className="px-5 py-3.5 border-b border-neutral-200 bg-neutral-900 text-white flex items-center justify-between rounded-tl-2xl">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-400 text-neutral-950 flex items-center justify-center font-serif text-sm font-bold shadow-xs">
            WB
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-serif font-bold text-white tracking-tight">
                Warren Buffett AI &bull; Guru Inwestycyjny
              </h3>
              <span className="text-[10px] bg-neutral-800 text-amber-300 border border-neutral-700 px-1.5 py-0.2 rounded font-mono">
                LIVE
              </span>
            </div>
            <p className="text-[11px] text-neutral-400">
              Doradztwo oparte na 4 Zasadach Buffetta &bull; Zna aplikację na wylot
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setShowKnowledge(!showKnowledge)}
            title="Przeglądaj Bank Wiedzy aplikacji"
            className={`px-2.5 py-1 rounded-lg text-[11px] font-mono flex items-center gap-1.5 transition-colors cursor-pointer ${
              showKnowledge
                ? 'bg-amber-400 text-neutral-950 font-bold'
                : 'bg-neutral-800 hover:bg-neutral-700 text-amber-300 border border-neutral-700'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Bank Wiedzy</span>
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Zmniejsz okno' : 'Rozwiń na szerokość'}
            className="p-1.5 text-neutral-400 hover:text-white rounded-lg hover:bg-neutral-800 transition-colors cursor-pointer"
          >
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
          <button
            onClick={handleClearHistory}
            title="Wyczyść historię"
            className="p-1.5 text-neutral-400 hover:text-white rounded-lg hover:bg-neutral-800 transition-colors cursor-pointer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            title="Zamknij czat"
            className="p-1.5 text-neutral-400 hover:text-white rounded-lg hover:bg-neutral-800 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Knowledge Base Browser Panel */}
      {showKnowledge && (
        <div className="p-4 bg-amber-50/70 border-b border-amber-200 max-h-[45vh] overflow-y-auto text-xs">
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-amber-900" />
              <h4 className="font-serif font-bold text-neutral-900 text-sm">
                Oficjalny Bank Wiedzy Aplikacji BUFFET
              </h4>
            </div>
            <span className="text-[10px] font-mono text-amber-800 bg-amber-100 px-2 py-0.5 rounded">
              {knowledgeTopics.length} zagadnień
            </span>
          </div>
          <p className="text-[11px] text-neutral-600 mb-3 leading-relaxed">
            Kliknij dowolne zagadnienie, aby zapytać o nie Warrena Buffetta lub poznać dokładne formuły i metodologię:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {knowledgeTopics.map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  setShowKnowledge(false);
                  handleSend(`Wyjaśnij mi szczegółowo zagadnienie z Banku Wiedzy: ${t.title}`);
                }}
                className="p-2.5 bg-white hover:bg-amber-100/50 border border-amber-200/80 rounded-xl text-left transition-colors cursor-pointer group shadow-2xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[9px] font-mono font-bold text-amber-800 uppercase tracking-wider">
                    {t.category}
                  </span>
                  <ArrowRight className="w-3 h-3 text-neutral-300 group-hover:text-amber-700 transition-colors" />
                </div>
                <div className="font-medium text-neutral-900 text-[11px] leading-snug">
                  {t.title}
                </div>
                <div className="text-[10px] text-neutral-500 line-clamp-2 mt-1">
                  {t.summary}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-neutral-50/40 text-xs">
        {messages.map((m, idx) => {
          const isUser = m.role === 'user';
          return (
            <div
              key={idx}
              className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-7 h-7 rounded-lg bg-neutral-900 text-amber-400 flex items-center justify-center font-serif text-xs font-bold shrink-0 mt-0.5">
                  B
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-2xl p-4 shadow-xs leading-relaxed ${
                  isUser
                    ? 'bg-neutral-900 text-white rounded-br-xs'
                    : 'bg-white border border-neutral-200 text-neutral-900 rounded-bl-xs'
                }`}
              >
                {/* Treść wiadomości z obsługą markdown-like formatowania */}
                <div className="whitespace-pre-wrap font-sans text-xs">
                  {m.content}
                </div>

                {/* Wykorzystane dane rynkowe badge */}
                {m.dataUsed?.analyzed_stocks && m.dataUsed.analyzed_stocks.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-neutral-100 flex flex-wrap gap-1.5">
                    <span className="text-[10px] text-neutral-400 font-mono">Pobrane dane:</span>
                    {m.dataUsed.analyzed_stocks.map((s) => (
                      <span
                        key={s.ticker}
                        className="text-[10px] bg-neutral-100 border border-neutral-200 text-neutral-800 px-1.5 py-0.5 rounded font-mono"
                      >
                        {s.ticker}: DCF ${s.intrinsic_value} ({s.margin_of_safety_pct}%)
                      </span>
                    ))}
                  </div>
                )}

                {/* Sugerowane akcje */}
                {m.suggestedActions && m.suggestedActions.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-neutral-100 flex flex-wrap gap-2">
                    {m.suggestedActions.map((act, aIdx) => (
                      <button
                        key={aIdx}
                        onClick={() => handleActionClick(act)}
                        className="px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-lg text-[11px] font-medium transition-colors flex items-center gap-1 cursor-pointer"
                      >
                        <span>{act.label}</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded-lg bg-neutral-200 text-neutral-700 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-3 justify-start items-center text-neutral-500 font-mono text-xs pl-1">
            <div className="w-7 h-7 rounded-lg bg-neutral-900 text-amber-400 flex items-center justify-center font-serif text-xs font-bold shrink-0">
              B
            </div>
            <div className="bg-white border border-neutral-200 rounded-2xl px-4 py-2.5 shadow-xs flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-neutral-700" />
              <span>Warren analizuje fundamenty, wycenę DCF i rynek...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestions (gdy mało wiadomości lub po pytaniu) */}
      {messages.length <= 3 && (
        <div className="px-4 py-2 bg-neutral-100/60 border-t border-neutral-200 overflow-x-auto flex gap-1.5 no-scrollbar">
          {suggestions.slice(0, 4).map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(s.prompt)}
              className="whitespace-nowrap px-2.5 py-1 bg-white hover:bg-neutral-50 text-neutral-700 border border-neutral-200 rounded-lg text-[11px] font-medium transition-colors shrink-0 cursor-pointer shadow-2xs"
            >
              {s.label}
            </button>
          ))}
        </div>
      )}

      {/* Custom Data Attachment Accordion */}
      {showCustomDataInput && (
        <div className="p-3 bg-amber-50/60 border-t border-amber-200 text-xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-[11px] font-bold text-amber-900 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" />
              Wklej dane zewnętrzne / fragment sprawozdania finansowego:
            </span>
            <button
              onClick={() => setShowCustomDataInput(false)}
              className="text-neutral-400 hover:text-neutral-700 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <textarea
            rows={3}
            placeholder="Wklej tutaj fragment raportu kwartalnego, bilansu, notatki analitycznej lub artykułu prasowego..."
            value={customData}
            onChange={(e) => setCustomData(e.target.value)}
            className="w-full p-2 border border-amber-300 rounded-lg bg-white text-xs font-mono focus:outline-none focus:ring-1 focus:ring-amber-500"
          />
        </div>
      )}

      {/* Bottom Input Form */}
      <div className="p-3 bg-white border-t border-neutral-200">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <button
            type="button"
            onClick={() => setShowCustomDataInput(!showCustomDataInput)}
            title="Dodaj dane zewnętrzne lub fragment raportu"
            className={`p-2 rounded-xl border transition-colors cursor-pointer ${
              showCustomDataInput || customData.trim()
                ? 'bg-amber-100 text-amber-900 border-amber-300'
                : 'bg-neutral-100 hover:bg-neutral-200 text-neutral-600 border-neutral-200'
            }`}
          >
            <FileText className="w-4 h-4" />
          </button>

          <input
            type="text"
            placeholder={
              activeTicker
                ? `Zapytaj o ${activeTicker} lub zadaj dowolne pytanie inwestycyjne...`
                : "Zapytaj o spółkę, DCF, portfel lub okazje rynkowe..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="flex-1 px-3.5 py-2.5 bg-neutral-50 border border-neutral-300 rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900"
          />

          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2.5 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-40 text-white rounded-xl transition-all cursor-pointer shadow-xs"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>

        <div className="flex items-center justify-between text-[10px] text-neutral-400 font-mono mt-2 px-1">
          <span>Agent zna wszystkie parametry spółki &bull; Reguła 1</span>
          <span>przemokoduje.com</span>
        </div>
      </div>
    </div>
  );
}
