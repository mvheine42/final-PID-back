from app.db.firebase import db


# -------------------------------------------------------
#  ID AUTOINCREMENTAL
# -------------------------------------------------------
def get_next_product_id_from_existing():
    try:
        products = db.collection('products').stream()
        existing_ids = [int(p.id) for p in products if p.id.isdigit()]
        return max(existing_ids) + 1 if existing_ids else 1
    except Exception as e:
        return {"error": f"Error retrieving next ID: {str(e)}"}


# -------------------------------------------------------
#  CREATE PRODUCT
# -------------------------------------------------------
def create_product(product_data):
    try:
        next_id = get_next_product_id_from_existing()
        if isinstance(next_id, dict) and "error" in next_id:
            return next_id

        # siempre almacenar category como string
        if "category" in product_data:
            product_data["category"] = str(product_data["category"])

        product_ref = db.collection("products").document(str(next_id))
        product_ref.set(product_data)

        return {"message": "Product added successfully", "id": next_id}

    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
#  GET PRODUCTS
# -------------------------------------------------------
def products():
    try:
        ref = db.collection('products').stream()
        product_list = []

        for p in ref:
            data = p.to_dict()
            data["id"] = p.id
            product_list.append(data)

        return {"products": product_list, "message": "Products retrieved successfully"}

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  UPDATE PRICE
# -------------------------------------------------------
def update_product_newprice(product_id: str, new_price):
    try:
        product_ref = db.collection('products').document(product_id)
        snap = product_ref.get()

        if not snap.exists:
            return {"error": "Product not found"}

        product_ref.update({"price": new_price})
        return {"message": "Product price updated successfully"}

    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
#  UPDATE DESCRIPTION
# -------------------------------------------------------
def update_product_newdescription(product_id, new_description):
    try:
        product_ref = db.collection('products').document(product_id)
        snap = product_ref.get()

        if not snap.exists:
            return {"error": "Product not found"}

        product_ref.update({"description": new_description})
        return {"message": "Product description updated successfully"}

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  UPDATE CATEGORIES
# -------------------------------------------------------
def update_product_newcategories(product_id, new_categories):
    try:
        product_ref = db.collection("products").document(product_id)
        snap = product_ref.get()

        if not snap.exists:
            return {"error": "Product not found"}

        product_ref.update({"category": new_categories})
        return {"message": "Product categories updated successfully"}

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  DELETE PRODUCT
# -------------------------------------------------------
def delete_product(product_id: str):
    try:
        product_ref = db.collection("products").document(product_id)
        snap = product_ref.get()

        if not snap.exists:
            return {"error": "Product not found"}

        product_ref.delete()
        return {"message": "Product deleted successfully"}

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  GET PRODUCT BY ID
# -------------------------------------------------------
def product_by_id(product_id: str):
    try:
        ref = db.collection("products").document(product_id)
        snap = ref.get()

        if not snap.exists:
            return {"error": "Product not found"}

        data = snap.to_dict()
        data["id"] = product_id

        return {"product": data, "message": "Product retrieved successfully"}

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  ADD CALORIES
# -------------------------------------------------------
def add_calories(product_id: str, calories: float):
    try:
        ref = db.collection("products").document(product_id)
        snap = ref.get()

        if not snap.exists:
            return {"error": "Product not found"}

        ref.update({"calories": calories})
        return {"message": "Product calories updated successfully"}

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  CHECK IF NAME EXISTS
# -------------------------------------------------------
def check_product_name_exists(product_name: str):
    try:
        query = db.collection("products").where("name", "==", product_name).stream()

        # stream solo se puede consumir una vez → convierto a lista
        results = list(query)

        return len(results) > 0

    except Exception as e:
        return {"error": f"Error checking if product name exists: {str(e)}"}



# -------------------------------------------------------
#  GET PRODUCTS BY CATEGORY
# -------------------------------------------------------
def get_products_by_category(category_ids_str: str):
    try:
        category_ids = category_ids_str.split(", ")
        ref = db.collection("products").stream()

        filtered = []

        for p in ref:
            data = p.to_dict()
            data["id"] = p.id

            product_categories = str(data.get("category", "")).split(", ")

            if any(cat in product_categories for cat in category_ids):
                filtered.append(data)

        if not filtered:
            return {"error": "No products found for given categories"}

        return filtered

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  PRODUCTS IN IN-PROGRESS ORDERS
# -------------------------------------------------------
def check_product_in_in_progress_orders():
    try:
        orders_ref = db.collection("orders")
        in_progress = orders_ref.where("status", "==", "IN PROGRESS").stream()

        products_list = []

        for order in in_progress:
            data = order.to_dict()
            items = data.get("orderItems", [])
            products_list.extend(items)

        if not products_list:
            return {"error": "No products found in 'IN PROGRESS' orders"}

        return products_list

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  UPDATE STOCK (ADD)
# -------------------------------------------------------
def update_stock(product_id: str, new_stock: str):
    try:
        product_ref = db.collection("products").document(product_id)
        snap = product_ref.get()

        if not snap.exists:
            return {"error": "Product not found"}

        data = snap.to_dict()
        current_stock = int(data.get("stock", "0"))

        updated_stock = current_stock + int(new_stock)

        if updated_stock < 0:
            return {"error": "Stock cannot be negative"}

        product_ref.update({"stock": str(updated_stock)})

        return {"message": "Product stock updated successfully"}

    except Exception as e:
        return {"error": str(e)}



# -------------------------------------------------------
#  LOWER STOCK (SUBTRACT)
# -------------------------------------------------------
def lower_stock(product_id: str, new_stock: str):
    try:
        product_ref = db.collection("products").document(product_id)
        snap = product_ref.get()

        if not snap.exists:
            return {"error": "Product not found"}

        data = snap.to_dict()
        current_stock = int(data.get("stock", "0"))

        updated_stock = current_stock - int(new_stock)

        if updated_stock < 0:
            return {"error": "Insufficient stock"}

        product_ref.update({"stock": str(updated_stock)})

        return {"message": "Product stock updated successfully"}

    except Exception as e:
        return {"error": str(e)}
