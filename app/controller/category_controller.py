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


def register_new_category(category: Category):
    """
    Valida y registra una nueva categoría.
    - name obligatorio, no solo espacios, no solo números
    - name único
    - type siempre termina siendo 'Custom'
    - no se permite crear categorías 'Default'
    """

    if category.name is None or not str(category.name).strip():
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    name = category.name.strip()

    if name.isdigit():
        raise HTTPException(status_code=400, detail="Category name cannot be only numbers")


    try:
        exists = check_category_name_exists(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if exists:
        raise HTTPException(status_code=400, detail="Category name already exists")

    incoming_type = str(category.type or "").strip()

    if incoming_type.lower() == "default":
        raise HTTPException(status_code=400, detail="Cannot create a category with type 'Default'")

    final_type = "Custom"

    payload = {
        "name": name,
        "type": final_type,
    }

    try:
        response = create_category(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return {"message": "Category registered successfully", "id": response["id"]}

def get_all_categories():
    response = get_categories()

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return response


def get_category_by_id_controller(category_id: str):

    if not category_id.isdigit():
        raise HTTPException(status_code=400, detail="Category ID must be numeric")

    category = get_category_by_id(category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


def delete_category_controller(category_id: str):

    if not category_id.isdigit():
        raise HTTPException(status_code=400, detail="Category ID must be numeric")

    response = delete_category_by_id(category_id)

    if "error" in response:
        msg = response["error"]

        if msg == "Category not found":
            raise HTTPException(status_code=404, detail=msg)

        raise HTTPException(status_code=400, detail=msg)

    return response


def update_category_name_controller(category_id: str, new_name: str):

    if not category_id.isdigit():
        raise HTTPException(status_code=400, detail="Category ID must be numeric")

    if new_name is None or not str(new_name).strip():
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    new_name_clean = new_name.strip()

    if new_name_clean.isdigit():
        raise HTTPException(status_code=400, detail="Category name cannot be only numbers")

    if check_category_name_exists(new_name_clean):
        raise HTTPException(status_code=400, detail="Category name already exists")

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
    """
    Calculates revenue (margin = price - cost) per category for all FINALIZED orders.
    Uses caching to minimize repeated database calls for products and categories.
    """
    try:
        finalized_orders = get_orders_by_status("FINALIZED")
        revenue_by_category = {}
        products = {}
        categories= {}
        
        for order in finalized_orders or []:
            for order_item in order.get("orderItems", []):
                product_id = order_item.get("product_id")
                item_quantity = order_item.get("amount", 0)
                
                if not product_id or not item_quantity:
                    continue
                
                # Get product with caching
                if product_id in products:
                    product_response = products[product_id]
                else:
                    product_response = product_by_id(product_id)
                    products[product_id] = product_response
                
                # Validate product response
                if not isinstance(product_response, dict) or "product" not in product_response:
                    continue
                
                product_details = product_response["product"]
                
                # Handle category field (string or list)
                category_field = product_details.get("category")
                if isinstance(category_field, str):
                    category_ids = [c.strip() for c in category_field.split(",") if c.strip()]
                elif isinstance(category_field, list):
                    category_ids = [str(c).strip() for c in category_field if c]
                else:
                    category_ids = []
                
                # Calculate margin safely
                try:
                    product_price = float(product_details.get("price", 0))
                    product_cost = float(product_details.get("cost", 0))
                    item_margin = (product_price - product_cost) * float(item_quantity)
                except (ValueError, TypeError):
                    continue
                
                # Accumulate revenue per category
                for category_id in category_ids:
                    # Get category with caching
                    if category_id in categories:
                        category_data = categories[category_id]
                    else:
                        category_data = get_category_by_id(category_id)
                        categories[category_id] = category_data
                    
                    # Validate category
                    if not category_data or not isinstance(category_data, dict) or "error" in category_data:
                        continue
                    
                    category_name = category_data.get("name")
                    if not category_name:
                        continue
                    
                    # Add margin to category
                    revenue_by_category[category_name] = revenue_by_category.get(category_name, 0) + item_margin
        
        return revenue_by_category
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating category revenue: {str(e)}")
