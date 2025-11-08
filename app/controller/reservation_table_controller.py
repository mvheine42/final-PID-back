from datetime import date, timedelta
from typing import Dict, Union
from app.models.reservation import Reservation
from app.models.table import Table
from fastapi import HTTPException
from app.service.reservation_service import create_reservation, check_and_update_slot, get_available_slots
from app.service.table_service import associate_order_with_table, clean_table_service, close_table_service, get_tables_service, get_table_by_id, update_table_status
from app.service.reservation_table_service import assign_reservation_to_table_service

def assign_reservation_to_table_controller(table_id: str, reservation_id: int):
    """
    Asocia la reserva `reservation_id` a la mesa `table_id`.
    Reglas:
      - Solo si la mesa está FREE.
      - Idempotente si ya está RESERVED por la misma reserva.
      - 409 si BUSY o RESERVED por otra reserva.
    """
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


