from calendar import monthrange
from typing import Dict, List
from zoneinfo import ZoneInfo
from app.db.firebase import db
from app.service.table_service import get_table_by_id, update_table_status
from app.models.order_item import OrderItem
from datetime import datetime
from app.date_time_utils import now_ba, now_ba_iso, parse_any_iso_to_ba_naive
from app.service.table_service import associate_order_with_table_service
from fastapi import HTTPException
from collections import defaultdict

from datetime import datetime, timedelta

from app.service.user_service import user_by_id


def create_order(order_data):
    try:

        next_id = get_next_order_id_from_existing()
        # Crear una nueva orden
        orders_ref = db.collection('orders')
        new_order_ref = orders_ref.document(str(next_id))
        new_order_ref.set(order_data)  # Crear la nueva orden en Firebase
        # necesito que la mesa pase a BUSY y se asocie la orden
        #associate_order_with_table(order_data.get("tableNumber"), str(next_id))
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
        order_ref = db.collection('orders').document(str(order_id))
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
    """
    Calculates total revenue per month from all FINALIZED orders.
    Returns a dictionary with format: {"YYYY-MM": total_revenue}
    """
    try:
        # Only get FINALIZED orders for accurate revenue reporting
        finalized_orders = db.collection('orders').where('status', '==', 'FINALIZED').stream()
        monthly_revenue = {}
        
        for order_doc in finalized_orders:
            order_data = order_doc.to_dict()
            order_date = order_data.get('date')
            order_total = order_data.get('total')
            
            # Skip orders without date or total
            if not order_date or not order_total:
                continue
            
            # Extract year and month from date (YYYY-MM-DD)
            try:
                date_parts = order_date.split('-')
                if len(date_parts) >= 2:
                    year = date_parts[0]
                    month = date_parts[1]
                    month_year_key = f"{year}-{month}"
                    
                    # Accumulate revenue for this month
                    revenue_amount = float(order_total)
                    monthly_revenue[month_year_key] = monthly_revenue.get(month_year_key, 0) + revenue_amount
            except (ValueError, IndexError) as e:
                # Skip invalid dates
                continue
        
        return monthly_revenue
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving monthly revenue: {str(e)}")

def get_average_per_person_service(year: str, month: str) -> Dict[str, float]:
    """
    Calculates the average spending per person per day for a given month.
    For each order, divides total by amountOfPeople, then averages across all orders per day.
    """
    try:
        _, num_days = monthrange(int(year), int(month))
        
        # Initialize all days with 0
        average_per_person = {
            f"{year}-{int(month):02d}-{day:02d}": 0.0 
            for day in range(1, num_days + 1)
        }
        
        # Format month with leading zero for query
        month_padded = f"{int(month):02d}"
        start_date = f"{year}-{month_padded}-01"
        end_date = f"{year}-{month_padded}-{num_days:02d}"
        
        # Query orders within the specified month
        orders = db.collection('orders') \
            .where('date', '>=', start_date) \
            .where('date', '<=', end_date) \
            .stream()
        
        # Dictionary to accumulate per-person values per day
        daily_per_person_values = defaultdict(list)
        
        for order_doc in orders:
            order_data = order_doc.to_dict()
            order_date = order_data.get('date')
            order_total = order_data.get('total')
            amount_of_people = order_data.get('amountOfPeople')
            
            # Skip invalid data
            if not order_date or not order_total or not amount_of_people:
                continue
            
            # Convert and validate
            try:
                total_amount = float(order_total)
                num_people = int(amount_of_people)
                
                # Only process if we have at least 1 person
                if num_people > 0:
                    per_person_amount = total_amount / num_people
                    daily_per_person_values[order_date].append(per_person_amount)
            except (ValueError, TypeError, ZeroDivisionError):
                continue
        
        # Calculate the average of all per-person amounts for each day
        for day_key, per_person_amounts in daily_per_person_values.items():
            if per_person_amounts:
                # Average all the per-person amounts for this day
                average_per_person[day_key] = round(
                    sum(per_person_amounts) / len(per_person_amounts), 
                    2
                )
        
        return average_per_person
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error calculating average per person: {str(e)}"
        )

