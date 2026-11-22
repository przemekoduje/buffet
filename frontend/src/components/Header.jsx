import React from 'react';
import { ShieldCheck, TrendingUp, Layers, Settings, Compass, Sparkles } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, activeProvider }) {
  const tabs = [
    { id: 'portfolio', label: 'Portfel Demo (Audyt 1R)', icon: TrendingUp },
    { id: 'screener', label: 'Screener Buffetta', icon: Compass },
    { id: 'deepdive', label: 'Karta Wyceny & AI', icon: Sparkles },
    { id: 'settings', label: 'Dostawcy & Koszty', icon: Settings },
  ];

  return (
    <header className="border-b border-neutral-200 bg-white sticky top-0 z-30">
      {/* Top Banner: Motto Buffetta */}
      <div className="bg-neutral-900 text-white py-1.5 px-4 text-xs font-mono tracking-tight flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="bg-amber-400 text-neutral-950 px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase">
            Reguła Buffetta
          </span>
          <span className="font-medium text-neutral-200">
            1. Nigdy nie trać pieniędzy. 2. Zawsze pamiętaj o punkcie pierwszym.
          </span>
        </div>
        <div className="hidden sm:flex items-center gap-3 text-neutral-400 text-[11px]">
          <span>Tryb audytu: <strong className="text-neutral-200 uppercase font-sans">{activeProvider}</strong></span>
          <span className="text-neutral-600">|</span>
          <span className="text-amber-400/90 font-medium">przemokoduje.com / cz. 4</span>
        </div>
      </div>

      {/* Main Navbar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('portfolio')}>
          <div className="w-8 h-8 rounded-lg bg-neutral-900 text-white flex items-center justify-center font-serif text-lg font-bold">
            B
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-serif font-bold text-neutral-900 tracking-tight">BUFFET</h1>
              <span className="text-[10px] bg-neutral-100 text-neutral-600 border border-neutral-300 px-1.5 py-0.5 rounded font-mono">
                VALUE & AI
              </span>
            </div>
            <p className="text-[11px] text-neutral-500 hidden sm:block">Inteligentna analiza wartości wewnętrznej spółek</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex space-x-1 sm:space-x-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-neutral-900 text-white shadow-xs'
                    : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
