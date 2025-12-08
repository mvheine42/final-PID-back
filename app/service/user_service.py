from http.client import HTTPException
from app.db.firebase import db
import firebase_admin
from firebase_admin import auth 

# Crear un nuevo usuario en Firestore
def create_user(user_data):
    try:
        doc_ref = db.collection("users").document(user_data.uid)
        doc_ref.set({
            "name": user_data.name,
            "birthday": user_data.birthday,
            "imageUrl": user_data.imageUrl,
            "level": "1",
            "globalPoints": "0",
            "monthlyPoints": "0"
        })
        return {"message": "User data saved successfully"}
    except Exception as e:
        print(f"Error creating user: {str(e)}")  # Add logging
        return {"error": str(e)}

# Obtener un usuario por su email
def get_user_by_email(email):
    try:
        user = auth.get_user_by_email(email)
        return {"uid": user.uid, "email": user.email}  # Retorna el UID del usuario
    except firebase_admin.auth.UserNotFoundError:
        return None
    except Exception as e:
        return {"error": str(e)}
    

# Función para manejar la recuperación de contraseña
def forgot_password(email):
    try:
        # Check if user exists in Firebase Auth
        auth.get_user_by_email(email)
        # Generate password reset link
        reset_link = auth.generate_password_reset_link(email)
        # In production, you would send this link via email
        return {"message": "Password reset link sent", "link": reset_link}
    except firebase_admin.auth.UserNotFoundError:
        return {"error": "Email not found"}
    except Exception as e:
        return {"error": str(e)}
    
def user_by_id(uid):
    try:
        # Referencia al documento del usuario
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()  # Obtener el documento
        
        if user_doc.exists:  # Verificar si el documento existe
            user_data = user_doc.to_dict()  # Obtener datos como un diccionario
            
            # Obtener el nivel del usuario
            level_id = user_data.get("level")
            if level_id:
                # Referencia al documento del nivel
                level_ref = db.collection('levels').document(level_id)
                level_doc = level_ref.get()  # Obtener el documento del nivel
                
                if level_doc.exists:  # Verificar si el documento del nivel existe
                    level_data = level_doc.to_dict()  # Obtener datos del nivel
                    # Crear una lista que contenga el ID y el nombre del nivel
                    user_data['level'] = {
                        'id': level_id,  # ID del nivel
                        'name': level_data.get("name")  # Nombre del nivel
                    }
            
            return user_data  # Retornar los datos del usuario, ahora con el nivel incluido
        else:
            return None  # Usuario no existe - esto es normal durante el registro
    except Exception as e:
        return {"error": str(e)}


def delete_user(uid):
    try:
        # Verificar órdenes activas
        orders_ref = db.collection("orders")
        active_orders = list(
            orders_ref.where("employee", "==", uid)
                     .where("status", "==", "IN PROGRESS")
                     .stream()
        )
        
        if len(active_orders) > 0:
            return {"error": "ACTIVE_ORDERS", "count": len(active_orders)}
        
        # Eliminar usuario
        auth.delete_user(uid)
        user_ref = db.collection('users').document(uid)
        user_ref.delete()
        
        return {"message": "User deleted successfully"}
        
    except Exception as e:
        return {"error": str(e)}

def ranking():
    try:
        user_ref = db.collection('users')
        users = user_ref.stream()
        user_data = sorted(
            [
                {
                    "name": user.get("name"),
                    "imageUrl": user.get("imageUrl"),
                    "monthlyPoints": int(user.get("monthlyPoints"))
                }
                for user in users
            ],
            key=lambda x: x["monthlyPoints"],
            reverse=True
        )

        return user_data
    except Exception as e:
        return {"error": str(e)}

def rewards(level_id):
    try:
        # Referencia al documento del nivel
        level_ref = db.collection('levels').document(level_id)
        level_doc = level_ref.get()  # Obtener el documento del nivel
        
        if level_doc.exists:  # Verificar si el nivel existe
            level_data = level_doc.to_dict()
            rewards_ids = level_data.get("rewards", "").split(", ")  # Obtener y dividir los IDs de rewards
            
            rewards_list = []  # Lista para almacenar los datos de cada recompensa
            for reward_id in rewards_ids:
                # Referencia al documento de cada recompensa
                reward_ref = db.collection('rewards').document(reward_id)
                reward_doc = reward_ref.get()
                
                if reward_doc.exists:  # Verificar si la recompensa existe
                    rewards_list.append(reward_doc.to_dict())  # Agregar los datos de la recompensa a la lista
            
            return rewards_list # Retornar las recompensas como un diccionario
        else:
            return {"error": "Level not found"}
    except Exception as e:
        return {"error": str(e)}

def level(level_id):
    try:
        # Referencia al documento del nivel
        level_ref = db.collection('levels').document(level_id)
        level_doc = level_ref.get()  # Obtener el documento del siguiente nivel
        
        if level_doc.exists:  # Verificar si el nivel existe
            level_data = level_doc.to_dict()
            return level_data
        else:
            return {"error": "Level not found"}
    except Exception as e:
        return {"error": str(e)}

def check_level_service(uid):
    try:
        if not uid:
            raise HTTPException(status_code=400, detail="No UID provided")
        
        # Reference to the user's document
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_doc.to_dict()
        current_level = int(user_data.get("level", "1"))
        current_global_points = int(user_data.get("globalPoints", "0"))
        
        # Get the points required for the next level
        next_level_ref = db.collection("levels").document(str(current_level + 1)).get()
        
        if next_level_ref.exists:
            next_level_data = next_level_ref.to_dict()
            next_level_points_required = int(next_level_data['points'])
            
            if current_global_points >= next_level_points_required:
                new_level = current_level + 1
                user_ref.update({"level": str(new_level)})
                user_data["level"] = str(new_level)
                user_data["level_updated"] = True
            else:
                user_data["level_updated"] = False
        else:
            # No next level exists, just return current data
            user_data["level_updated"] = False
        
        return user_data
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    

def get_top_level_status(level_id):
    try:
        # Stream all levels from Firestore
        levels_ref = db.collection('levels').stream()
        
        # Collect level IDs, converting them to integers for comparison
        levels_list = []
        for level in levels_ref:
            level_data = level.to_dict()
            level_data['id'] = level.id  # Use document ID as the level ID
            levels_list.append(int(level_data['id']))
        print(levels_list)
        # Ensure there are valid level IDs to compare
        if not levels_list or (int(level_id) not in levels_list):
            return {"error": "No levels found or levels have invalid IDs."}
        
        # Find the highest level ID
        max_level_id = max(levels_list)
        
        # Check if the provided level_id (converted to int) is the highest level
        return {"isTopLevel": int(level_id) == max_level_id}
    
    except ValueError:
        return {"error": "Invalid level ID format, unable to convert to integer."}
    except Exception as e:
        return {"error": str(e)}

def reset_monthly_points():
    """
    Resets monthly points for all users in the Firestore database.
    Returns a message indicating the completion status.
    """
    users_ref = db.collection("users").stream()
    updated_users_count = 0

    for user in users_ref:
        user_ref = db.collection("users").document(user.id)
        user_ref.update({"monthlyPoints": "0"})  # Resetting to zero
        updated_users_count += 1  # Increment the count of updated users

    return f"Monthly points reset for {updated_users_count} users."