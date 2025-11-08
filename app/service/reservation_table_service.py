from app.db.firebase import db

def assign_reservation_to_table_service(table_id: str, reservation_id: int):
    """
    Lógica de negocio para asociar reserva -> mesa.
    Cambios:
      - tables/{table_id}: status = "RESERVED", current_reservation_id = reservation_id
      - (opcional recomendado) reservations/{reservation_id}: table_id = table_id
    """
    try:
        # --- 1) Leer mesa ---
        table_ref = db.collection("tables").document(str(table_id))
        table_doc = table_ref.get()
        if not table_doc.exists:
            return {"error": "Table not found"}

        table = table_doc.to_dict()
        status = table.get("status")
        current_reservation_id = table.get("current_reservation_id", 0)

        # --- 2) Validar estado de mesa ---
        if status == "BUSY":
            return {"error": "Table is busy"}

        if status == "RESERVED":
            # idempotente: ya está asignada a la misma reserva
            if current_reservation_id == reservation_id:
                return {
                    "message": "Reservation already assigned to this table",
                    "idempotent": True,
                    "table_id": str(table_id),
                    "reservation_id": reservation_id,
                }
            # reservada por otra
            if current_reservation_id not in (0, None):
                return {
                    "error": "Table is already booked for another reservation",
                    "current_reservation_id": current_reservation_id,
                }

        # En este punto debe ser FREE o RESERVED sin reserva previa
        if status not in ("FREE", "RESERVED"):
            # Por si existieran otros estados
            return {"error": f"Invalid table status '{status}' for assignment"}

        # --- 3) Verificar que la reserva exista ---
        res_ref = db.collection("reservations").document(str(reservation_id))
        res_doc = res_ref.get()
        if not res_doc.exists:
            return {"error": "Reservation not found"}
        
        #Verify capacity and amountOfPeople
        reservation = res_doc.to_dict()
        amount_of_people = reservation.get("amountOfPeople", 0)
        table_capacity = table.get("capacity", 0)
        if amount_of_people > table_capacity:
            return {"error": "La mesa no tiene capacidad suficiente para la reserva"}
        
        # --- 4) Persistir cambios (mesa -> RESERVED) ---
        table_ref.update({
            "status": "RESERVED",
            "current_reservation_id": int(reservation_id),
        })

        # (Opcional recomendado) backlink en reservation:
        # si tu doc id de mesa es numérico, lo guardamos como int; si no, como str.
        try:
            numeric_table_id = int(table_id)
            res_ref.update({"table_id": numeric_table_id})
        except ValueError:
            res_ref.update({"table_id": str(table_id)})

        return {
            "message": "Reservation assigned to table successfully",
            "table_id": str(table_id),
            "reservation_id": reservation_id,
            "table_status": "RESERVED",
        }

    except Exception as e:
        return {"error": str(e)}