def get_average_per_order_service(year: str, month: str) -> Dict[str, float]:
    """
    Calculates the average order total per day for a given month.
    Returns daily averages for all orders (not just FINALIZED).
    """
    try:
        _, num_days = monthrange(int(year), int(month))
        
        # Initialize all days with 0
        average_per_order = {
            f"{year}-{int(month):02d}-{day:02d}": 0.0 
            for day in range(1, num_days + 1)
        }
        
        # Format month with leading zero for query
        month_padded = f"{int(month):02d}"
        start_date = f"{year}-{month_padded}-01"
        end_date = f"{year}-{month_padded}-{num_days:02d}"
        
        # Query orders within the specified month
        orders = db.collection('orders') \
            .where('date', '>=', start_date) \
            .where('date', '<=', end_date) \
            .stream()
        
        # Dictionary to accumulate totals per day
        daily_totals = defaultdict(list)
        
        for order_doc in orders:
            order_data = order_doc.to_dict()
            order_date = order_data.get('date')
            order_total = order_data.get('total')
            
            if not order_date or not order_total:
                continue
            
            # Convert total to float
            try:
                total_amount = float(order_total)
                daily_totals[order_date].append(total_amount)
            except (ValueError, TypeError):
                continue
        
        # Calculate average for each day that has orders
        for day_key, totals in daily_totals.items():
            if totals:
                average_per_order[day_key] = round(sum(totals) / len(totals), 2)
        
        return average_per_order
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating average per order: {str(e)}")

