import React, { useState, useEffect } from 'react';
import { Database, Key, Server, Check, ArrowRight, ShieldCheck, DollarSign } from 'lucide-react';

export default function SettingsView({ activeProvider, onUpdateProvider }) {
  const [settingsData, setSettingsData] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState(activeProvider);
  const [fmpKey, setFmpKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [statusMsg, setStatusMsg] = useState(null);

  useEffect(() => {
    fetch('/api/settings')
      .then((res) => res.json())
      .then((data) => {
        setSettingsData(data);
        setSelectedProvider(data.active_data_provider);
      })
      .catch(console.error);
  }, []);

  const handleSave = async () => {
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data_provider: selectedProvider,
          fmp_api_key: fmpKey || undefined,
          gemini_api_key: geminiKey || undefined
        })
      });
      const json = await res.json();
      onUpdateProvider(json.active_data_provider);
      setStatusMsg('Ustawienia zostały pomyślnie zaktualizowane!');
      setTimeout(() => setStatusMsg(null), 3500);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Overview box */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs">
        <h2 className="text-xl font-serif font-bold text-neutral-900">
          Architektura Danych & Kosztów
        </h2>
        <p className="text-xs text-neutral-600 mt-1 max-w-2xl leading-relaxed">
          Wszystkie wersje aplikacji korzystają z <strong>identycznego interfejsu panelu admina i tego samego silnika matematycznego DCF</strong>.
          Różnica polega wyłącznie na podpiętym adapterze źródła danych (darmowy vs komercyjny) oraz częstotliwości zapytań.
        </p>
      </div>

      {statusMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg">
          {statusMsg}
        </div>
      )}

      {/* Provider Selector Cards */}
      <div className="space-y-3">
        <h3 className="text-xs font-mono uppercase text-neutral-500 font-semibold tracking-wider">
          Wybierz Aktywny Adapter Źródła Danych
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(settingsData?.available_providers || []).map((prov) => {
            const isSelected = selectedProvider === prov.id;
            return (
              <div
                key={prov.id}
                onClick={() => setSelectedProvider(prov.id)}
                className={`border rounded-xl p-4 cursor-pointer transition-all ${
                  isSelected
                    ? 'border-neutral-900 bg-neutral-900 text-white shadow-md'
                    : 'border-neutral-200 bg-white hover:border-neutral-300 text-neutral-900'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded ${
                    isSelected ? 'bg-neutral-800 text-amber-300' : 'bg-neutral-100 text-neutral-700'
                  }`}>
                    {prov.cost}
                  </span>
                  {isSelected && <Check className="w-4 h-4 text-emerald-400" />}
                </div>

                <h4 className="font-serif font-bold text-sm mb-1">{prov.name}</h4>
                <p className={`text-xs ${isSelected ? 'text-neutral-300' : 'text-neutral-500'}`}>
                  {prov.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* API Keys Configuration */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-neutral-100 pb-3">
          <Key className="w-4 h-4 text-neutral-700" />
          <h3 className="text-sm font-serif font-bold text-neutral-900">
            Klucze API (Opcjonalne dla Wersji Średniej i Wyższej)
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block text-neutral-700 font-mono mb-1">Financial Modeling Prep (FMP) Key:</label>
            <input
              type="password"
              placeholder="Wklej klucz FMP (opcjonalnie)"
              value={fmpKey}
              onChange={(e) => setFmpKey(e.target.value)}
              className="w-full border border-neutral-300 rounded px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900"
            />
          </div>

          <div>
            <label className="block text-neutral-700 font-mono mb-1">Gemini API Key (dla AI Memoranda):</label>
            <input
              type="password"
              placeholder="Wklej klucz Gemini AI (opcjonalnie)"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              className="w-full border border-neutral-300 rounded px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900"
            />
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            Zapisz Ustawienia Adaptera
          </button>
        </div>
      </div>
    </div>
  );
}
