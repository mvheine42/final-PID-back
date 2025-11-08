from app.db.firebase import db

def get_next_id_from_existing():
    """
    Obtiene el próximo ID disponible en la colección 'reservation'.
    """
    try:
        # Obtener todos los documentos de la colección 'category'
        reservations = db.collection('reservations').stream()
        
        # Extraer los IDs existentes y convertirlos a enteros
        existing_ids = [int(reservation.id) for reservation in reservations if reservation.id.isdigit()]

        if existing_ids:
            # Encontrar el mayor ID existente y sumar 1
            next_id = max(existing_ids) + 1
        else:
            # Si no hay IDs, comenzamos desde 1
            next_id = 1

        return next_id
    except Exception as e:
        raise Exception(f"Error retrieving next ID from existing reservations: {str(e)}")
    

def create_reservation(reservation_data):
    """
    Crea una nueva categoría asegurando que el ID no colisione con uno existente.
    """
    try:
        # Obtén el siguiente ID disponible
        next_id = get_next_id_from_existing()
        # Crea el nuevo documento con el ID autoincremental
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
    try:
        # Generar ID único del slot (YYYY-MM-DD_HH:MM)
        slot_id = f"{reservation_date.isoformat()}_{reservation_time}"
        slot_ref = db.collection("reservation_slots").document(slot_id)
        slot_doc = slot_ref.get()

        if slot_doc.exists:
            slot_data = slot_doc.to_dict()
            used = slot_data.get("used", 0)
            capacity = slot_data.get("capacity", 5)

            if used >= capacity:
                return {"error": "Horario completo"}

            # Incrementar contador
            slot_ref.update({"used": used + 1})
        else:
            # Crear nuevo slot con un cupo inicial usado
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
    Devuelve una lista de horarios con cupo disponible.
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
                capacity = data.get("capacity", 5)
                remaining = max(0, capacity - used)
            else:
                remaining = 5  # Si no existe el documento, significa 0 usadas

            results.append({
                "time": t,
                "remaining": remaining
            })

        return results

    except Exception as e:
        return {"error": str(e)}