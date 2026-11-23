import React from 'react';
import { ShieldCheck, TrendingUp, Layers, Settings, Compass, Sparkles, Cloud, CloudCheck, User, LogOut, LogIn } from 'lucide-react';

export default function Header({
  activeTab,
  setActiveTab,
  activeProvider,
  user,
  onOpenAuth,
  onLogout,
  syncStatus = 'synced', // 'synced', 'syncing', 'local'
  onManualSync
}) {
  const tabs = [
    { id: 'portfolio', label: 'Portfel Demo (Audyt 1R)', icon: TrendingUp },
    { id: 'screener', label: 'Screener Buffetta', icon: Compass },
    { id: 'deepdive', label: 'Karta Wyceny & AI', icon: Sparkles },
    { id: 'settings', label: 'Dostawcy & Koszty', icon: Settings },
  ];

  return (
    <header className="border-b border-neutral-200 bg-white sticky top-0 z-30">
      {/* Top Banner: Motto Buffetta + Firebase Sync Status */}
      <div className="bg-neutral-900 text-white py-1.5 px-4 text-xs font-mono tracking-tight flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="bg-amber-400 text-neutral-950 px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase">
            Reguła Buffetta
          </span>
          <span className="font-medium text-neutral-200 truncate">
            1. Nigdy nie trać pieniędzy. 2. Zawsze pamiętaj o punkcie pierwszym.
          </span>
        </div>

        {/* Firebase Cloud Sync status */}
        <div className="flex items-center gap-3 text-neutral-400 text-[11px]">
          {user ? (
            <div className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-medium">Firebase Cloud: Zsynchronizowano</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-neutral-400">
              <span className="w-1.5 h-1.5 rounded-full bg-neutral-500"></span>
              <span>Tryb Lokalny (Gość)</span>
            </div>
          )}
          <span className="text-neutral-600 hidden sm:inline">|</span>
          <span className="text-amber-400/90 font-medium hidden sm:inline">przemokoduje.com / cz. 4</span>
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

        {/* Tab Navigation & User Session */}
        <div className="flex items-center gap-2 sm:gap-4">
          <nav className="flex space-x-1 sm:space-x-1.5">
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

          {/* User Auth Chip */}
          <div className="border-l border-neutral-200 pl-2 sm:pl-3 ml-1 flex items-center">
            {user ? (
              <div className="flex items-center gap-2">
                <div
                  title={`Zalogowany jako: ${user.email}`}
                  className="flex items-center gap-1.5 bg-neutral-100 hover:bg-neutral-200 text-neutral-800 border border-neutral-300 px-2.5 py-1.5 rounded-lg text-xs font-mono transition-colors"
                >
                  <div className="w-4 h-4 rounded-full bg-neutral-900 text-white text-[10px] flex items-center justify-center font-bold">
                    {(user.displayName || user.email || 'U')[0].toUpperCase()}
                  </div>
                  <span className="max-w-[100px] truncate hidden md:inline font-sans font-medium">
                    {user.displayName || user.email?.split('@')[0]}
                  </span>
                </div>
                <button
                  onClick={onLogout}
                  title="Wyloguj się"
                  className="p-1.5 text-neutral-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenAuth}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium rounded-lg transition-all shadow-xs cursor-pointer"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Zaloguj się</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
