# app/db/firebase.py
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase():
    if firebase_admin._apps:
        return firestore.client()

    json_env = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if json_env:
        try:
            data = json.loads(json_env)
            cred = credentials.Certificate(data)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        except Exception as e:
            raise RuntimeError(f"FIREBASE_CREDENTIALS_JSON inválida: {e}")

    cred_path = os.getenv("FIREBASE_CRED_PATH")
    if cred_path:
        try:
            if not os.path.isabs(cred_path):
                cred_path = os.path.abspath(cred_path)

            if not os.path.exists(cred_path):
                raise FileNotFoundError(f"No existe archivo de credenciales: {cred_path}")

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return firestore.client()

        except Exception as e:
            raise RuntimeError(f"Error con FIREBASE_CRED_PATH: {e}")

    raise RuntimeError(
        "No hay credenciales Firebase. Definí FIREBASE_CREDENTIALS_JSON (Render) o FIREBASE_CRED_PATH (Local)."
    )

db = init_firebase()
