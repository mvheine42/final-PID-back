from datetime import date, timedelta
from typing import Dict, Union
from app.models.reservation import Reservation
from app.models.table import Table
from fastapi import HTTPException
from app.service.reservation_service import create_reservation, check_and_update_slot, get_available_slots
from app.service.table_service import associate_order_with_table, clean_table_service, close_table_service, get_tables_service, get_table_by_id, update_table_status
from app.service.reservation_table_service import assign_reservation_to_table_service, available_tables_for_reservation_service, reservation_by_id_service

def assign_reservation_to_table_controller(table_id: str, reservation_id: int):
    """
    Asocia la reserva `reservation_id` a la mesa `table_id`.
    Reglas:
      - Solo si la mesa está FREE.
      - Idempotente si ya está RESERVED por la misma reserva.
      - 409 si BUSY o RESERVED por otra reserva.
    """
    if not table_id or table_id.strip() == "":
        raise HTTPException(status_code=400, detail="table_id is required")
    
    if not reservation_id:
        raise HTTPException(status_code=400, detail="reservation_id is required")
    
    if not isinstance(reservation_id, int):
        raise HTTPException(status_code=400, detail="reservation_id must be an integer")
    
    if not isinstance(table_id, str):
        raise HTTPException(status_code=400, detail="table_id must be a string")
    
    if not table_id.isdigit():
        raise HTTPException(status_code=400, detail="table_id must be a positive integer")
    
    table = get_table_by_id(table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if table.status != "FREE":
        raise HTTPException(status_code=409, detail="Table is not FREE")
    
    reservation = reservation_by_id_service(reservation_id) 

    if table.current_reservation_id != 0 and table.current_reservation_id is not None:
        raise HTTPException(status_code=409, detail="Table is already RESERVED for another reservation")
    
    if table.current_reservation_id == reservation_id:
        return {
            "message": "Reservation already assigned to this table",
            "idempotent": True,
            "table_id": table_id,
            "reservation_id": reservation_id,
        }

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found") 
    

    result = assign_reservation_to_table_service(table_id, reservation_id)

    if "error" in result:
        err = result["error"]
        # Mapear errores a HTTP status
        if err in ("Table not found", "Reservation not found"):
            raise HTTPException(status_code=404, detail=err)
        if err in ("TABLE_BUSY", "TABLE_RESERVED_OTHER"):
            raise HTTPException(status_code=409, detail=err)
        # fallback
        raise HTTPException(status_code=400, detail=err)

    return result

def get_available_tables_for_reservation_controller(reservation_id: int):
    """
    Obtiene las mesas disponibles que pueden alojar la reserva `reservation_id`.
    """
    result = available_tables_for_reservation_service(reservation_id)

    if "error" in result:
        err = result["error"]
        if err == "Reservation not found":
            raise HTTPException(status_code=404, detail=err)
        raise HTTPException(status_code=400, detail=err)

    return result


