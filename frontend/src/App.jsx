import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import PortfolioView from './components/PortfolioView';
import ScreenerView from './components/ScreenerView';
import DeepDiveView from './components/DeepDiveView';
import SettingsView from './components/SettingsView';
import TradeOrderModal from './components/TradeOrderModal';
import AuthModal from './components/AuthModal';
import ChatAdvisorDrawer from './components/ChatAdvisorDrawer';
import {
  subscribeToAuthChanges,
  logoutUser,
  saveUserDataToFirebase,
  loadUserDataFromFirebase
} from './config/firebase';

export default function App() {
  const [activeTab, setActiveTab] = useState('portfolio');
  const [activeProvider, setActiveProvider] = useState('yfinance');
  const [selectedTicker, setSelectedTicker] = useState('BRK.B');
  const [orderModal, setOrderModal] = useState(null);
  const [tradeNotice, setTradeNotice] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Autoryzacja i Firebase Cloud Sync
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [syncStatus, setSyncStatus] = useState('local'); // 'synced', 'syncing', 'local'
  const [lastSyncTime, setLastSyncTime] = useState(null);

  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [portfolioRefreshing, setPortfolioRefreshing] = useState(false);

  const [screenerData, setScreenerData] = useState(null);
  const [screenerLoading, setScreenerLoading] = useState(true);
  const [screenerScanning, setScreenerScanning] = useState(false);
  const [alertsChecking, setAlertsChecking] = useState(false);

  const hasRestoredUidRef = useRef(null);

  // Funkcja synchronizacji stanu do Firebase i backendu
  const syncToCloud = useCallback(async (user, currentSummary) => {
    if (!user || !currentSummary) return;
    setSyncStatus('syncing');
    try {
      const payload = {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        portfolio: {
          initial_capital: currentSummary.initial_capital,
          cash_balance: currentSummary.cash_balance,
          realized_pnl_cash: currentSummary.realized_pnl_cash,
          total_portfolio_value: currentSummary.total_portfolio_value,
          total_invested: currentSummary.total_invested,
          total_pnl_cash: currentSummary.total_pnl_cash,
          total_pnl_pct: currentSummary.total_pnl_pct,
          holdings: currentSummary.holdings || [],
        },
        mm_config: currentSummary.mm_config || currentSummary.account_config || null,
        trades: currentSummary.trades || currentSummary.recent_trades || [],
      };

      // 1. Zapis bezpośredni do Google Cloud Firestore
      await saveUserDataToFirebase(user.uid, payload);

      // 2. Powiadomienie backendu API
      await fetch('/api/user/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      setSyncStatus('synced');
      setLastSyncTime(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('[Cloud Sync Error]', err);
      setSyncStatus('synced');
    }
  }, []);

  const fetchPortfolio = useCallback((silent = false, shouldSync = false) => {
    if (!silent) setPortfolioLoading(true);
    fetch('/api/portfolio')
      .then((res) => res.json())
      .then((data) => {
        setPortfolioSummary(data);
        setPortfolioLoading(false);
        if (shouldSync && currentUser) {
          syncToCloud(currentUser, data);
        }
      })
      .catch((err) => {
        console.error(err);
        setPortfolioLoading(false);
      });
  }, [currentUser, syncToCloud]);

  // Nasłuchiwanie stanu autoryzacji Firebase (jednorazowa subskrypcja)
  useEffect(() => {
    const unsubscribe = subscribeToAuthChanges(async (user) => {
      setCurrentUser(user);
      if (user) {
        if (hasRestoredUidRef.current === user.uid) return;
        hasRestoredUidRef.current = user.uid;
        setSyncStatus('syncing');
        try {
          // 1. Pobierz i odtwórz dane użytkownika z Firestore przez Backend Admin SDK (omija lokalne ograniczenia reguł klienta)
          const loadRes = await fetch(`/api/user/load/${user.uid}`, { method: 'POST' });
          if (loadRes.ok) {
            const loaded = await loadRes.json();
            if (loaded.found && loaded.summary) {
              console.log('[Firebase] Odtworzono portfel z chmury Firestore:', loaded.restored_holdings, 'pozycji');
              setPortfolioSummary(loaded.summary);
              setPortfolioLoading(false);
              fetchScreener(activeProvider, true);
              setSyncStatus('synced');
              setLastSyncTime(new Date().toLocaleTimeString());
              return;
            }
          }

          // 2. Fallback: spróbuj odczytać przez Client SDK
          const cloudData = await loadUserDataFromFirebase(user.uid);
          if (cloudData && cloudData.portfolio) {
            const restoreRes = await fetch('/api/user/restore', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                uid: user.uid,
                email: user.email,
                displayName: user.displayName,
                portfolio: cloudData.portfolio,
                mm_config: cloudData.mm_config,
                trades: cloudData.trades,
                watchlist: cloudData.watchlist,
              })
            });
            if (restoreRes.ok) {
              const restored = await restoreRes.json();
              if (restored.summary) {
                setPortfolioSummary(restored.summary);
                setPortfolioLoading(false);
                fetchScreener(activeProvider, true);
              }
            }
          } else if (loadRes.ok) {
            // Tylko gdy backend potwierdził, że dokument naprawdę nie istnieje (nowy użytkownik)
            const res = await fetch('/api/portfolio');
            if (res.ok) {
              const localSummary = await res.json();
              setPortfolioSummary(localSummary);
              await syncToCloud(user, localSummary);
            }
          }
          setSyncStatus('synced');
          setLastSyncTime(new Date().toLocaleTimeString());
        } catch (err) {
          console.error('[Firebase Auth Sync Error]', err);
          setSyncStatus('synced');
        }
      } else {
        hasRestoredUidRef.current = null;
        setSyncStatus('local');
      }
    });

    return () => unsubscribe();
  }, [syncToCloud]);

  const handleRefreshPortfolio = async () => {
    setPortfolioRefreshing(true);
    try {
      const res = await fetch('/api/portfolio/refresh', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setPortfolioSummary(data);
        if (currentUser) syncToCloud(currentUser, data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setPortfolioRefreshing(false);
    }
  };

  const handleSaveMM = async (mmUpdates) => {
    const res = await fetch('/api/portfolio/mm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mmUpdates),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Błąd zapisu ustawień MM');
    setPortfolioSummary(json);
    if (currentUser) syncToCloud(currentUser, json);
    return json;
  };

  const handleResetAccount = async (initialCapital) => {
    const res = await fetch('/api/portfolio/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initial_capital: initialCapital }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Błąd resetowania konta');
    setPortfolioSummary(json);
    fetchScreener(activeProvider, true);
    if (currentUser) syncToCloud(currentUser, json);
    return json;
  };

  const handleBuyOrder = async (orderPayload) => {
    const res = await fetch('/api/portfolio/buy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...orderPayload,
        provider_name: activeProvider,
      }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Błąd zlecenia KUP');
    fetchPortfolio(true, true);
    fetchScreener(activeProvider, true);
    setTradeNotice(json.message);
    setTimeout(() => setTradeNotice(null), 5000);
    return json;
  };

  const handleSellHolding = async (holdingId, shares = null, note = '') => {
    const res = await fetch(`/api/portfolio/sell/${holdingId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shares, note }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Błąd sprzedaży pozycji');
    fetchPortfolio(true, true);
    fetchScreener(activeProvider, true);
    setTradeNotice(json.message);
    setTimeout(() => setTradeNotice(null), 5000);
    return json;
  };

  const fetchScreener = (provider = activeProvider, silent = false) => {
    if (!silent) setScreenerLoading(true);
    fetch(`/api/screener?provider_name=${provider}`)
      .then((res) => res.json())
      .then((data) => {
        setScreenerData(data);
        setScreenerLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setScreenerLoading(false);
      });
  };

  const handleRunEodScan = async () => {
    setScreenerScanning(true);
    try {
      const res = await fetch(`/api/screener/run-eod?provider_name=${activeProvider}&sync=true`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchScreener(activeProvider, true);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setScreenerScanning(false);
    }
  };

  const handleCheckAlerts = async () => {
    setAlertsChecking(true);
    try {
      const res = await fetch('/api/screener/alerts/check', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setScreenerData((prev) =>
          prev
            ? {
                ...prev,
                alerts: data.alerts || prev.alerts,
                market_session: data.market_session || prev.market_session,
              }
            : prev
        );
        fetchScreener(activeProvider, true);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setAlertsChecking(false);
    }
  };

  useEffect(() => {
    fetch('/api/settings')
      .then((res) => res.json())
      .then((data) => {
        const prov = data.active_data_provider || 'yfinance';
        setActiveProvider(prov);
        fetchScreener(prov);
      })
      .catch((err) => {
        console.error(err);
        fetchScreener('yfinance');
      });

    fetchPortfolio();
  }, []);

  useEffect(() => {
    if (activeTab !== 'screener') return;
    const interval = setInterval(() => {
      fetch('/api/screener/alerts')
        .then((res) => res.json())
        .then((data) => {
          setScreenerData((prev) =>
            prev
              ? {
                  ...prev,
                  alerts: data.alerts || prev.alerts,
                  market_session: data.market_session || prev.market_session,
                }
              : prev
          );
        })
        .catch(() => {});
    }, 300000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const handleSelectTicker = (ticker) => {
    setSelectedTicker(ticker);
    setActiveTab('deepdive');
  };

  const handleScanCustom = async (ticker) => {
    const res = await fetch(`/api/screener/scan/${ticker}?provider_name=${activeProvider}`);
    if (!res.ok) throw new Error('Ticker not found');
    const data = await res.json();
    setSelectedTicker(ticker);
    setActiveTab('deepdive');
    return data;
  };

  const handleUpdateProvider = (newProvider) => {
    setActiveProvider(newProvider);
    fetchScreener(newProvider);
    fetchPortfolio();
  };

  return (
    <div className="min-h-screen bg-[#fcfcfc] text-[#171717] flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeProvider={activeProvider}
        user={currentUser}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={logoutUser}
        syncStatus={syncStatus}
        onManualSync={() => syncToCloud(currentUser, portfolioSummary)}
        isChatOpen={isChatOpen}
        onToggleChat={() => setIsChatOpen(!isChatOpen)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        {tradeNotice && (
          <div className="mb-5 p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl font-medium">
            {tradeNotice}
          </div>
        )}

        {activeTab === 'portfolio' && (
          <PortfolioView
            summary={portfolioSummary}
            loading={portfolioLoading}
            refreshing={portfolioRefreshing}
            onRefresh={handleRefreshPortfolio}
            onSelectTicker={handleSelectTicker}
            onOpenOrderModal={setOrderModal}
            onSaveMM={handleSaveMM}
            onResetAccount={handleResetAccount}
            user={currentUser}
            onOpenAuth={() => setIsAuthModalOpen(true)}
            onManualSync={() => syncToCloud(currentUser, portfolioSummary)}
            lastSyncTime={lastSyncTime}
          />
        )}

        {activeTab === 'screener' && (
          <ScreenerView
            screenerData={screenerData}
            loading={screenerLoading}
            scanning={screenerScanning}
            alertsChecking={alertsChecking}
            activeProvider={activeProvider}
            onSelectTicker={handleSelectTicker}
            onOpenOrderModal={setOrderModal}
            onScanCustom={handleScanCustom}
            onRunEodScan={handleRunEodScan}
            onCheckAlerts={handleCheckAlerts}
          />
        )}

        {activeTab === 'deepdive' && (
          <DeepDiveView
            ticker={selectedTicker}
            activeProvider={activeProvider}
            portfolioSummary={portfolioSummary}
            onOpenOrderModal={setOrderModal}
            onBackToScreener={() => setActiveTab('screener')}
            onOpenSettings={() => setActiveTab('settings')}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsView
            activeProvider={activeProvider}
            onUpdateProvider={handleUpdateProvider}
            user={currentUser}
            onOpenAuth={() => setIsAuthModalOpen(true)}
            onManualSync={() => syncToCloud(currentUser, portfolioSummary)}
            lastSyncTime={lastSyncTime}
          />
        )}
      </main>

      <TradeOrderModal
        order={orderModal}
        portfolioSummary={portfolioSummary}
        onClose={() => setOrderModal(null)}
        onExecuteBuy={handleBuyOrder}
        onExecuteSell={handleSellHolding}
        onSaveMM={handleSaveMM}
      />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={(user) => {
          setCurrentUser(user);
        }}
      />

      <ChatAdvisorDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        activeTicker={selectedTicker}
        onSelectTicker={handleSelectTicker}
        onOpenOrderModal={setOrderModal}
        onNavigateTab={setActiveTab}
      />

      {!isChatOpen && (
        <button
          onClick={() => setIsChatOpen(true)}
          className="fixed bottom-6 right-6 z-40 bg-neutral-900 hover:bg-neutral-800 text-white rounded-full p-2.5 sm:px-4 sm:py-2.5 shadow-2xl flex items-center gap-2.5 transition-all hover:scale-105 cursor-pointer border border-neutral-700 animate-in fade-in"
        >
          <div className="w-7 h-7 rounded-full bg-amber-400 text-neutral-950 font-serif font-bold text-xs flex items-center justify-center">
            WB
          </div>
          <div className="text-left hidden sm:block">
            <div className="text-xs font-serif font-bold text-white flex items-center gap-1.5">
              <span>Guru AI</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            </div>
            <div className="text-[10px] text-neutral-400 font-mono">Doradca Buffetta</div>
          </div>
        </button>
      )}

      <footer className="border-t border-neutral-200 bg-white py-6 text-center text-xs text-neutral-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>BUFFET &bull; Value Investing &amp; AI Engine &bull; przemokoduje.com</span>
          <span className="text-neutral-400">
            Reguła 1: Nigdy nie trać pieniędzy. Reguła 2: Pamiętaj o punkcie 1.
          </span>
        </div>
      </footer>
    </div>
  );
}
