from app.db.firebase import db
from fastapi import HTTPException

def get_next_id_from_existing():
    """
    Devuelve el siguiente ID disponible para la colección 'category'.
    """
    try:
        categories = db.collection('category').stream()
        existing_ids = [int(c.id) for c in categories if c.id.isdigit()]
        return max(existing_ids) + 1 if existing_ids else 1
    except Exception as e:
        return {"error": f"Error retrieving next ID: {str(e)}"}


def create_category(category_data: dict):
    """
    Guarda una categoría normalizando campos básicos.
    El controller valida reglas de negocio.
    """
    try:
        if not isinstance(category_data, dict):
            return {"error": "Invalid category data format"}

        name = str(category_data.get("name", "")).strip()
        type_value = str(category_data.get("type", "")).strip()

        category_data["name"] = name
        category_data["type"] = type_value

        next_id = get_next_id_from_existing()
        if isinstance(next_id, dict) and "error" in next_id:
            return next_id

        ref = db.collection("category").document(str(next_id))
        ref.set(category_data)

        return {"message": "Category added successfully", "id": next_id}

    except Exception as e:
        return {"error": str(e)}

def update_category_name(category_id: str, new_name: str):
    try:
        ref = db.collection("category").document(category_id)
        snap = ref.get()

        if not snap.exists:
            return {"error": "Category not found"}

        data = snap.to_dict()

        if data.get("type") == "Default":
            return {"error": "Cannot edit the name of a 'Default' category"}

        new_name_clean = str(new_name).strip()

        ref.update({"name": new_name_clean})

        return {"message": "Category name updated successfully"}

    except Exception as e:
        return {"error": str(e)}

def get_categories():
    try:
        ref = db.collection("category").stream()
        result = []

        for c in ref:
            data = c.to_dict()
            data["id"] = c.id
            result.append(data)

        return {"categories": result}

    except Exception as e:
        return {"error": str(e)}

def get_category_by_id(category_id: str):
    try:
        snap = db.collection("category").document(category_id).get()
        if not snap.exists:
            return None

        data = snap.to_dict()
        data["id"] = snap.id
        return data

    except Exception as e:
        return {"error": str(e)}

def delete_category_by_id(category_id: str):
    try:
        ref = db.collection("category").document(category_id)
        snap = ref.get()

        if not snap.exists:
            return {"error": "Category not found"}

        data = snap.to_dict()

        if data.get("type") == "Default":
            return {"error": "Cannot delete a 'Default' category"}

        products_ref = db.collection("products").stream()

        for p in products_ref:
            p_data = p.to_dict()
            p_cats = str(p_data.get("category", "")).split(",")

            p_cats = [c.strip() for c in p_cats if c.strip()]

            if category_id in p_cats:
                return {
                    "error": f"Category is assigned to at least one product and cannot be deleted"
                }

        ref.delete()
        return {"message": "Category deleted successfully"}

    except Exception as e:
        return {"error": str(e)}

def category_exists(category_id: int) -> bool:
    try:
        snap = db.collection("category").document(str(category_id)).get()
        return snap.exists
    except Exception as e:
        raise Exception(f"Error checking category: {str(e)}")

def check_multiple_categories_exist(category_str: str) -> dict:
    category_ids = [c.strip() for c in category_str.split(",") if c.strip()]
    missing = []

    for cid in category_ids:
        if not cid.isdigit():
            missing.append(cid)
            continue
        if not category_exists(int(cid)):
            missing.append(cid)

    return {
        "ok": len(missing) == 0,
        "missing": missing
    }


def check_category_name_exists(category_name: str) -> bool:
    """
    Devuelve True si ya existe una categoría con ese nombre,
    False si no. Si hay error de Firebase, lanza excepción.
    """
    try:
        ref = db.collection("category").where("name", "==", category_name).stream()
        return any(ref)
    except Exception as e:
        raise Exception(f"Error checking if category name exists: {str(e)}")

