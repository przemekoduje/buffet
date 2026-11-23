import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore, auth
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class FirebaseService:
    _app: Optional[firebase_admin.App] = None
    _db: Optional[Any] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> bool:
        if cls._initialized:
            return True

        if firebase_admin._apps:
            cls._app = firebase_admin.get_app()
            cls._db = firestore.client()
            cls._initialized = True
            return True

        # Poszukiwanie pliku service account w standardowych lokalizacjach projektu
        candidate_paths = [
            BASE_DIR / "firebase-adminsdk.json",
            BASE_DIR.parent / "keepGoals" / "firebase-adminsdk.json",
            BASE_DIR.parent / "firebase_service_account.json",
            Path(os.getenv("FIREBASE_CREDENTIALS_PATH", "")) if os.getenv("FIREBASE_CREDENTIALS_PATH") else None
        ]

        cred_path = None
        for p in candidate_paths:
            if p and p.exists():
                cred_path = p
                break

        try:
            if cred_path:
                print(f"[Firebase Admin] Inicjalizacja z poświadczeń: {cred_path}")
                cred = credentials.Certificate(str(cred_path))
                cls._app = firebase_admin.initialize_app(cred)
            else:
                print("[Firebase Admin] Brak lokalnego pliku klucza. Próba Default Application Credentials...")
                cls._app = firebase_admin.initialize_app()

            cls._db = firestore.client()
            cls._initialized = True
            print("[Firebase Admin] Połączenie z Google Cloud Firestore nawiązane pomyślnie.")
            return True
        except Exception as e:
            print(f"[Firebase Admin Warning] Nie udało się zainicjalizować Admin SDK: {e}")
            cls._initialized = False
            return False

    @classmethod
    def is_available(cls) -> bool:
        return cls.initialize() and cls._db is not None

    @classmethod
    def verify_token(cls, id_token: str) -> Optional[Dict[str, Any]]:
        """Weryfikuje token użytkownika wygenerowany przez Firebase Client SDK."""
        if not id_token:
            return None
        # Obsługa mock tokenu deweloperskiego
        if id_token.startswith("mock-dev-token-"):
            return {
                "uid": id_token.replace("mock-dev-token-", ""),
                "email": "dev@przemokoduje.com"
            }

        if not cls.initialize():
            return None

        try:
            decoded = auth.verify_id_token(id_token)
            return {
                "uid": decoded.get("uid"),
                "email": decoded.get("email"),
                "name": decoded.get("name")
            }
        except Exception as e:
            print(f"[Firebase Auth Error] Weryfikacja tokenu nie powiodła się: {e}")
            return None

    @classmethod
    def save_user_data(cls, uid: str, data: Dict[str, Any]) -> bool:
        """Zapisuje profil, portfel, zlecenia i watchlistę użytkownika w Firestore."""
        if not cls.initialize() or not cls._db:
            return False
        try:
            doc_ref = cls._db.collection("buffet_users").document(uid)
            doc_ref.set(data, merge=True)
            return True
        except Exception as e:
            print(f"[Firestore Save Error] {e}")
            return False

    @classmethod
    def load_user_data(cls, uid: str) -> Optional[Dict[str, Any]]:
        """Odczytuje kompletny stan użytkownika z Firestore."""
        if not cls.initialize() or not cls._db:
            return None
        try:
            doc_ref = cls._db.collection("buffet_users").document(uid)
            snap = doc_ref.get()
            if snap.exists:
                return snap.to_dict()
            return None
        except Exception as e:
            print(f"[Firestore Load Error] {e}")
            return None
