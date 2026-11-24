import { initializeApp, getApps, getApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  updateProfile
} from "firebase/auth";
import {
  getFirestore,
  doc,
  setDoc,
  getDoc,
  serverTimestamp
} from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.projectId
);

let app = null;
let auth = null;
let db = null;
let googleProvider = null;

if (isFirebaseConfigured) {
  try {
    app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
    auth = getAuth(app);
    db = getFirestore(app);
    googleProvider = new GoogleAuthProvider();
  } catch (err) {
    console.warn("[Firebase] Nie udało się zainicjalizować Firebase — tryb lokalny:", err);
    app = null;
    auth = null;
    db = null;
    googleProvider = null;
  }
} else {
  console.info("[Firebase] Brak zmiennych VITE_FIREBASE_* w frontend/.env — uruchomiono w trybie lokalnym (Gość).");
}

export { app, auth, db, googleProvider };

function requireAuth() {
  if (!auth) {
    throw new Error("Brak konfiguracji Firebase (frontend/.env). Aplikacja działa obecnie w trybie lokalnym.");
  }
  return auth;
}

// Funkcje autoryzacji
export async function loginWithGoogle() {
  const a = requireAuth();
  const result = await signInWithPopup(a, googleProvider);
  return result.user;
}

export async function loginWithEmail(email, password) {
  const a = requireAuth();
  const result = await signInWithEmailAndPassword(a, email, password);
  return result.user;
}

export async function registerWithEmail(email, password, displayName) {
  const a = requireAuth();
  const result = await createUserWithEmailAndPassword(a, email, password);
  if (displayName && result.user) {
    await updateProfile(result.user, { displayName });
  }
  return result.user;
}

export async function logoutUser() {
  if (!auth) return;
  await signOut(auth);
}

export function subscribeToAuthChanges(callback) {
  if (!auth) {
    callback(null);
    return () => {};
  }
  return onAuthStateChanged(auth, callback);
}

// Kolekcja w Firestore: buffet_users/{uid}
const COLLECTION_NAME = "buffet_users";

/**
 * Zapisuje kompletny stan portfela i ustawień użytkownika w Google Cloud Firestore.
 */
export async function saveUserDataToFirebase(userId, userData) {
  if (!userId || !db) return { success: false, error: "Tryb lokalny (brak konfiguracji Firebase)" };
  try {
    const userDocRef = doc(db, COLLECTION_NAME, userId);
    const payload = {
      ...userData,
      lastSyncedAt: new Date().toISOString(),
      updatedAtServer: serverTimestamp()
    };
    await setDoc(userDocRef, payload, { merge: true });
    return { success: true, timestamp: new Date().toISOString() };
  } catch (error) {
    console.error("[Firebase Firestore] Błąd zapisu danych użytkownika:", error);
    return { success: false, error: error.message };
  }
}

/**
 * Pobiera zapisany stan użytkownika z Google Cloud Firestore.
 */
export async function loadUserDataFromFirebase(userId) {
  if (!userId || !db) return null;
  try {
    const userDocRef = doc(db, COLLECTION_NAME, userId);
    const snap = await getDoc(userDocRef);
    if (snap.exists()) {
      return snap.data();
    }
    return null;
  } catch (error) {
    console.error("[Firebase Firestore] Błąd odczytu danych użytkownika:", error);
    return null;
  }
}