# SERVICE
def assign_order_to_table_service(order_id: str, table_id: int):
    try:
        # Get fresh data
        order = get_order_by_id(order_id)
        table = get_table_by_id(str(table_id))
        
        # Basic existence checks
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        
        # Normalize statuses for comparison
        order_status = (order.get("status") or "").strip().upper()
        table_status = (table.get("status") or "").strip().upper()
        order_table_num = int(order.get("tableNumber") or 0)
        table_order_id = int(table.get("order_id") or 0)
        
        # IDEMPOTENCY CHECK - if already assigned correctly, return success
        if (order_status == "IN PROGRESS" 
            and order_table_num == int(table_id)
            and table_status == "BUSY"
            and table_order_id == int(order_id)):
            return {"message": "Order assigned to table successfully"}
        
        # Business validations
        if not order.get("orderItems"):
            raise HTTPException(status_code=400, detail="ORDER HAS NO ITEMS")
        
        if order_status != "INACTIVE":
            raise HTTPException(
                status_code=400, 
                detail=f"Order status must be INACTIVE, current status: {order_status}"
            )
        
        if order_table_num != 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Order is already assigned to table {order_table_num}"
            )
        
        # REMOVED: Employee check - orders can have employees assigned before table assignment
        # This allows the workflow: Employee -> assigns themselves -> then assigns to table
        
        if table_status != "FREE":
            raise HTTPException(
                status_code=400, 
                detail=f"Table status must be FREE, current status: {table_status}"
            )
        
        # Prepare timestamp and items
        ts = now_ba_iso()
        items = order.get("orderItems", [])
        for item in items:
            item["created_at"] = ts
            item["served_at"] = None
        
        # Get references
        order_ref = db.collection('orders').document(order_id)
        table_ref = db.collection('tables').document(str(table_id))
        
        # Update order first
        order_ref.update({
            "status": "IN PROGRESS",
            "tableNumber": int(table_id),
            "orderItems": items
        })
        
        try:
            # Update table second
            table_ref.update({
                "order_id": int(order_id),
                "status": "BUSY"
            })
        except Exception as table_error:
            # Rollback order if table update fails
            try:
                order_ref.update({
                    "status": "INACTIVE",
                    "tableNumber": 0
                })
            except Exception as rollback_error:
                print(f"CRITICAL: Rollback failed: {rollback_error}")
            
            raise HTTPException(
                status_code=500, 
                detail=f"Failed updating table: {str(table_error)}"
            )
        
        return {"message": "Order assigned to table successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

def assign_employee_to_order_service(order_id: str, uid: str):
    try:
        # Get order reference and document
        order_ref = db.collection("orders").document(order_id)
        order_doc = order_ref.get()
        
        # Check if order exists
        if not order_doc.exists:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order_data = order_doc.to_dict()
        
        # Normalize values
        order_status = (order_data.get("status") or "").strip().upper()
        current_employee = order_data.get("employee")
        
        # IDEMPOTENCY: If this employee is already assigned, return success
        if current_employee == uid:
            return {"message": "Employee assigned successfully"}
        
        # Check if order already has a different employee assigned
        if current_employee and str(current_employee).strip():
            raise HTTPException(
                status_code=400, 
                detail=f"Order already has an assigned employee: {current_employee}"
            )
        
        # Check if order status is INACTIVE (only INACTIVE orders can be assigned)
        if order_status != "INACTIVE":
            raise HTTPException(
                status_code=400, 
                detail=f"Can only assign employees to INACTIVE orders. Current status: {order_status}"
            )
        
        user_data = user_by_id(uid)
        if not user_data or "error" in user_data:
            raise HTTPException(status_code=500, detail="Error fetching employee data")
        
        # Assign employee
        order_ref.update({
            "employee": uid,
            "employee_name": user_data.get("name")
        })
        
        return {"message": "Employee assigned successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error assigning employee: {str(e)}"
        )


def serve_order_item_service(order_id: str, item_id: str):
    try:
        order_ref = db.collection('orders').document(order_id)
        order_doc = order_ref.get()
        
        if not order_doc.exists:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order_data = order_doc.to_dict()
        items = order_data.get("orderItems", [])
        item_found = False

        # --- Obtener hora BA actual coherente con created_at ---
        now_iso = now_ba_iso()                                      # ISO BA
        now_dt = parse_any_iso_to_ba_naive(now_iso)                # NAIVE BA

        for item in items:
            if item.get("item_id") == item_id:

                # Idempotente
                if item.get("served_at"):
                    return {"message": "Item already served"}

                # created_at obligatorio
                created_str = item.get("created_at")
                if not created_str:
                    raise HTTPException(500, "Item has no created_at timestamp")

                try:
                    created_dt = parse_any_iso_to_ba_naive(created_str)
                except Exception:
                    raise HTTPException(500, "Invalid created_at timestamp format")

                # Validación tiempo BA
                if now_dt < created_dt:
                    raise HTTPException(
                        400,
                        "Serve time cannot be earlier than created_at"
                    )

                # Guardar serve_at
                item["served_at"] = now_iso
                item_found = True
                break

        if not item_found:
            raise HTTPException(404, "Item not found in this order")
        
        # Persistir update
        order_ref.update({"orderItems": items})
        
        return {"message": "Item served successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))



    
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


# ============================================
# SERVICES CON FILTRO (mes/año específico)
# ============================================

def get_wait_time_by_product_filtered_service(month: str, year: str):
    try:
        orders_ref = db.collection('orders').stream()
        product_waits = defaultdict(list)
        
        # Convertir "null" string a None para filtrado opcional
        filter_month = None if month == 'null' else int(month)
        filter_year = None if year == 'null' else int(year)
        
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
                    
                    # FILTRO POR MES (si está definido)
                    if filter_month is not None and start_dt.month != filter_month:
                        continue
                    
                    # FILTRO POR AÑO (si está definido)
                    if filter_year is not None and start_dt.year != filter_year:
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

def get_wait_time_by_day_filtered_service(month: str, year: str):
    try:
        orders_ref = db.collection('orders').stream()
        
        # Convertir "null" string a None para filtrado opcional
        filter_month = None if month == 'null' else int(month)
        filter_year = None if year == 'null' else int(year)
        
        # Si hay filtro de mes pero NO de año, agrupamos por día del mes (1-31)
        # Si hay filtro de año (con o sin mes), agrupamos por fecha completa
        if filter_month is not None and filter_year is None:
            # CASO: Agosto + All Years → Agrupar por día del mes (Aug 1, Aug 2, etc.)
            daily_waits = defaultdict(list)  # Key será "Aug 1", "Aug 2", etc.
            month_name = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][filter_month]
            
            for order_doc in orders_ref:
                order = order_doc.to_dict()
                items = order.get("orderItems", [])
                
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
                    
                    # Filtrar solo por mes
                    if start_dt.month != filter_month:
                        continue
                    
                    wait_minutes = (end_dt - start_dt).total_seconds() / 60
                    if wait_minutes >= 0:
                        day_key = f"{month_name} {start_dt.day}"
                        daily_waits[day_key].append(wait_minutes)
            
            # Calcular promedios y ordenar por día
            averages = {}
            for day in range(1, 32):  # Días 1-31
                day_key = f"{month_name} {day}"
                if day_key in daily_waits:
                    times = daily_waits[day_key]
                    averages[day_key] = round(sum(times) / len(times), 2)
            
            return averages
            
        else:
            # CASO NORMAL: Fecha completa (cuando hay filtro de año o sin filtros específicos)
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
                    
                    # FILTRO POR MES (si está definido)
                    if filter_month is not None and start_dt.month != filter_month:
                        continue
                    
                    # FILTRO POR AÑO (si está definido)
                    if filter_year is not None and start_dt.year != filter_year:
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
                
                # FILTRO POR MES/AÑO
                if start_dt.month != int(month) or start_dt.year != int(year):
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