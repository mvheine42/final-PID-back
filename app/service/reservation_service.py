from app.db.firebase import db
from google.cloud import firestore # <-- ¡IMPORTANTE! Para el Increment

def get_next_id_from_existing():
    """
    Obtiene el próximo ID disponible en la colección 'reservation'.
    """
    try:
        reservations = db.collection('reservations').stream()
        existing_ids = [int(reservation.id) for reservation in reservations if reservation.id.isdigit()]

        if existing_ids:
            next_id = max(existing_ids) + 1
        else:
            next_id = 1

        return next_id
    except Exception as e:
        raise Exception(f"Error retrieving next ID from existing reservations: {str(e)}")
    

def create_reservation(reservation_data):
    """
    Crea una nueva categoría asegurando que el ID no colisione con uno existente.
    """
    try:
        next_id = get_next_id_from_existing()
        new_reservation_ref = db.collection('reservations').document(str(next_id))
        new_reservation_ref.set(reservation_data)

        return {"message": "Reservation added successfully", "id": next_id}
    except Exception as e:
        return {"error": str(e)}
    
def check_and_update_slot(reservation_date, reservation_time):
    """
    Verifica y actualiza el cupo disponible para una fecha y hora determinada.
    Devuelve un dict con 'success' o 'error'.
    """
    #
    # --- ACORDATE: Esta función sigue teniendo el "race condition" ---
    # --- ¡Para la v2.0 acordate de ponerle la Transacción! ---
    #
    try:
        slot_id = f"{reservation_date.isoformat()}_{reservation_time}"
        slot_ref = db.collection("reservation_slots").document(slot_id)
        slot_doc = slot_ref.get()

        if slot_doc.exists:
            slot_data = slot_doc.to_dict()
            used = slot_data.get("used", 0)
            capacity = slot_data.get("capacity", 5)

            if used >= capacity:
                return {"error": "Horario completo"}
            slot_ref.update({"used": used + 1})
        else:
            slot_ref.set({
                "date": reservation_date.isoformat(),
                "time": reservation_time,
                "capacity": 5,
                "used": 1
            })

        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
    
def get_available_slots(reservation_date):
    """
    Obtiene los horarios disponibles para una fecha dada.
    """
    try:
        allowed_times = ["12:00", "13:00", "21:00", "22:00"]
        results = []
        for t in allowed_times:
            slot_id = f"{reservation_date}_{t}"
            slot_ref = db.collection("reservation_slots").document(slot_id)
            slot_doc = slot_ref.get()
            if slot_doc.exists:
                data = slot_doc.to_dict()
                used = data.get("used", 0)
                capacity = data.get("capacity", 4)
                remaining = max(0, capacity - used)
            else:
                remaining = 4
            results.append({
                "time": t,
                "remaining": remaining
            })
        return results
    except Exception as e:
        return {"error": str(e)}
    
def get_reservations_by_day(reservation_date: str):
    """
    Servicio para obtener las reservas de un día específico (YYYY-MM-DD).
    """
    try:
        reservations_ref = db.collection("reservations")
        query = reservations_ref.where("reservationDate", "==", reservation_date)
        docs = query.stream()
        reservations = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = int(doc.id) if doc.id.isdigit() else doc.id
            data["table_id"] = data.get("table_id", "")
            reservations.append(data)
        return reservations
    except Exception as e:
        return {"error": f"Error al obtener reservas para {reservation_date}: {str(e)}"}

# ---
# --- ¡NUEVA FUNCIÓN DE CANCELACIÓN! ---
# ---
def cancel_reservation_service(reservation_id: int):
    """
    Libera todos los recursos de una reserva (mesa y cupo) y la borra.
    """
    try:
        res_ref = db.collection("reservations").document(str(reservation_id))
        res_doc = res_ref.get()

        if not res_doc.exists:
            return {"error": "Reservation not found"}
        
        reservation = res_doc.to_dict()

        # --- 1. Liberar la Mesa (si estaba asignada) ---
        table_id = reservation.get("table_id")
        if table_id not in (None, "", 0):
            table_ref = db.collection("tables").document(str(table_id))
            table_doc = table_ref.get()
            if table_doc.exists:
                table_data = table_doc.to_dict()
                # Solo la liberamos si la mesa sigue reservada para ESTA reserva
                if table_data.get("current_reservation_id") == reservation_id:
                    table_ref.update({
                        "status": "FREE",
                        "current_reservation_id": 0
                    })

        # --- 2. Devolver el Cupo al Slot ---
        res_date = reservation.get("reservationDate")
        res_time = reservation.get("reservationTime")
        
        if res_date and res_time:
            slot_id = f"{res_date}_{res_time}"
            slot_ref = db.collection("reservation_slots").document(slot_id)
            slot_doc = slot_ref.get()
            
            if slot_doc.exists and slot_doc.to_dict().get("used", 0) > 0:
                # Usamos Increment para restar 1 de forma segura
                slot_ref.update({
                    "used": firestore.Increment(-1)
                })

        # --- 3. Borrar la Reserva ---
        res_ref.delete()

        return {"message": f"Reservation {reservation_id} cancelled successfully."}

    except Exception as e:
        return {"error": str(e)}
    

def get_reservation_by_id(reservation_id: int):
    """
    Devuelve la reserva como dict o None.
    Nunca lanza excepción interna (solo HTTPException si se pide).
    """
    try:
        ref = db.collection("reservations").document(str(reservation_id))
        doc = ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["id"] = reservation_id
        return data
    except Exception as e:
        return {"error": str(e)}
