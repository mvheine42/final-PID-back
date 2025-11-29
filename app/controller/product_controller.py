from app.service.product_service import (
    check_product_in_in_progress_orders,
    check_product_name_exists,
    create_product,
    get_products_by_category,
    lower_stock,
    products,
    update_product_newprice,
    update_product_newdescription,
    delete_product,
    product_by_id,
    update_product_newcategories,
    add_calories,
    update_stock,
)
from app.models.product import Product
from app.service.category_service import check_multiple_categories_exist
from fastapi import HTTPException
import re


def register_new_product(product: Product):

    if product.name is None or not str(product.name).strip():
        raise HTTPException(status_code=400, detail="Product Name cannot be empty")


    if product.name.isdigit():
        raise HTTPException(status_code=400, detail="Product Name cannot be only numbers")

    if product.description is None or not str(product.description).strip():
        raise HTTPException(status_code=400, detail="Description cannot be empty")

    description = product.description.strip()

    if description.isdigit():
        raise HTTPException(status_code=400, detail="Description cannot be only numbers")

    if check_product_name_exists(product.name):
        raise HTTPException(status_code=400, detail="Product name already exists")

    if product.price is None or str(product.price).strip() == "":
        raise HTTPException(status_code=400, detail="Price cannot be empty")

    try:
        price = float(product.price)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Price must be a number")

    if price <= 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative or zero")

    if price > 1_000_000:
        raise HTTPException(status_code=400, detail="Price exceeds allowed limit")


    if product.cost is None or str(product.cost).strip() == "":
        raise HTTPException(status_code=400, detail="Cost cannot be empty")

    try:
        cost = float(product.cost)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Cost must be a number")

    if cost < 0:
        raise HTTPException(status_code=400, detail="Cost cannot be negative")

    if cost > price:
        raise HTTPException(status_code=400, detail="Cost cannot exceed price")
    
    if product.imageUrl is None or not str(product.imageUrl).strip():
        raise HTTPException(status_code=400, detail="Image URL cannot be empty")

    if product.category is None or not str(product.category).strip():
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    category_str = str(product.category).strip()

    category_ids = [c.strip() for c in category_str.split(",") if c.strip()]

    for cid in category_ids:
        if not cid.isdigit() or int(cid) <= 0:
            raise HTTPException(status_code=400, detail=f"Invalid category ID: {cid}")

    if len(category_ids) != len(set(category_ids)):
        raise HTTPException(status_code=400, detail="Categories cannot contain duplicates")

    check = check_multiple_categories_exist(category_str)
    if isinstance(check, dict):
        if not check.get("ok", False):
            missing = ", ".join(check.get("missing", []))
            raise HTTPException(status_code=400, detail=f"Category does not exist: {missing}")
    else:
        if not check:
            raise HTTPException(status_code=400, detail="Category does not exist")


    if product.calories is None or str(product.calories).strip() == "":
        raise HTTPException(status_code=400, detail="Calories cannot be empty")

    try:
        calories = float(product.calories)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Calories must be a valid number")

    if calories < 0:
        raise HTTPException(status_code=400, detail="Calories must be equal or greater than 0")

    if calories > 100_000:
        raise HTTPException(status_code=400, detail="Calories exceed allowed limit")

    if product.stock is None or str(product.stock).strip() == "":
        raise HTTPException(status_code=400, detail="Stock cannot be empty")

    try:
        stock = int(product.stock)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Stock must be an integer")

    if stock < 0:
        raise HTTPException(status_code=400, detail="Stock must be >= 0")

    if stock > 10_000:
        raise HTTPException(status_code=400, detail="Stock exceeds allowed limit")

    product_data = product.dict()
    product_data["category"] = category_str

    try:
        response = create_product(product_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return {"message": "Product registered successfully", "id": response["id"]}


def get_products():
    try:
        response = products()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def update_product_price(product_id: str, new_price):

    if new_price is None or str(new_price).strip() == "":
        raise HTTPException(status_code=400, detail="Price cannot be empty")

    try:
        price = float(new_price)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Price must be a number")

    if price <= 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative or zero")

    if price > 1_000_000:
        raise HTTPException(status_code=400, detail="Price exceeds allowed limit")

    product_check = product_by_id(product_id)
    if "error" in product_check:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        resp = update_product_newprice(product_id, new_price)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in resp:
        raise HTTPException(status_code=500, detail=resp["error"])

    return resp


def update_product_description(product_id: str, new_description: str):

    if new_description is None or not str(new_description).strip():
        raise HTTPException(status_code=400, detail="Description cannot be empty")

    description = new_description.strip()

    if description.isdigit():
        raise HTTPException(status_code=400, detail="Description cannot be only numbers")

    product_check = product_by_id(product_id)
    if "error" in product_check:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        resp = update_product_newdescription(product_id, new_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in resp:
        raise HTTPException(status_code=500, detail=resp["error"])

    return resp

def update_product_categories(product_id: str, newcategories: str):

    if newcategories is None or not str(newcategories).strip():
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    categories_str = newcategories.strip()

    if not re.match(r"^[0-9,\s]+$", categories_str):
        raise HTTPException(status_code=400, detail="Categories format is invalid")

    category_ids = [c.strip() for c in categories_str.split(",") if c.strip()]

    if len(category_ids) == 0:
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    for cid in category_ids:
        if not cid.isdigit() or int(cid) <= 0:
            raise HTTPException(status_code=400, detail=f"Invalid category ID: {cid}")
        
    if len(category_ids) != len(set(category_ids)):
        raise HTTPException(status_code=400, detail="Categories cannot contain duplicates")

    product_check = product_by_id(product_id)
    if "error" in product_check:
        raise HTTPException(status_code=404, detail="Product not found")

    check = check_multiple_categories_exist(categories_str)

    if isinstance(check, dict):
        if not check.get("ok", False):
            missing = ", ".join(check.get("missing", []))
            raise HTTPException(status_code=400, detail=f"Category does not exist: {missing}")
    else:
        if not check:
            raise HTTPException(status_code=400, detail="Category does not exist")

    try:
        resp = update_product_newcategories(product_id, categories_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in resp:
        raise HTTPException(status_code=500, detail=resp["error"])

    return resp



def delete_product_by_id(product_id: str):

    if product_id is None or str(product_id).strip() == "":
        raise HTTPException(status_code=400, detail="Product ID cannot be empty")

    product_id = str(product_id).strip()

    if not product_id.isdigit():
        raise HTTPException(status_code=400, detail="Product ID must be a positive integer")

    product_check = product_by_id(product_id)
    if "error" in product_check:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        response = delete_product(product_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return {"message": "Product deleted successfully"}


def get_product_by_id(product_id: str):

    if product_id is None or str(product_id).strip() == "":
        raise HTTPException(status_code=400, detail="Product ID cannot be empty")

    product_id = str(product_id).strip()

    if not product_id.isdigit():
        raise HTTPException(status_code=400, detail="Product ID must be a positive integer")

    try:
        response = product_by_id(product_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in response:
        raise HTTPException(status_code=404, detail="Product not found")

    return response


def add_food_calories(product_id: str, calories: float):
    
    if product_id is None or str(product_id).strip() == "":
        raise HTTPException(status_code=400, detail="Product ID cannot be empty")
    
    product_check = product_by_id(product_id)
    if "error" in product_check:
        raise HTTPException(status_code=404, detail="Product not found")

    product_id = str(product_id).strip()

    if not product_id.isdigit():
        raise HTTPException(status_code=400, detail="Product ID must be a positive integer")

    if calories is None or str(calories).strip() == "":
        raise HTTPException(status_code=400, detail="Calories cannot be empty")
    try:
        cal = float(calories)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Calories must be a number")

    if cal < 0:
        raise HTTPException(status_code=400, detail="Calories must be equal or greater than 0")

    if cal > 100_000:
        raise HTTPException(status_code=400, detail="Calories exceed allowed limit")

    try:
        response = add_calories(product_id, cal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return response


def get_products_by_category_controller(category_id: str):

    if category_id is None or str(category_id).strip() == "":
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    categories_str = str(category_id).strip()

    if not re.match(r"^[0-9,\s]+$", categories_str):
        raise HTTPException(status_code=400, detail="Invalid category format")

    category_ids = [c.strip() for c in categories_str.split(",") if c.strip()]

    if len(category_ids) == 0:
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    for cid in category_ids:
        if not cid.isdigit() or int(cid) <= 0:
            raise HTTPException(status_code=400, detail=f"Invalid category ID: {cid}")

    if len(category_ids) != len(set(category_ids)):
        raise HTTPException(status_code=400, detail="Categories cannot contain duplicates")

    check = check_multiple_categories_exist(categories_str)
    if isinstance(check, dict):
        if not check.get("ok", False):
            missing = ", ".join(check.get("missing", []))
            raise HTTPException(status_code=400, detail=f"Category does not exist: {missing}")
    else:
        if not check:
            raise HTTPException(status_code=400, detail="Category does not exist")

    try:
        response = get_products_by_category(categories_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Si no hay productos → devolver 404
    if isinstance(response, dict) and "error" in response:
        raise HTTPException(status_code=404, detail=response["error"])

    return response



def check_product_in_in_progress_orders_controller():

    try:
        response = check_product_in_in_progress_orders()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Si el service devuelve un error controlado
    if isinstance(response, dict) and "error" in response:
        # Ejemplo: "No products found in 'IN PROGRESS' orders"
        raise HTTPException(status_code=404, detail=response["error"])

    return response


def update_stock_controller(product_id, stock):

    if product_id is None or str(product_id).strip() == "":
        raise HTTPException(status_code=400, detail="Product ID cannot be empty")

    product_id = str(product_id).strip()

    if not product_id.isdigit():
        raise HTTPException(status_code=400, detail="Product ID must be a positive integer")

    if stock is None or str(stock).strip() == "":
        raise HTTPException(status_code=400, detail="Stock cannot be empty")

    try:
        add_units = int(stock)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Stock must be an integer")

    if add_units < 0:
        raise HTTPException(status_code=400, detail="Stock must be equal or greater than 0")

    product_check = product_by_id(product_id)
    if "error" in product_check:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        resp = update_stock(product_id, stock)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in resp:
        raise HTTPException(status_code=500, detail=resp["error"])

    return resp

def lower_stock_controller(product_id, stock):

    if product_id is None or str(product_id).strip() == "":
        raise HTTPException(status_code=400, detail="Product ID cannot be empty")

    product_id = str(product_id).strip()

    if not product_id.isdigit():
        raise HTTPException(status_code=400, detail="Product ID must be a positive integer")

    if stock is None or str(stock).strip() == "":
        raise HTTPException(status_code=400, detail="Stock cannot be empty")

    try:
        sub_units = int(stock)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Stock must be an integer")

    if sub_units <= 0:
        raise HTTPException(status_code=400, detail="Stock to lower must be > 0")

    product_check = product_by_id(product_id)
    if "error" in product_check:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        resp = lower_stock(product_id, stock)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in resp:
        msg = resp["error"]

        if msg == "Insufficient stock":
            raise HTTPException(status_code=400, detail=msg)

        raise HTTPException(status_code=500, detail=msg)

    return resp
