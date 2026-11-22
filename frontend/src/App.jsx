import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PortfolioView from './components/PortfolioView';
import ScreenerView from './components/ScreenerView';
import DeepDiveView from './components/DeepDiveView';
import SettingsView from './components/SettingsView';

export default function App() {
  const [activeTab, setActiveTab] = useState('portfolio');
  const [activeProvider, setActiveProvider] = useState('mock');
  const [selectedTicker, setSelectedTicker] = useState('BRK.B');

  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);

  const [screenerData, setScreenerData] = useState(null);
  const [screenerLoading, setScreenerLoading] = useState(true);

  // Pobierz dane portfela
  const fetchPortfolio = () => {
    setPortfolioLoading(true);
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

  // Pobierz dane screenera
  const fetchScreener = () => {
    setScreenerLoading(true);
    fetch(`/api/screener?provider_name=${activeProvider}`)
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

  // Pobierz ustawienia i początkowe dane
  useEffect(() => {
    fetch('/api/settings')
      .then((res) => res.json())
      .then((data) => {
        setActiveProvider(data.active_data_provider);
      })
      .catch(console.error);

    fetchPortfolio();
    fetchScreener();
  }, []);

  // Odśwież screener przy zmianie dostawcy
  useEffect(() => {
    fetchScreener();
  }, [activeProvider]);

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

  const handleAddToDemo = async (ticker) => {
    const res = await fetch(`/api/analysis/${ticker}/add-to-demo`, { method: 'POST' });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Błąd zapisu');
    fetchPortfolio();
    return json;
  };

  const handleRemoveHolding = async (holdingId) => {
    if (!window.confirm('Czy na pewno chcesz zamknąć tę pozycję w portfelu demo?')) return;
    try {
      await fetch(`/api/portfolio/${holdingId}`, { method: 'DELETE' });
      fetchPortfolio();
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateProvider = (newProvider) => {
    setActiveProvider(newProvider);
  };

  return (
    <div className="min-h-screen bg-[#fcfcfc] text-[#171717] flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeProvider={activeProvider}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        {activeTab === 'portfolio' && (
          <PortfolioView
            summary={portfolioSummary}
            loading={portfolioLoading}
            onSelectTicker={handleSelectTicker}
            onRemoveHolding={handleRemoveHolding}
          />
        )}

        {activeTab === 'screener' && (
          <ScreenerView
            screenerData={screenerData}
            loading={screenerLoading}
            activeProvider={activeProvider}
            onSelectTicker={handleSelectTicker}
            onScanCustom={handleScanCustom}
          />
        )}

        {activeTab === 'deepdive' && (
          <DeepDiveView
            ticker={selectedTicker}
            onAddToDemo={handleAddToDemo}
            onBackToScreener={() => setActiveTab('screener')}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsView
            activeProvider={activeProvider}
            onUpdateProvider={handleUpdateProvider}
          />
        )}
      </main>

      {/* Minimalist Footer */}
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
