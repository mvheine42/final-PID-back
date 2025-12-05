from app.service.user_service import check_level_service, create_user, get_top_level_status, get_user_by_email, forgot_password, level, ranking, reset_monthly_points, rewards, user_by_id, delete_user
from app.models.user import TokenData, UserLogin, UserRegister, UserForgotPassword
from firebase_admin import auth
from fastapi import HTTPException

def login(user: UserLogin):
    try:
        # Verificar las credenciales del usuario
        user = auth.get_user_by_email(user.email)
        return {"message": "Usuario autenticado exitosamente", "user_id": user.uid}
    except firebase_admin.auth.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def token(token_data: TokenData):
    try:
        # Verificar el token enviado por el cliente
        decoded_token = auth.verify_id_token(token_data.id_token)
        uid = decoded_token['uid']
        if not uid:
            raise HTTPException(status_code=400, detail="Token inválido")
        return {"message": "Token verificado", "user_id": uid}
    except firebase_admin.auth.AuthError as e:
        raise HTTPException(status_code=400, detail="Token no válido o expirado")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Controlador para registrar un nuevo usuario
def register(user: UserRegister, auth_user):
    token = auth_user.get("uid") or auth_user.get("sub") or auth_user.get("user_id")
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    if user.uid != token:
        raise HTTPException(status_code=403, detail="User ID does not match token")
    #verify if repeated email
    db_user = get_user_by_email(user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already in use")
    response = create_user(user)
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
    return {"message": "User registered successfully"}

# Controlador para recuperación de contraseña
def handle_forgot_password(user: UserForgotPassword):
    db_user = get_user_by_email(user.email)
    if db_user:
        return forgot_password(user.email)
    else:
        raise HTTPException(status_code=404, detail="Email not found")

def get_user_by_id(uid: str, user):
    try:
        token = (user.get("uid") or user.get("sub") or user.get("user_id") or "").strip()
        if not token or uid != token:
            raise HTTPException(status_code=403, detail="Forbidden: Cannot access other user's data")
        response = user_by_id(uid)
        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
        if not response:
            raise HTTPException(status_code=404, detail="User not found")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def delete_user_by_id(uid: str, user):
    try:
        token = (user.get("uid") or user.get("sub") or user.get("user_id") or "").strip()
        if not token or uid != token:
            raise HTTPException(status_code=403, detail="Forbidden: Cannot access other user's data")
        response = delete_user(uid)
        if "error" in response:            
            raise HTTPException(status_code=500, detail=response["error"])
        return response
    except Exception as e:    
        raise HTTPException(status_code=500, detail=str(e))

def ranking_controller():
    try: 
        response = ranking()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def rewards_controller(level_id: str):
    try: 
        response = rewards(level_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def level_controller(level_id: str):
    try:
        response = level(level_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def check_level_controller(user):
    try:
        token = (user.get("uid") or user.get("sub") or user.get("user_id") or "").strip()
        
        if not token:
            raise HTTPException(status_code=403, detail="Forbidden: No user ID found")
        
        response = check_level_service(token)
        
        # Check if the response contains an error
        if isinstance(response, dict) and "error" in response:
            raise HTTPException(status_code=404, detail=response["error"])
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_top_level_status_controller(level_id: str):
    try:
        response = get_top_level_status(level_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def reset_monthly_points_controller():
    try:
        response = reset_monthly_points()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
