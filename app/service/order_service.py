from calendar import monthrange
from typing import Dict, List
from zoneinfo import ZoneInfo
from app.db.firebase import db
from app.service.table_service import get_table_by_id
from app.models.order_item import OrderItem
from datetime import datetime
from app.date_time_utils import now_ba_iso, parse_any_iso_to_ba_naive
from fastapi import HTTPException
from collections import defaultdict

from datetime import datetime, timedelta


def create_order(order_data):
    try:

        next_id = get_next_order_id_from_existing()
        # Crear una nueva orden
        orders_ref = db.collection('orders')
        new_order_ref = orders_ref.document(str(next_id))
        new_order_ref.set(order_data)  # Crear la nueva orden en Firebase
        
        return {
            "message": "Order created successfully",
            "order_id": next_id,  # Devuelve el ID de la nueva orden
            "order": order_data  # También puedes devolver los datos de la orden
        }
    except Exception as e:
        return {"error": str(e)}
    

def finalize_order(order_id: str):
    """
    Finalizes an order and updates the employee's points.
    """
    try:
        # Get the order by its ID
        order_ref = db.collection('orders').document(order_id)
        order = order_ref.get()

        if not order.exists:
            raise HTTPException(status_code=404, detail="Order not found")

        # Extract employee UID from the order
        employee_uid = order.to_dict().get("employee")
        if not employee_uid:
            raise HTTPException(status_code=400, detail="Employee UID missing in order")

        # Update the order status to finalized
        order_ref.update({"status": "FINALIZED"})

        # Fetch the user's current points
        user_ref = db.collection("users").document(employee_uid)
        user_data = user_ref.get()

        if not user_data.exists:
            raise HTTPException(status_code=404, detail="User not found")

        # Get current points and convert to int, default to 0 if missing
        user_dict = user_data.to_dict()
        current_global_points = int(user_dict.get("globalPoints", "0"))
        current_monthly_points = int(user_dict.get("monthlyPoints", "0"))

        # Increment points and convert back to string
        updated_global_points = str(current_global_points + 1)
        updated_monthly_points = str(current_monthly_points + 1)

        # Update the user's points as strings
        user_ref.update({
            "globalPoints": updated_global_points,
            "monthlyPoints": updated_monthly_points
        })

        return {"message": "Order finalized successfully, points updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_order_by_id(order_id: str):
    try:
        order_ref = db.collection('orders').document(order_id)
        order_doc = order_ref.get()
        if not order_doc.exists:
            return None
        
        # --- AGREGAR ESTO ---
        data = order_doc.to_dict()
        data['id'] = order_doc.id # Inyectamos el ID en la respuesta
        print(data)
        return data
        # --------------------

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving order: {str(e)}")


def get_all_orders():
    """
    Obtiene todas las órdenes de la colección 'orders'.
    """
    try:
        orders_ref = db.collection('orders').stream()
        orders_list = []

        for order in orders_ref:
            order_data = order.to_dict()
            order_data['id'] = order.id
            orders_list.append(order_data)

        return orders_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving orders: {str(e)}")

def get_next_order_id_from_existing():
    """
    Obtiene el próximo ID disponible en la colección 'products'.
    """
    try:
        # Obtener todos los documentos de la colección 'products'
        orders = db.collection('orders').stream()

        # Extraer los IDs existentes y convertirlos a enteros
        existing_ids = [int(order.id) for order in orders if order.id.isdigit()]

        if existing_ids:
            # Encontrar el mayor ID existente y sumar 1
            next_id = max(existing_ids) + 1
        else:
            # Si no hay IDs, comenzamos desde 1
            next_id = 1

        return next_id
    except Exception as e:
        raise Exception(f"Error retrieving next ID from existing products: {str(e)}")

def update_order(order_id: str, updated_order_data: dict):
    try:
        # Reference to the order in the database
        order_ref = db.collection('orders').document(order_id)
        
        # Perform the update in the database
        order_ref.update(updated_order_data)
        return {"message": "Order updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def add_items_to_order(order_id: str, new_items: List[OrderItem], total: str):
    # 1) Traer la orden existente
    existing_order = get_order_by_id(order_id)
    if not existing_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2) Ítems que ya tenía la orden (NO los tocamos)
    existing_items = existing_order.get("orderItems", [])

    # 3) Convertimos los nuevos ítems a dict
    new_items_dicts = [item.dict() for item in new_items]

    # 4) Merge: viejos + nuevos
    merged_items = existing_items + new_items_dicts

    # 5) Armamos copia para actualizar
    order_copy = existing_order.copy()
    order_copy["orderItems"] = merged_items
    order_copy["total"] = total

    # 6) Persistimos en Firestore
    response = update_order(order_id, order_copy)

    if isinstance(response, dict) and "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return response



def delete_order_items(order_id: str, order_items: List[str]):
    # Obtener la orden existente
    order_ref = db.collection('orders').document(order_id)
    existing_order = order_ref.get()

    if not existing_order.exists:
        raise HTTPException(status_code=404, detail="Order not found")

    # Obtener los orderItems de la orden
    order_data = existing_order.to_dict()
    current_order_items = order_data.get('orderItems', [])

    # Filtrar los orderItems que no estén en la lista order_items
    updated_order_items = [
        item for item in current_order_items if item['product_id'] not in order_items
    ]

    # Actualizar la orden con los nuevos orderItems
    order_ref.update({
        'orderItems': updated_order_items
    })

    return {"message": "Order items deleted successfully"}

def get_orders_by_status(status: str):
    """
    Retrieves all orders from the 'orders' collection with the specified status.
    """
    try:
        orders_ref = db.collection('orders').where('status', '==', status).stream()
        orders_list = []

        for order in orders_ref:
            order_data = order.to_dict()
            order_data['id'] = order.id  # Add the document ID to the order data
            orders_list.append(order_data)
        return orders_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving orders: {str(e)}")

def get_months_revenue_service():
    try:
        #necesito ver todas las ordenes de mi base y armar una lista que asocie mes con el total de plata de cada orden en el mes
        #en este caso, lo que me interesa es el mes y el total de plata
        #la lista lo construyo con un diccionario donde la llave es el mes y el valor es el total de plata

        orders = db.collection('orders').stream()
        months_revenue = {}
        for order in orders:
            order_data = order.to_dict()
            date = order_data.get('date')
            #necesito mes y año juntos
            #ejemplo: 2022-01
            #ejemplo: 2022-02
            # i need to join month and year together
            # example: 2022-01
            # example: 2022-02
            #
            month = date.split('-')[1]
            year = date.split('-')[0]
            month_year = f"{year}-{month}"
            total = order_data.get('total')
            if month_year in months_revenue:
                months_revenue[month_year] += float(total)  
            else:
                months_revenue[month_year] = float(total)

        return months_revenue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving orders: {str(e)}")

def get_average_per_person_service(year: str, month: str) -> Dict[str, float]:
    try:
        _, num_days = monthrange(int(year), int(month))

        average_per_person = {f"{year}-{int(month):02d}-{day:02d}": 0 for day in range(1, num_days + 1)}

        # Query orders within the specified month
        orders = db.collection('orders') \
                   .where('date', '>=', f"{year}-{month}-01") \
                   .where('date', '<=', f"{year}-{month}-{num_days}") \
                   .stream()

        # Dictionary to accumulate the sum of averages per day
        daily_totals = {f"{year}-{int(month):02d}-{day:02d}": [] for day in range(1, num_days + 1)}

        for order in orders:
            order_data = order.to_dict()
            date = order_data.get('date')
            total = order_data.get('total')
            amount_of_people = order_data.get('amountOfPeople')

            # Ensure that total is converted to float
            try:
                total = float(total)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid total value: {total}")

            # Ensure amount_of_people is valid
            if amount_of_people > 0:
                average = total / amount_of_people
                if date in daily_totals:
                    daily_totals[date].append(average)

        # Calculate the sum of averages for each day
        for day, averages in daily_totals.items():
            if averages:  # Only sum if there are averages for that day
                average_per_person[day] = sum(averages)

        return average_per_person
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving orders: {str(e)}")

def get_average_per_order_service(year: str, month: str) -> Dict[str, float]:
    # i need to get the average per order so, sum all the orders totals and divide by the amount of orders
    try:
        _, num_days = monthrange(int(year), int(month))

        average_per_order = {f"{year}-{int(month):02d}-{day:02d}": 0 for day in range(1, num_days + 1)}

        # Query orders within the specified month
        orders = db.collection('orders') \
                   .where('date', '>=', f"{year}-{month}-01") \
                   .where('date', '<=', f"{year}-{month}-{num_days}") \
                   .stream()

        # Dictionary to accumulate the sum of averages per day
        daily_totals = {f"{year}-{int(month):02d}-{day:02d}": [] for day in range(1, num_days + 1)}

        for order in orders:
            order_data = order.to_dict()
            date = order_data.get('date')
            total = order_data.get('total')

            # Ensure that total is converted to float
            try:
                total = float(total)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid total value: {total}")

            daily_totals[date].append(total)

        # Calculate the sum of averages for each day
        for day, totals in daily_totals.items():
            if totals:  # Only sum if there are totals for that day
                average = sum(totals) / len(totals)
                average_per_order[day] = average

        return average_per_order
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving orders: {str(e)}")

def assign_order_to_table_service(order_id: str, table_id: int, updated_order: dict):

    order_ref = db.collection("orders").document(str(order_id))
    table_ref = db.collection("tables").document(str(table_id))

    try:
        # 1) Actualiza la ORDEN
        order_ref.update(updated_order)

        try:
            # 2) Actualiza la MESA
            table_ref.update({
                "status": "BUSY",
                "order_id": int(order_id)
            })

        except Exception as e:
            # Rollback
            order_ref.update({
                "status": "INACTIVE",
                "tableNumber": 0
            })
            raise HTTPException(status_code=500, detail=f"Failed updating table: {e}")

        return {
            "message": "Order assigned successfully",
            "order_id": order_id,
            "table_id": table_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def assign_employee_to_order(order_id, uid):
    order_ref = db.collection("orders").document(order_id)
    #check if order exists
    order_doc = order_ref.get()
    if not order_doc.exists:
        return HTTPException(status_code=404, detail="Order not found")
    
    if order_doc.to_dict().get("employee") != "" and order_doc.to_dict().get("status") != "INACTIVE":
        raise HTTPException(status_code=400, detail="Order already has an assigned employee")
    try:
        order_ref.update({
            "employee": uid  # Assuming you store employee's UID in the 'employee' field
        })
        return {"message": "Employee assigned successfully"}
    except Exception as e:
        return {"error": str(e)}

def serve_order_item_service(order_id: str, item_id: str):
    try:
        order_ref = db.collection('orders').document(order_id)
        order_doc = order_ref.get()
        
        if not order_doc.exists:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order_data = order_doc.to_dict()
        items = order_data.get("orderItems", [])
        item_found = False
        
        for item in items:
            if item.get("item_id") == item_id:
                if item.get("served_at"):
                    return {"message": "Item already served"}
                item["served_at"] = now_ba_iso()
                item_found = True
                break
        
        if not item_found:
            raise HTTPException(status_code=404, detail="Item not found in this order")
        
        order_ref.update({"orderItems": items})
        
        return {"message": "Item served successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ... (El resto del archivo queda igual) ...

def get_wait_time_by_product_service():
    try:
        orders_ref = db.collection('orders').stream()
        product_waits = defaultdict(list)

        for order_doc in orders_ref:
            order = order_doc.to_dict()
            items = order.get("orderItems", [])

            for item in items:
                start_str = item.get("created_at")
                end_str = item.get("served_at")
                prod_name = item.get("product_name")

                if start_str and end_str and prod_name:
                    try:
                        start_dt = parse_any_iso_to_ba_naive(start_str)
                        end_dt = parse_any_iso_to_ba_naive(end_str)
                    except ValueError:
                        continue

                    wait_minutes = (end_dt - start_dt).total_seconds() / 60
                    if wait_minutes >= 0:
                        product_waits[prod_name].append(wait_minutes)

        averages = {
            name: round(sum(times) / len(times), 2)
            for name, times in product_waits.items()
        }
        return averages
    except Exception as e:
        return {"error": str(e)}


def get_wait_time_by_day_service():
    try:
        orders_ref = db.collection('orders').stream()
        daily_waits = defaultdict(list)

        for order_doc in orders_ref:
            order = order_doc.to_dict()
            order_date = order.get("date")
            items = order.get("orderItems", [])

            if not order_date:
                continue

            for item in items:
                start_str = item.get("created_at")
                end_str = item.get("served_at")
                if not (start_str and end_str):
                    continue
                try:
                    start_dt = parse_any_iso_to_ba_naive(start_str)
                    end_dt = parse_any_iso_to_ba_naive(end_str)
                except ValueError:
                    continue

                wait_minutes = (end_dt - start_dt).total_seconds() / 60
                if wait_minutes >= 0:
                    daily_waits[order_date].append(wait_minutes)

        averages = {}
        for day in sorted(daily_waits.keys()):
            times = daily_waits[day]
            averages[day] = round(sum(times) / len(times), 2)

        return averages
    except Exception as e:
        return {"error": str(e)}
