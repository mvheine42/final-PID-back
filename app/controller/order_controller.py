from zoneinfo import ZoneInfo
from app.controller.user_controller import get_user_by_id
from fastapi import HTTPException
from typing import List, Dict
from datetime import datetime
import re
import pytz

from app.models.order import Order, OrderItem
from app.service.order_service import (
    assign_employee_to_order,
    assign_order_to_table_service,
    create_order,
    delete_order_items,
    finalize_order,
    get_months_revenue_service,
    get_order_by_id,
    get_all_orders,
    add_items_to_order,
    get_average_per_person_service,
    get_average_per_order_service,
    serve_order_item_service,
    get_wait_time_by_product_service,
    get_wait_time_by_day_service,
)

from app.service.product_service import product_by_id
from app.service.table_service import get_table_by_id
from app.service.reservation_service import get_reservation_by_id
from app.date_time_utils import now_ba_iso, today_ba_str, time_ba_str


# --- ZONA HORARIA ---
BA_TZ = pytz.timezone("America/Argentina/Buenos_Aires")


# --- VALIDACIONES AUXILIARES ---
def _parse_float(value: str, field_name: str) -> float:
    try:
        return float(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"{field_name} must be a number")

def _round2(x: float):
    return round(x + 1e-9, 2)


def _local_now_iso():
    """Devuelve la fecha/hora actual en Buenos Aires en ISO8601 (sin UTC)."""
    return datetime.now(BA_TZ).replace(microsecond=0).isoformat()


def _make_local_datetime(date_str: str, time_str: str):
    """Combina YYYY-MM-DD + HH:mm para generar un datetime localizado en BA."""
    dt_str = f"{date_str} {time_str}"
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    return BA_TZ.localize(dt)


