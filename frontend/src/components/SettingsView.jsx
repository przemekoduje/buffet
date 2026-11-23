import React, { useState, useEffect } from 'react';
import { Key, Check, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

export default function SettingsView({ activeProvider, onUpdateProvider }) {
  const [settingsData, setSettingsData] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState(activeProvider);
  const [fmpKey, setFmpKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-flash-lite-latest');
  const [statusMsg, setStatusMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [saving, setSaving] = useState(false);

  const loadSettings = () => {
    fetch('/api/settings')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setErrorMsg(null);
        setSettingsData(data);
        setSelectedProvider(data.active_data_provider);
        if (data.gemini_model) setGeminiModel(data.gemini_model);
      })
      .catch((err) => {
        console.error(err);
        setErrorMsg('Brak połączenia z serwerem API (/api/settings). Sprawdź, czy działają backend (port 8000) oraz frontend (port 5173).');
      });
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data_provider: selectedProvider,
          fmp_api_key: fmpKey || undefined,
          gemini_api_key: geminiKey || undefined,
          gemini_model: geminiModel,
        }),
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || `HTTP ${res.status}`);
      }
      const json = await res.json();
      onUpdateProvider(json.active_data_provider);
      setFmpKey('');
      setGeminiKey('');
      loadSettings();
      setStatusMsg('Ustawienia zapisane na stałe w backend/.env i aktywowane!');
      setTimeout(() => setStatusMsg(null), 4000);
    } catch (e) {
      console.error(e);
      setErrorMsg(`Nie udało się zapisać ustawień: ${e.message || 'brak połączenia z backendem'}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Overview box */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs">
        <h2 className="text-xl font-serif font-bold text-neutral-900">
          Architektura Danych & Silnik AI
        </h2>
        <p className="text-xs text-neutral-600 mt-1 max-w-2xl leading-relaxed">
          Wszystkie wersje aplikacji korzystają z <strong>identycznego interfejsu i tego samego silnika matematycznego DCF</strong>.
          Domyślnie aktywny jest realny dostawca <strong>Yahoo Finance (yfinance)</strong>, a po dodaniu klucza Gemini AI generuje żywe memoriały inwestycyjne.
        </p>
      </div>

      {statusMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg">
          {statusMsg}
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-800 text-xs rounded-lg">
          {errorMsg}
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
                className={`border rounded-xl p-4 cursor-pointer transition-all ${isSelected
                    ? 'border-neutral-900 bg-neutral-900 text-white shadow-md'
                    : 'border-neutral-200 bg-white hover:border-neutral-300 text-neutral-900'
                  }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span
                    className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded ${isSelected ? 'bg-neutral-800 text-amber-300' : 'bg-neutral-100 text-neutral-700'
                      }`}
                  >
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

      {/* API Keys & AI Engine Configuration */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-neutral-700" />
            <h3 className="text-sm font-serif font-bold text-neutral-900">
              Klucze API & Konfiguracja Gemini AI
            </h3>
          </div>
          <div className="flex items-center gap-2 text-[11px] font-mono">
            {settingsData?.has_gemini_key ? (
              <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                <CheckCircle2 className="w-3 h-3" /> Gemini AI: AKTYWNY ({settingsData.gemini_model})
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                <AlertCircle className="w-3 h-3" /> Gemini AI: brak klucza
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block text-neutral-700 font-mono mb-1 flex items-center justify-between">
              <span>Gemini API Key (AI Memoranda):</span>
              {settingsData?.has_gemini_key && (
                <span className="text-[10px] text-emerald-700">zapisany</span>
              )}
            </label>
            <input
              type="password"
              placeholder={settingsData?.has_gemini_key ? '•••••••• (zapisany — wpisz nowy, aby nadpisać)' : 'Wklej klucz z aistudio.google.com'}
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              className="w-full border border-neutral-300 rounded px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900"
            />
          </div>

          <div>
            <label className="block text-neutral-700 font-mono mb-1 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-600" />
              <span>Model Gemini AI:</span>
            </label>
            <select
              value={geminiModel}
              onChange={(e) => setGeminiModel(e.target.value)}
              className="w-full border border-neutral-300 rounded px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900 bg-white"
            >
              <option value="gemini-flash-lite-latest">gemini-flash-lite-latest (Szybki, rekomendowany)</option>
              <option value="gemini-3.5-flash-lite">gemini-3.5-flash-lite (Stabilny, szybki)</option>
              <option value="gemini-3.5-flash">gemini-3.5-flash (Pełny Flash)</option>
              <option value="gemini-3.8-flash">gemini-3.8-flash (Najnowszy — bywa przeciążony)</option>
            </select>
          </div>

          <div className="sm:col-span-2">
            <label className="block text-neutral-700 font-mono mb-1 flex items-center justify-between">
              <span>Financial Modeling Prep (FMP) Key (opcjonalnie):</span>
              {settingsData?.has_fmp_key && (
                <span className="text-[10px] text-emerald-700">zapisany</span>
              )}
            </label>
            <input
              type="password"
              placeholder={settingsData?.has_fmp_key ? '•••••••• (zapisany — wpisz nowy, aby nadpisać)' : 'Wklej klucz FMP (tylko jeśli wybierasz adapter FMP)'}
              value={fmpKey}
              onChange={(e) => setFmpKey(e.target.value)}
              className="w-full border border-neutral-300 rounded px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900"
            />
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            {saving ? 'Zapisywanie...' : 'Zapisz Ustawienia Adaptera & AI'}
          </button>
        </div>
      </div>
    </div>
  );
}
