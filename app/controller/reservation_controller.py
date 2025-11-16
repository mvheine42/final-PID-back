from datetime import date, timedelta
from app.models.reservation import Reservation
from fastapi import HTTPException
from app.service.reservation_service import create_reservation, check_and_update_slot, get_available_slots, get_reservations_by_day

def make_reservation_controller(reservation: Reservation):
    try:
        # 1) Validaciones
        if reservation.amountOfPeople < 1 or reservation.amountOfPeople > 4:
            raise HTTPException(status_code=400, detail="Amount of people must be between 1 and 4")

        today = date.today()
        tomorrow = today + timedelta(days=1)
        one_month_later = tomorrow + timedelta(days=30)
        if reservation.reservationDate < tomorrow or reservation.reservationDate > one_month_later:
            raise HTTPException(status_code=400, detail="Reservation date must be between tomorrow and one month from tomorrow")

        valid_times = ["12:00", "13:00", "21:00", "22:00"]
        if not reservation.reservationTime:
            raise HTTPException(status_code=400, detail="Reservation time is required")
        if reservation.reservationTime not in valid_times:
            raise HTTPException(status_code=400, detail="Reservation time must be one of: 12:00, 13:00, 21:00, 22:00")
        
        slot_check = check_and_update_slot(reservation.reservationDate, reservation.reservationTime)
        if "error" in slot_check:
            raise HTTPException(status_code=400, detail=slot_check["error"])
        # 2) Preparar payload para Firestore (serializar fecha)
        payload = reservation.dict()  # o reservation.model_dump() si usás Pydantic v2
        payload["reservationDate"] = payload["reservationDate"].isoformat()  # <-- clave

        # 3) Guardar
        result = create_reservation(payload)  # este devuelve {"message": "...", "id": ...}

        # 4) Manejo de respuesta del service
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result  # {"message": "Reservation added successfully", "id": next_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_available_slots_controller(reservation_date: str):
    """
    Controlador para obtener los horarios disponibles para una fecha dada.
    """
    try:
        # --- AÑADIR ESTA VALIDACIÓN ---
        if len(reservation_date) != 10 or reservation_date[4] != "-" or reservation_date[7] != "-":
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")
        # --- FIN DE LA VALIDACIÓN ---
        
        slots = get_available_slots(reservation_date)
        return slots
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