from typing import List
from app.service.order_service import assign_employee_to_order, assign_order_to_table_service, create_order, delete_order_items, finalize_order, get_months_revenue_service, get_order_by_id, get_all_orders, add_items_to_order, get_average_per_person_service, get_average_per_order_service, serve_order_item_service
from app.models.order import Order
from app.models.order import OrderItem
from app.controller.table_controller import associate_order_with_table_controller
from fastapi import HTTPException
from app.service.product_service import product_by_id
from app.service.table_service import get_table_by_id, update_table_status

def register_new_order(order: Order):
    order_data = order.dict()

    # Validar que la mesa esté incluida en la orden
    '''table_id = order_data.get('tableNumber')
    if not table_id:
        raise HTTPException(status_code=400, detail="Table ID is required")

    # Verificar si la mesa existe utilizando get_table_by_id directamente
    table = get_table_by_id(str(table_id))  # Asegúrate de que sea string si es necesario
    if not table:
        raise HTTPException(status_code=404, detail=f"Table with ID {table_id} not found")'''

    # Obtener datos de los productos desde la orden
    order_items = order_data.get('orderItems', [])
    if not order_items:
        raise HTTPException(status_code=400, detail="At least one order item is required")

    # verificar que el amountOfPeople sea mayor a cero pero menor a la capacity de una table
    #amountOfPeople = order_data.get('amountOfPeople')
    #verificar que amountOfPeople sea mayor a 0 y menor a la capacidad de una mesa
    '''if amountOfPeople <= 0 or amountOfPeople > table.get('capacity'):
        raise HTTPException(status_code=400, detail="Amount of people must be greater than 0 and less than or equal to the table capacity")'''

    for item in order_items:
        # Obtener product_id del item
        product_id = item.get('product_id')
        if not product_id:
            raise HTTPException(status_code=400, detail="Product ID is required in the order item")

        # Verificar si el producto existe en la base de datos
        product_data = product_by_id(product_id)
        
        # Debugging: Print product to see its structure
        print(f"Fetched product from database: {product_data}")

        # Access the nested product fields
        product = product_data.get('product', {})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

        # Validar que el nombre y precio coincidan con los de la base de datos
        product_name = item.get('product_name')
        product_price = item.get('product_price')

        # Comparar con los valores de la base de datos
        if product_name != product.get('name'):
            raise HTTPException(status_code=400, detail=f"Product name for product ID {product_id} does not match")

        if product_price != str(product.get('price')): 
            raise HTTPException(status_code=400, detail=f"Product price for product ID {product_id} does not match")

    # Validaciones completas, proceder a crear la orden
    response = create_order(order_data)
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
    # quiero llamar a associate_order_with_table para asociar la orden con la mesa
    '''response_table = associate_order_with_table_controller(str(table_id), str(response["order_id"]))
    if "error" in response_table:
        raise HTTPException(status_code=500, detail=response_table["error"])
    #quiero retornar response_table y response juntos
    response["table"] = response_table'''
    return response

def finalize_order_controller(order_id: str):
    """
    Endpoint to finalize an order by ID.
    """
    try:
        # Call the service to finalize the order
        response = finalize_order(order_id)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_order_controller(order_id: str):
    try:
        response = get_order_by_id(order_id)
        if not response:
            raise HTTPException(status_code=404, detail="Order not found")
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_orders():
    try:
        response = get_all_orders()
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def add_order_items(order_id: str, new_order_items_data: List[dict], total: str):
    try:
        # Fetch the existing order
        existing_order = get_order_by_id(order_id)
        if not existing_order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Check if the order status is 'IN PROGRESS'
        if existing_order.get("status") != "IN PROGRESS":
            raise HTTPException(status_code=400, detail="Cannot add items to an order that is not in progress")

        # Convertir los datos de la solicitud en instancias de OrderItem
        new_order_items = [OrderItem(**item) for item in new_order_items_data]

        # Validar que cada product_id exista en la tabla de productos
        for item in new_order_items:
            product_id = item.product_id
            product = product_by_id(product_id)  # Fetch product details by product_id
            if "error" in product:
                raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

        # Actualizar la orden con los nuevos ítems (que ya incluyen viejos y nuevos)
        response = add_items_to_order(order_id, new_order_items, total)
        return response
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def delete_order_items_controller(order_id: str, order_items: List[str]):
    try:
        # Fetch the existing order
        existing_order = get_order_by_id(order_id)
        if not existing_order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Check if the order status is 'IN PROGRESS'
        if existing_order.get("status") != "INACTIVE":
            raise HTTPException(status_code=400, detail="Cannot DELETE items to an order that is not in progress")

        # Convertir los datos de la solicitud en instancias de OrderItem

        # Actualizar la orden con los nuevos ítems (que ya incluyen viejos y nuevos)
        response = delete_order_items(order_id, order_items)
        return response
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_months_revenue():
    try:
        response = get_months_revenue_service()
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_average_per_person_controller(year: str, month: str):
    try:
        response = get_average_per_person_service(year, month)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_average_per_order_controller(year: str, month: str):
    try:
        response = get_average_per_order_service(year, month)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def assign_order_to_table_controller(order_id: str, table_id: int):
    try:
        response = assign_order_to_table_service(order_id, table_id)
        response2 = associate_order_with_table_controller(str(table_id), order_id)
        response["table"] = response2
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def assign_employee_to_order_controller(order_id, uid):
    try:
        response = assign_employee_to_order(str(order_id), uid)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def serve_order_item_controller(order_id: str, item_id: str):
    try:
        return serve_order_item_service(order_id, item_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))