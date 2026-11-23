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

// Inicjalizacja Firebase App (singleton)
export const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();

// Funkcje autoryzacji
export async function loginWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider);
  return result.user;
}

export async function loginWithEmail(email, password) {
  const result = await signInWithEmailAndPassword(auth, email, password);
  return result.user;
}

export async function registerWithEmail(email, password, displayName) {
  const result = await createUserWithEmailAndPassword(auth, email, password);
  if (displayName && result.user) {
    await updateProfile(result.user, { displayName });
  }
  return result.user;
}

export async function logoutUser() {
  await signOut(auth);
}

export function subscribeToAuthChanges(callback) {
  return onAuthStateChanged(auth, callback);
}

// Kolekcja w Firestore: buffet_users/{uid}
const COLLECTION_NAME = "buffet_users";

/**
 * Zapisuje kompletny stan portfela i ustawień użytkownika w Google Cloud Firestore.
 */
export async function saveUserDataToFirebase(userId, userData) {
  if (!userId || !db) return { success: false, error: "Brak identyfikatora użytkownika" };
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
