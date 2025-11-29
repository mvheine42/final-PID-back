from fastapi import HTTPException
from app.models.category import Category
from app.service.category_service import (
    check_category_name_exists,
    create_category,
    get_categories,
    get_category_by_id,
    delete_category_by_id,
    update_category_name,
)
from app.service.product_service import product_by_id
from app.service.order_service import get_orders_by_status


# -------------------------------------------------------
#  REGISTER CATEGORY
# -------------------------------------------------------
def register_new_category(category: Category):
    """
    Valida y registra una nueva categoría.
    - name obligatorio, no solo espacios, no solo números
    - name único
    - type siempre termina siendo 'Custom'
    - no se permite crear categorías 'Default'
    """

    # --- NAME ---
    if category.name is None or not str(category.name).strip():
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    name = category.name.strip()

    if name.isdigit():
        raise HTTPException(status_code=400, detail="Category name cannot be only numbers")


    # --- NAME UNIQUE ---
    try:
        exists = check_category_name_exists(name)
    except Exception as e:
        # si Firebase falló al chequear el nombre
        raise HTTPException(status_code=500, detail=str(e))

    if exists:
        raise HTTPException(status_code=400, detail="Category name already exists")

    # --- TYPE ---
    # Lo que llegue en category.type lo usamos solo para bloquear 'Default'
    incoming_type = str(category.type or "").strip()

    if incoming_type.lower() == "default":
        raise HTTPException(status_code=400, detail="Cannot create a category with type 'Default'")

    # Regla de negocio: TODAS las creadas son 'Custom'
    final_type = "Custom"

    payload = {
        "name": name,
        "type": final_type,
    }

    # --- CREATE ---
    try:
        response = create_category(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return {"message": "Category registered successfully", "id": response["id"]}


# -------------------------------------------------------
#  GET ALL
# -------------------------------------------------------
def get_all_categories():
    response = get_categories()

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return response


# -------------------------------------------------------
#  GET BY ID
# -------------------------------------------------------
def get_category_by_id_controller(category_id: str):

    if not category_id.isdigit():
        raise HTTPException(status_code=400, detail="Category ID must be numeric")

    category = get_category_by_id(category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


# -------------------------------------------------------
#  DELETE CATEGORY
# -------------------------------------------------------
def delete_category_controller(category_id: str):

    # --- ID must be numeric ---
    if not category_id.isdigit():
        raise HTTPException(status_code=400, detail="Category ID must be numeric")

    response = delete_category_by_id(category_id)

    if "error" in response:
        msg = response["error"]

        if msg == "Category not found":
            raise HTTPException(status_code=404, detail=msg)

        # Includes:
        # - Cannot delete default
        # - Category used by products
        raise HTTPException(status_code=400, detail=msg)

    return response


# -------------------------------------------------------
#  UPDATE NAME
# -------------------------------------------------------
def update_category_name_controller(category_id: str, new_name: str):

    # --- ID debe ser numérico ---
    if not category_id.isdigit():
        raise HTTPException(status_code=400, detail="Category ID must be numeric")

    # --- VALIDAR NOMBRE ---
    if new_name is None or not str(new_name).strip():
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    new_name_clean = new_name.strip()

    # No permitir solo números
    if new_name_clean.isdigit():
        raise HTTPException(status_code=400, detail="Category name cannot be only numbers")

    if check_category_name_exists(new_name_clean):
        raise HTTPException(status_code=400, detail="Category name already exists")

    # --- EJECUTAR UPDATE ---
    response = update_category_name(category_id, new_name_clean)

    if "error" in response:
        msg = response["error"]
        if msg == "Category not found":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return response




# -------------------------------------------------------
#  CATEGORY REVENUE
# -------------------------------------------------------
def get_category_revenue_controller():
    try:
        orders = get_orders_by_status("FINALIZED")
        category_revenue = {}

        for order in orders:
            for item in order["orderItems"]:
                product_id = item["product_id"]
                amount = item["amount"]

                product = product_by_id(product_id)

                if "product" not in product:
                    continue

                category = product["product"].get("category", "")
                cats = [c.strip() for c in str(category).split(",") if c.strip()]

                price = float(product["product"].get("price", 0))
                cost = float(product["product"].get("cost", 0))

                for cid in cats:
                    cat = get_category_by_id(cid)
                    if not cat:
                        continue

                    name = cat["name"]
                    if name not in category_revenue:
                        category_revenue[name] = 0

                    category_revenue[name] += (price - cost) * amount

        return category_revenue

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
