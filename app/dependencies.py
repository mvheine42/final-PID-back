# app/dependencies.py
from fastapi import Header, HTTPException
from firebase_admin import auth
from app.db.firebase import db

def verify_token(authorization: str = Header(...)):
    try:
        scheme, _, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Esquema de autenticación inválido.")

        decoded_token = auth.verify_id_token(token)

        uid = decoded_token.get("uid") or decoded_token.get("user_id")
        role = decoded_token.get("role")

        # Si el token no trae role, lo buscamos en Firestore
        if not role and uid:
            try:
                doc = db.collection("users").document(str(uid)).get()
                if doc.exists:
                    role = (doc.to_dict() or {}).get("role")
            except:
                pass

        role_norm = (str(role).strip().upper()) if role else None

        return {
            **decoded_token,
            "uid": uid,
            "role": role_norm
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token no válido o expirado: {str(e)}")
