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