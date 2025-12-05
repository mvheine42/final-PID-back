from typing import Dict, Union
from app.service.table_service import associate_order_with_table_service, clean_table_service, close_table_service, get_tables_service, get_table_by_id, update_table_status
from app.models.table import Table
from fastapi import HTTPException
from app.service.order_service import get_order_by_id


def get_tables_controller():
    try:
        result = get_tables_service()

        # Si el service devolvió {"error": "..."} → levantar 500
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(
                status_code=500,
                detail="INTERNAL_ERROR_FETCHING_TABLES"
            )
        return result
    except Exception:
        # Si cualquier excepción se escapa del service
        raise HTTPException(
            status_code=500,
            detail="INTERNAL_ERROR_FETCHING_TABLES"
        )

from fastapi import HTTPException

def get_table_by_id_controller(table_id: str):

    # Validación mínima de ID
    if not table_id or not str(table_id).strip():
        raise HTTPException(status_code=400, detail="Invalid table ID")
    try:
        table = get_table_by_id(table_id)

        # El service devolvió error → 500
        if isinstance(table, dict) and "error" in table:
            raise HTTPException(
                status_code=500,
                detail="INTERNAL_ERROR_FETCHING_TABLE"
            )
        # La mesa no existe
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        return table
    except HTTPException:
        # Relevamos las HTTPException que tiramos arriba
        raise
    except Exception:
        # Cualquier otra excepción inesperada
        raise HTTPException(
            status_code=500,
            detail="INTERNAL_ERROR_FETCHING_TABLE"
        )


def update_table_status_controller(table_id: str, new_status: str):
    try:
        response = update_table_status(table_id, new_status)
        if isinstance(response, dict) and "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

async def get_order_for_table(table_id: str):
    # Fetch the table
    table = await get_table_by_id(table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Check if there is an associated order
    order = await get_order_by_id(table.order_id)  # Adjust this function based on your order retrieval logic
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check if the order status is 'in progress'
    if order.status != 'in progress':
        raise HTTPException(status_code=400, detail="Order is not in progress")

    return order

def associate_order_with_table_controller(table_id: str, order_id: int):

    table = get_table_by_id(table_id)
    
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    if isinstance(table, dict) and "error" in table:
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR_FETCHING_TABLE")
    
    current_status = table.get("status")
    
    if current_status not in ("FREE", "RESERVED"):
        raise HTTPException(
            status_code=400, 
            detail=f"Table is '{current_status}' and cannot be assigned an order."
        )
    
    order = get_order_by_id(order_id)

    # 1. Si vino None → no existe
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2. Si el service devolvió {"error": "..."} → error interno
    if isinstance(order, dict) and "error" in order:
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR_FETCHING_ORDER")

    # 3. AHORA EL EDITOR YA SABE QUE ORDER ES DICT → .get() FUNCIONA
    if order.get("status") != "IN PROGRESS":
        raise HTTPException(status_code=400, detail="Order is not IN_PROGRESS")
    
    response = associate_order_with_table_service(table_id, order_id)
    
    if 'error' in response:
        raise HTTPException(status_code=400, detail=response['error'])
    
    return response

def close_table_controller(table_id: str, body: Dict[str, Union[str, int]]):
    try:
        status = body.get("status")
        order_id = body.get("order_id")
        if status != "FINISHED":
            raise HTTPException(status_code=400, detail="Status must be 'FINISHED'")
        if order_id != 0:
            raise HTTPException(status_code=400, detail="Order ID must be 0")
        
        table = get_table_by_id(table_id)
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        
        if table.get("status") != "BUSY":
            raise HTTPException(status_code=400, detail="Table is not BUSY")
        
        order = get_order_by_id(table.get("order_id"))
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if int(table.get("order_id", 0)) == 0:
            raise HTTPException(status_code=400, detail="No order associated with the table")
        
        order_items = order.get("orderItems", [])
        if not all(item.get("served_at") for item in order_items):
            raise HTTPException(status_code=400, detail="Not all items in the order have been served")
        
        response = close_table_service(table_id)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def clean_table_controller(table_id: str, body: Dict[str, Union[str, int]]):
    try:
        status = body.get("status")
        order_id = body.get("order_id")
        if status != "FREE":
            raise HTTPException(status_code=400, detail="Status must be 'FREE'")
        if order_id != 0:
            raise HTTPException(status_code=400, detail="Order ID must be 0")
        table = get_table_by_id(table_id)
        if isinstance(table, dict) and "error" in table:
            raise HTTPException(status_code=500, detail=table["error"])
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        if table.get("status") != "FINISHED":
            raise HTTPException(
                status_code=409,
                detail=f"Table must be 'FINISHED' to clean (current: '{table.get('status')}')"
            )
        response = clean_table_service(table_id)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))