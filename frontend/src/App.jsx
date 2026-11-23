import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PortfolioView from './components/PortfolioView';
import ScreenerView from './components/ScreenerView';
import DeepDiveView from './components/DeepDiveView';
import SettingsView from './components/SettingsView';
import TradeOrderModal from './components/TradeOrderModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('portfolio');
  const [activeProvider, setActiveProvider] = useState('yfinance');
  const [selectedTicker, setSelectedTicker] = useState('BRK.B');
  const [orderModal, setOrderModal] = useState(null);
  const [tradeNotice, setTradeNotice] = useState(null);

  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [portfolioRefreshing, setPortfolioRefreshing] = useState(false);

  const [screenerData, setScreenerData] = useState(null);
  const [screenerLoading, setScreenerLoading] = useState(true);
  const [screenerScanning, setScreenerScanning] = useState(false);
  const [alertsChecking, setAlertsChecking] = useState(false);

  const fetchPortfolio = (silent = false) => {
    if (!silent) setPortfolioLoading(true);
    fetch('/api/portfolio')
      .then((res) => res.json())
      .then((data) => {
        setPortfolioSummary(data);
        setPortfolioLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setPortfolioLoading(false);
      });
  };

  const handleRefreshPortfolio = async () => {
    setPortfolioRefreshing(true);
    try {
      const res = await fetch('/api/portfolio/refresh', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setPortfolioSummary(data);
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
    fetchPortfolio(true);
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
    fetchPortfolio(true);
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

      <footer className="border-t border-neutral-200 bg-white py-6 text-center text-xs text-neutral-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>BUFFET &bull; Value Investing & AI Engine &bull; przemokoduje.com</span>
          <span className="text-neutral-400">
            Reguła 1: Nigdy nie trać pieniędzy. Reguła 2: Pamiętaj o punkcie 1.
          </span>
        </div>
      </footer>
    </div>
  );
}
