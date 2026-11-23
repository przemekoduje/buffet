import React, { useState } from 'react';
import { X, Mail, Lock, User, AlertCircle, CheckCircle2, Shield, LogIn } from 'lucide-react';
import { loginWithGoogle, loginWithEmail, registerWithEmail } from '../config/firebase';

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const user = await loginWithGoogle();
      if (onAuthSuccess) onAuthSuccess(user);
      onClose();
    } catch (err) {
      console.error(err);
      setError(err.message || 'Błąd logowania przez konto Google.');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Podaj adres email oraz hasło.');
      return;
    }
    if (password.length < 6) {
      setError('Hasło musi zawierać co najmniej 6 znaków.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      let user;
      if (isRegister) {
        user = await registerWithEmail(email, password, displayName);
      } else {
        user = await loginWithEmail(email, password);
      }
      if (onAuthSuccess) onAuthSuccess(user);
      onClose();
    } catch (err) {
      console.error(err);
      if (err.code === 'auth/user-not-found' || err.code === 'auth/wrong-password' || err.code === 'auth/invalid-credential') {
        setError('Nieprawidłowy adres email lub hasło.');
      } else if (err.code === 'auth/email-already-in-use') {
        setError('Ten adres email jest już zarejestrowany. Zaloguj się.');
      } else {
        setError(err.message || 'Wystąpił błąd autoryzacji.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="bg-white border border-neutral-200 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-100 flex items-center justify-between bg-neutral-50/50">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-neutral-900 text-white flex items-center justify-center font-serif text-sm font-bold">
              B
            </div>
            <div>
              <h3 className="text-sm font-serif font-bold text-neutral-900">
                {isRegister ? 'Utwórz Konto w BUFFET' : 'Zaloguj się do BUFFET'}
              </h3>
              <p className="text-[11px] text-neutral-500 font-sans">
                Synchronizacja portfela &amp; predykcji w Google Firebase
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-700 p-1 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-4 text-xs font-sans">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Google Button */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 py-2.5 px-4 border border-neutral-300 hover:border-neutral-400 bg-white hover:bg-neutral-50 text-neutral-800 rounded-xl font-medium transition-all shadow-xs cursor-pointer disabled:opacity-50"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Kontynuuj przez Google</span>
          </button>

          <div className="relative flex items-center justify-center">
            <div className="border-t border-neutral-200 w-full"></div>
            <span className="bg-white px-3 text-[11px] text-neutral-400 font-mono uppercase">lub email</span>
          </div>

          {/* Email / Password Form */}
          <form onSubmit={handleEmailAuth} className="space-y-3">
            {isRegister && (
              <div>
                <label className="block text-[11px] font-mono text-neutral-600 mb-1">Twoje Imię / Nick</label>
                <div className="relative">
                  <User className="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="np. Warren B."
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 border border-neutral-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-neutral-900"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-[11px] font-mono text-neutral-600 mb-1">Adres Email</label>
              <div className="relative">
                <Mail className="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  placeholder="twoj@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-neutral-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-neutral-900"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-mono text-neutral-600 mb-1">Hasło</label>
              <div className="relative">
                <Lock className="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  placeholder="Minimum 6 znaków"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-neutral-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-neutral-900"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-neutral-900 hover:bg-neutral-800 text-white rounded-xl font-medium transition-colors cursor-pointer disabled:opacity-50 mt-1"
            >
              {loading ? 'Przetwarzanie...' : (isRegister ? 'Zarejestruj i utwórz portfel' : 'Zaloguj się')}
            </button>
          </form>

          {/* Switch Register/Login */}
          <div className="text-center pt-1">
            <button
              type="button"
              onClick={() => { setIsRegister(!isRegister); setError(null); }}
              className="text-neutral-500 hover:text-neutral-900 text-[11px] underline cursor-pointer"
            >
              {isRegister ? 'Masz już konto? Zaloguj się' : 'Nie masz konta? Zarejestruj się bezpłatnie'}
            </button>
          </div>
        </div>

        {/* Footer info */}
        <div className="px-6 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between text-[11px] text-neutral-500">
          <span className="flex items-center gap-1">
            <Shield className="w-3 h-3 text-emerald-600" />
            Szyfrowanie Google Firebase
          </span>
          <button
            type="button"
            onClick={onClose}
            className="hover:text-neutral-800 font-medium cursor-pointer"
          >
            Kontynuuj jako Gość
          </button>
        </div>
      </div>
    </div>
  );
}
