import os
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin

def init_firebase():
    cred_path = os.getenv("FIREBASE_CRED_PATH")
    if not cred_path:
        raise ValueError("❌ No se encontró la variable FIREBASE_CRED_PATH. Definila antes de iniciar FastAPI.")

    # Evita reinicializar Firebase cuando FastAPI hace reload
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
        print(f"✅ Firebase inicializado con credencial: {cred_path}")
    else:
        print("⚠️ Firebase ya estaba inicializado.")

    return firestore.client()

db = init_firebase()
