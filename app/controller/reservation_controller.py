from datetime import date, timedelta
from app.models.reservation import Reservation
from fastapi import HTTPException
# --- ¡AÑADIMOS LA NUEVA FUNCIÓN DEL SERVICIO! ---
from app.service.reservation_service import (
    create_reservation, 
    check_and_update_slot, 
    get_available_slots, 
    get_reservations_by_day,
    cancel_reservation_service  # <-- ¡NUEVA!
)

from app.service.reservation_table_service import reservation_by_id_service

from datetime import datetime, timedelta
from fastapi import HTTPException
from zoneinfo import ZoneInfo


# IMPORTAR TUS FUNCIONES ─────────────────────────────────────
from app.date_time_utils import (
    now_ba,
    parse_any_iso_to_ba_naive,
)


def make_reservation_controller(reservation: Reservation):
    try:
        # 0) Normalizar la fecha usando tus utilidades
        raw_date = reservation.reservationDate

        # ───────────────────────────────────────────────
        # STRING → usar parse_any_iso_to_ba_naive
        # ───────────────────────────────────────────────
        if isinstance(raw_date, str):
            # ejemplo: "2025-12-03", "2025-12-03T00:00:00Z"
            dt_ba = parse_any_iso_to_ba_naive(raw_date)
            res_date = dt_ba.date()

        # ───────────────────────────────────────────────
        # datetime → pasarlo a str y parsear igual
        # ───────────────────────────────────────────────
        elif isinstance(raw_date, datetime):
            # convertir a ISO y reutilizar tu parser
            dt_ba = parse_any_iso_to_ba_naive(raw_date.isoformat())
            res_date = dt_ba.date()

        # ───────────────────────────────────────────────
        # date → ya está listo (assume BA)
        # ───────────────────────────────────────────────
        elif isinstance(raw_date, date):
            res_date = raw_date

        else:
            raise HTTPException(status_code=400, detail="Invalid reservationDate format")
        
        if reservation.customerName is None or not reservation.customerName.strip():
            raise HTTPException(status_code=400, detail="Customer name cannot be empty")

        name = reservation.customerName.strip()

        if name.isdigit():
            raise HTTPException(status_code=400, detail="Customer name cannot be only numbers")

        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Customer name is too short")

        if len(name) > 60:
            raise HTTPException(status_code=400, detail="Customer name is too long")

        # 1) Validación amountOfPeople
        if reservation.amountOfPeople < 1 or reservation.amountOfPeople > 4:
            raise HTTPException(
                status_code=400,
                detail="Amount of people must be between 1 and 4",
            )

        # 2) Fechas basadas en BA
        today_ba = now_ba().date()
        tomorrow_ba = today_ba + timedelta(days=1)
        one_month_later_ba = tomorrow_ba + timedelta(days=30)

        if res_date < tomorrow_ba or res_date > one_month_later_ba:
            raise HTTPException(
                status_code=400,
                detail="Reservation date must be between tomorrow and one month from tomorrow (BA time)",
            )

        
        # --- 3) Validación de horario ---
        if not reservation.reservationTime:
            raise HTTPException(status_code=400, detail="Reservation time is required")

        # Limpieza de espacios
        time_raw = reservation.reservationTime
        time_clean = str(time_raw).strip()

        # Normalización: si viene como "21:00:00" → cortar a "21:00"
        if len(time_clean) >= 5 and time_clean[2] == ":":
            time_clean = time_clean[:5]

        valid_times = ["12:00", "13:00", "21:00", "22:00"]

        if time_clean not in valid_times:
            raise HTTPException(
                status_code=400,
                detail="Reservation time must be one of: 12:00, 13:00, 21:00, 22:00",
            )
        # Reemplazar el valor limpio en el payload
        reservation.reservationTime = time_clean


        # 4) Chequeo de slot usando la fecha BA ya corregida
        slot_check = check_and_update_slot(res_date, reservation.reservationTime)
        if "error" in slot_check:
            raise HTTPException(status_code=400, detail=slot_check["error"])

        # 5) Armar payload final
        payload = reservation.dict()
        payload["reservationDate"] = res_date.isoformat()

        # 6) Crear reserva
        result = create_reservation(payload)

        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_available_slots_controller(reservation_date: str):
    """
    Controlador para obtener los horarios disponibles para una fecha dada.
    """
    try:
        # 1) Validación de formato básico YYYY-MM-DD
        if len(reservation_date) != 10 or reservation_date[4] != "-" or reservation_date[7] != "-":
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")

        # 2) Validar que sea una fecha REAL (no 2025-13-40)
        try:
            parsed_date = datetime.strptime(reservation_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida. Use una fecha real en formato YYYY-MM-DD.")

        # 3) Validar rango permitido (mañana hasta 1 mes desde mañana)
        today_ba = now_ba().date()
        tomorrow_ba = today_ba + timedelta(days=1)
        one_month_later_ba = tomorrow_ba + timedelta(days=30)

        if parsed_date < tomorrow_ba or parsed_date > one_month_later_ba:
            raise HTTPException(
                status_code=400,
                detail="Date must be between tomorrow and one month ahead."
            )

        # 4) Obtener slots
        slots = get_available_slots(reservation_date)
        return slots

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
def get_reservations_by_day_controller(reservation_date: str):
    try:
        if len(reservation_date) != 10 or reservation_date[4] != "-" or reservation_date[7] != "-":
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")
        response = get_reservations_by_day(reservation_date)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---
# --- ¡NUEVO ENDPOINT DE CANCELACIÓN! ---
# ---
def cancel_reservation_controller(reservation_id: int):
    """
    Controlador para cancelar una reserva y liberar todos sus recursos.
    """
    try: 
        reservation = reservation_by_id_service(reservation_id)
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
    
        result = cancel_reservation_service(reservation_id)
        
        if "error" in result:
            if result["error"] == "Reservation not found":
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))