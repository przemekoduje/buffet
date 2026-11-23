import React, { useState, useEffect } from 'react';
import { Key, Check, Sparkles, CheckCircle2, AlertCircle, Cloud, LogIn, RefreshCw } from 'lucide-react';

export default function SettingsView({
  activeProvider,
  onUpdateProvider,
  user,
  onOpenAuth,
  onManualSync,
  lastSyncTime
}) {
  const [settingsData, setSettingsData] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState(activeProvider);
  const [fmpKey, setFmpKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-flash-lite-latest');
  const [statusMsg, setStatusMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [manualSyncing, setManualSyncing] = useState(false);

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

  const handleManualSyncClick = async () => {
    if (!onManualSync) return;
    setManualSyncing(true);
    await onManualSync();
    setManualSyncing(false);
    setStatusMsg('Dane użytkownika zostały pomyślnie zapisane w Google Cloud Firestore!');
    setTimeout(() => setStatusMsg(null), 4000);
  };

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
    <div className="space-y-6 max-w-4xl mx-auto font-sans">
      {/* Overview box */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs">
        <h2 className="text-xl font-serif font-bold text-neutral-900">
          Architektura Danych &amp; Chmura Firebase
        </h2>
        <p className="text-xs text-neutral-600 mt-1 max-w-2xl leading-relaxed">
          Wszystkie wersje aplikacji korzystają z <strong>identycznego interfejsu i tego samego silnika matematycznego DCF</strong>.
          Domyślnie aktywny jest realny dostawca <strong>Yahoo Finance (yfinance)</strong>, a dane portfela każdego użytkownika są synchronizowane z bazą <strong>Google Cloud Firestore</strong>.
        </p>
      </div>

      {statusMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{statusMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-800 text-xs rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Google Firebase Cloud Sync Card */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <Cloud className="w-4 h-4 text-emerald-600" />
            <h3 className="text-sm font-serif font-bold text-neutral-900">
              Google Firebase — Zapis Danych Użytkownika na Serwerze
            </h3>
          </div>
          <span className="text-[11px] font-mono text-neutral-500">
            Kolekcja: <code className="bg-neutral-100 px-1 py-0.5 rounded text-neutral-800">buffet_users</code>
          </span>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-neutral-50 border border-neutral-200">
          <div>
            <div className="text-xs font-medium text-neutral-900 flex items-center gap-2">
              {user ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span>Zalogowany jako: <strong>{user.email}</strong> {user.displayName ? `(${user.displayName})` : ''}</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-neutral-400"></span>
                  <span>Niezalogowany — Aktywny <strong>Tryb Lokalny (Gość)</strong></span>
                </>
              )}
            </div>
            <p className="text-[11px] text-neutral-500 mt-1">
              {user
                ? `UID: ${user.uid} • Ostatnia synchronizacja: ${lastSyncTime || 'chwilę temu'}`
                : 'Zaloguj się kontem Google lub email, aby Twój portfel Paper Trading, zlecenia i ustawienia były zawsze bezpiecznie zapisane na serwerze.'}
            </p>
          </div>

          <div>
            {user ? (
              <button
                type="button"
                onClick={handleManualSyncClick}
                disabled={manualSyncing}
                className="px-3.5 py-2 bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${manualSyncing ? 'animate-spin' : 'text-emerald-400'}`} />
                <span>{manualSyncing ? 'Zapisywanie...' : 'Zsynchronizuj teraz'}</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onOpenAuth}
                className="px-3.5 py-2 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Zaloguj się</span>
              </button>
            )}
          </div>
        </div>
      </div>

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

      {/* API Keys Configuration */}
      <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-neutral-100 pb-3">
          <Key className="w-4 h-4 text-neutral-700" />
          <h3 className="text-sm font-serif font-bold text-neutral-900">
            Klucze API (Google Gemini AI &amp; FMP)
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block text-neutral-700 font-mono mb-1 flex items-center justify-between">
              <span>Google Gemini API Key:</span>
              {settingsData?.has_gemini_key && (
                <span className="text-[10px] text-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> zapisany
                </span>
              )}
            </label>
            <input
              type="password"
              placeholder={settingsData?.has_gemini_key ? '•••••••• (zapisany — wpisz nowy, aby nadpisać)' : 'AIzaSy... (darmowy klucz z Google AI Studio)'}
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              className="w-full border border-neutral-300 rounded px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900"
            />
          </div>

          <div>
            <label className="block text-neutral-700 font-mono mb-1">
              Model Gemini (szybki, stabilny &amp; tani):
            </label>
            <select
              value={geminiModel}
              onChange={(e) => setGeminiModel(e.target.value)}
              className="w-full border border-neutral-300 rounded px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900 bg-white"
            >
              <option value="gemini-flash-lite-latest">gemini-flash-lite-latest (Zalecany, bez 503)</option>
              <option value="gemini-3.5-flash-lite">gemini-3.5-flash-lite</option>
              <option value="gemini-3.5-flash">gemini-3.5-flash</option>
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