# ---------------------------------------------------------------
#                   C R E A T E   O R D E R
# ---------------------------------------------------------------
def register_new_order(order: Order, user):
    """
    Crea una orden validando:
      - EXTERNAL (INACTIVE + sin mesa)
      - FREE (IN PROGRESS + mesa FREE)
      - RESERVED (IN PROGRESS + mesa RESERVED)
    Agrega SIEMPRE timestamps “Buenos Aires”:
      - date  (YYYY-MM-DD)
      - time  (HH:MM)
      - created_at (ISO BA)
      - para cada item: created_at (ISO BA) + served_at = None
    """

    status = (order.status or "").strip().upper()

    if status not in ("INACTIVE", "IN PROGRESS"):
        raise HTTPException(status_code=400,
            detail="status must be 'INACTIVE' or 'IN PROGRESS' on creation")

    # Validaciones básicas
    if order.amountOfPeople < 1:
        raise HTTPException(status_code=400,
            detail="amountOfPeople must be >= 1")

    if order.tableNumber < 0:
        raise HTTPException(status_code=400,
            detail="tableNumber must be >= 0")

    # Tipo de orden
    is_external = status == "INACTIVE"

    order_type = None
    table_data = None
    reservation_data = None

    # ---------------------------------------
    #        EXTERNAL ORDER
    # ---------------------------------------
    if is_external:

        if order.tableNumber != 0:
            raise HTTPException(status_code=400,
                detail="tableNumber must be 0 for external orders")
        
        if order.amountOfPeople not in (1, 2, 3, 4):
            raise HTTPException(status_code=400,
                detail="amountOfPeople must be between 1 and 4 for external orders")

        if (order.employee or "").strip():
            raise HTTPException(status_code=400,
                detail="employee must be empty for external orders")

        if not order.orderItems:
            raise HTTPException(status_code=400,
                detail="At least one order item is required for external orders")

        order_type = "EXTERNAL"

    # ---------------------------------------
    #        INTERNAL ORDER
    # ---------------------------------------
    else:
        if order.tableNumber <= 0:
            raise HTTPException(status_code=400,
                detail="tableNumber must be > 0 when status is IN PROGRESS")
        
        order.employee = user.get("uid")
        if not order.employee:
            raise HTTPException(status_code=400,
                detail="Employee is required for internal orders")

        table_data = get_table_by_id(str(order.tableNumber))
        if not table_data:
            raise HTTPException(status_code=404, detail="Table not found")

        table_status = (table_data.get("status") or "").strip().upper()
        current_res_id = table_data.get("current_reservation_id") or 0

        if table_status == "FREE":
            order_type = "FREE"

            if not order.orderItems:
                raise HTTPException(status_code=400,
                    detail="At least one order item is required for internal FREE orders")
            
            table_capacity = int(table_data.get("capacity") or 0)
            if order.amountOfPeople > table_capacity:
                raise HTTPException(
                    status_code=400,
                    detail=f"amountOfPeople ({order.amountOfPeople}) exceeds table capacity ({table_capacity})"
    )

        elif table_status == "RESERVED":
            order_type = "RESERVED"

            if not current_res_id:
                raise HTTPException(status_code=400,
                    detail="Table is RESERVED but has no current_reservation_id")

            reservation_data = get_reservation_by_id(current_res_id)
            if not reservation_data:
                raise HTTPException(status_code=404,
                    detail="Reservation not found for this table")

            res_people = reservation_data.get("amountOfPeople")
            if res_people is not None and res_people != order.amountOfPeople:
                raise HTTPException(status_code=400,
                    detail=f"amountOfPeople ({order.amountOfPeople}) does not match reservation amountOfPeople ({res_people})")

            if not order.orderItems:
                declared_total = _parse_float(order.total, "total")
                if declared_total != 0:
                    raise HTTPException(status_code=400,
                        detail="total must be 0 when no orderItems are provided in RESERVED orders")

        else:
            raise HTTPException(status_code=400,
                detail=f"Table status '{table_status}' is not valid for new orders")

    # -----------------------------------------------------
    #    VALIDACIÓN DE PRODUCTOS & TOTAL DECLARADO
    # -----------------------------------------------------
    computed_total = 0.0
    if order.orderItems:
        for raw_item in order.orderItems:
            prod_res = product_by_id(raw_item.product_id)
            if not isinstance(prod_res, dict) or "product" not in prod_res:
                raise HTTPException(status_code=404,
                    detail=f"Product with ID {raw_item.product_id} not found")

            prod = prod_res["product"]

            if raw_item.product_name != prod.get("name"):
                raise HTTPException(status_code=400,
                    detail=f"Product name for product ID {raw_item.product_id} does not match")

            if raw_item.product_price != str(prod.get("price")):
                raise HTTPException(status_code=400,
                    detail=f"Product price for product ID {raw_item.product_id} does not match")

            item_price = float(raw_item.product_price)
            computed_total += item_price * raw_item.amount

        declared_total = _parse_float(order.total, "total")
        if _round2(declared_total) != _round2(computed_total):
            raise HTTPException(status_code=400,
                detail="total does not match orderItems sum")

    # -----------------------------------------------------
    #     ARMAR PAYLOAD FINAL SIEMPRE EN BA
    # -----------------------------------------------------

    ba_now_iso = now_ba_iso()          # ISO con -03:00
    ba_date = today_ba_str()           # YYYY-MM-DD
    ba_time = time_ba_str()            # HH:MM

    data = order.dict()

    data["date"] = ba_date
    data["time"] = ba_time
    data["created_at"] = ba_now_iso

    # Timestamps de items
    for item in data.get("orderItems", []):
        item["created_at"] = ba_now_iso
        item["served_at"] = None

    # EXTERNAL ajustes
    if order_type == "EXTERNAL":
        data["tableNumber"] = 0
        data["employee"] = ""

    # Guardar
    resp = create_order(data)
    if isinstance(resp, dict) and "error" in resp:
        raise HTTPException(status_code=500, detail=resp["error"])
    
    return resp   # order_id

