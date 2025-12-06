from fastapi import Header, HTTPException
from firebase_admin import auth

async def verify_token(authorization: str = Header(...)):
    try:
        # Separar esquema y token
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Esquema de autenticación inválido.")

        # Verificar el token con Firebase Admin
        decoded_token = auth.verify_id_token(token)

        # Obtener UID
        uid = decoded_token.get("uid") or decoded_token.get("user_id")

        # Armar respuesta básica
        out = {**decoded_token, "uid": uid}

        print("verify_token | uid:", uid)  # opcional para debug

        return out

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token no válido o expirado: {str(e)}"
        )
