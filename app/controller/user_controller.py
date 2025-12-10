from app.service.user_service import check_level_service, create_user, get_top_level_status, get_user_by_email, forgot_password, level, ranking, reset_monthly_points, rewards, user_by_id, delete_user
from app.models.user import TokenData, UserLogin, UserRegister, UserForgotPassword
from firebase_admin import auth
from fastapi import HTTPException

def login(user: UserLogin):
    try:
        u = auth.get_user_by_email(user.email)
        return {"message": "Usuario autenticado exitosamente", "user_id": u.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def token(token_data: TokenData):
    try:
        decoded_token = auth.verify_id_token(token_data.id_token)
        uid = decoded_token.get("uid") or decoded_token.get("sub")
        if not uid:
            raise HTTPException(status_code=400, detail="Token inválido: uid ausente")
        return {"message": "Token verificado", "user_id": uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Token no válido o expirado")

def register(user: UserRegister, auth_user):
    
    token = auth_user.get("uid") or auth_user.get("sub") or auth_user.get("user_id")
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    if user.uid != token:
        raise HTTPException(status_code=403, detail="User ID does not match token")
    try:
        firebase_user = auth.get_user(user.uid)
        user_email = firebase_user.email
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not retrieve user from Firebase Auth: {str(e)}")

    db_user = user_by_id(user.uid)
    
    if db_user and "error" not in db_user:
        raise HTTPException(status_code=400, detail="User already registered")
    
    if db_user and "error" in db_user:
        raise HTTPException(status_code=500, detail=db_user["error"])
    
    response = create_user(user)
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
    
    return {"message": "User registered successfully"}


def handle_forgot_password(user: UserForgotPassword):
    response = forgot_password(user.email)
    
    if "error" in response:
        if response["error"] == "Email not found":
            raise HTTPException(status_code=404, detail="Email not found")
        else:
            raise HTTPException(status_code=500, detail=response["error"])
    
    return response

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
            # Manejo específico de error de órdenes activas
            if response["error"] == "ACTIVE_ORDERS":
                raise HTTPException(
                    status_code=400,
                    detail=f"You have {response['count']} active order(s) in progress. Please complete or reassign them before deleting your account."
                )
            # Otros errores
            raise HTTPException(status_code=500, detail=response["error"])
        
        return response
        
    except HTTPException:
        raise
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
    
def check_level_user_controller(uid: str):
    try:
        if not uid:
            raise HTTPException(400, "No UID provided")

        response = check_level_service(uid)

        if isinstance(response, dict) and "error" in response:
            raise HTTPException(404, response["error"])

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


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