# ---------------------------------------------------------------
#                    OTROS ENDPOINTS
# ---------------------------------------------------------------
def finalize_order_controller(order_id: str):
    try:
        order = get_order_by_id(order_id)
        print(order)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        #order is a dict i need to get the status
        order_status = (order.get("status") or "").upper()

        if order_status != "IN PROGRESS":
            raise HTTPException(status_code=400, detail="Order is not in progress")

        return finalize_order(order_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_order_controller(order_id: str):
    try:
        order = get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_orders():
    try:
        return get_all_orders()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def add_order_items_controller(order_id: str, new_items_raw: List[dict], total: str):
    """
    Recibe SOLO los nuevos ítems que se agregan a la orden.
    - A cada ítem nuevo le setea created_at con hora actual BA.
    - Fuerza served_at = None.
    - No toca los ítems viejos (eso lo maneja el service).
    """
    local_now = now_ba_iso()

    if not isinstance(new_items_raw, list) or not new_items_raw:
        raise HTTPException(status_code=400, detail="new_items must be a list woth items")

    new_items: List[OrderItem] = []
    for raw in new_items_raw:
        data = raw.copy()
        data["created_at"] = local_now
        data["served_at"] = None
        new_items.append(OrderItem(**data))

    try:
        return add_items_to_order(order_id, new_items, total)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def delete_order_items_controller(order_id: str, order_items: List[str]):
    try:
        if not order_items:
            raise HTTPException(status_code=400, detail="order_items list cannot be empty")
        if not isinstance(order_items, list):
            raise HTTPException(status_code=400, detail="order_items must be a list")
        return delete_order_items(order_id, order_items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def assign_order_to_table_controller(order_id: str, table_id: int):

    # ----------- VALIDACIONES ORDEN ------------
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if (order.get("status") or "").upper() != "INACTIVE":
        raise HTTPException(status_code=400, detail="Order status is not INACTIVE")

    # ----------- VALIDACIONES MESA ------------
    table = get_table_by_id(str(table_id))
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if (table.get("status") or "").upper() != "FREE":
        raise HTTPException(status_code=400, detail="Table status is not FREE")

    # ----------- IDEMPOTENCIA ------------
    if (
        (order.get("status") or "").upper() == "IN PROGRESS"
        and int(order.get("tableNumber") or 0) == int(table_id)
        and (table.get("status") or "").upper() == "BUSY"
        and int(table.get("order_id") or 0) == int(order_id)
    ):
        return {"message": "Order already assigned to table"}

    # ----------- TIMESTAMP BA (USANDO SOLO TU FUNCIÓN) ------------
    ts = now_ba_iso()

    items = order.get("orderItems", [])
    for item in items:
        item["created_at"] = ts
        item["served_at"] = None

    # ----------- Payload final para service ------------
    updated_order = {
        "status": "IN PROGRESS",
        "tableNumber": int(table_id),
        "orderItems": items
    }

    return assign_order_to_table_service(order_id, table_id, updated_order)




def assign_employee_to_order_controller(order_id, uid):
    try:

        return assign_employee_to_order(str(order_id), uid)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=str(e)
        )



def serve_order_item_controller(order_id: str, item_id: str):
    try:
        if not order_id or not item_id:
            raise HTTPException(status_code=400, detail="order_id and item_id are required")
        
        if not isinstance(order_id, str) or not isinstance(item_id, str):
            raise HTTPException(status_code=400, detail="order_id and item_id must be strings")
        
        order = get_order_by_id(order_id) 
        if order.get("status") != "IN PROGRESS":
            raise HTTPException(status_code=400, detail="Order is not in progress")

        return serve_order_item_service(order_id, item_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_wait_time_by_product_controller():
    try:
        return get_wait_time_by_product_service()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_wait_time_by_day_controller():
    try:
        return get_wait_time_by_day_service()
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

def register_external_order_controller(order: Order):
    """
    Crea exclusivamente órdenes EXTERNAL (INACTIVE + sin mesa).
    Blindado:
      - Si intentan mandar IN PROGRESS -> 403
      - Si intentan mandar mesa != 0 -> se fuerza a 0
      - Si intentan mandar employee -> se fuerza a ""
      - Siempre timestamp BA (lo hace register_new_order)
    """

    incoming_status = (order.status or "").strip().upper()

    # Si mandan cualquier cosa que no sea INACTIVE → NO SE ACEPTA
    if incoming_status != "INACTIVE":
        raise HTTPException(
            status_code=403,
            detail="External orders cannot set status IN PROGRESS. Forbidden."
        )

    # Forzar EXTERNAL siempre
    order.status = "INACTIVE"
    order.tableNumber = 0
    order.employee = ""

    # El resto de validaciones y timestamps BA lo hace register_new_order
    return register_new_order(order, order.employee)
