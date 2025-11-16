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
    
        
        #Verify capacity and amountOfPeople and if reservation already has a table assigned
        reservation = res_doc.to_dict()
        existing_table_id = reservation.get("table_id", "")
        if existing_table_id not in ("", None, 0):
            # mismo id → podríamos tratarlo como idempotente, pero ya lo manejamos
            # más arriba con el estado de la mesa; acá sólo bloqueamos si es OTRA.
            if str(existing_table_id) != str(table_id):
                return {
                    "error": "Reservation already has a table assigned",
                    "current_table_id": existing_table_id,
                }

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

# en tu backend (firebase)
def available_tables_for_reservation_service(reservation_id: int):
    try:
        # 1) Leer reserva para conocer amountOfPeople y si ya tiene mesa
        res_ref = db.collection("reservations").document(str(reservation_id))
        res_doc = res_ref.get()
        if not res_doc.exists:
            return {"error": "Reservation not found"}
        
        reservation = res_doc.to_dict()
        party = int(reservation.get("amountOfPeople", 0))
        # Capturamos la mesa actual
        current_table_id = reservation.get("table_id") 

        # 2) Traer mesas FREE y filtrar por capacidad
        tables_ref = db.collection("tables").where("status", "==", "FREE")
        docs = tables_ref.stream()

        items = []
        # Usamos un set para no duplicar si la mesa actual también está 'FREE'
        seen_table_ids = set() 

        for doc in docs:
            data = doc.to_dict()
            if int(data.get("capacity", 0)) >= party:
                table_id_str = doc.id
                # Asumiendo que el ID de la tabla es numérico por tu frontend
                try: 
                    current_id = int(table_id_str)
                except ValueError:
                    current_id = table_id_str

                items.append({
                    "id": current_id,
                    "capacity": int(data.get("capacity", 0)),
                    "status": data.get("status", ""),
                    # ... (resto de campos que necesites en el dropdown)
                })
                seen_table_ids.add(table_id_str)

        # 3) AÑADIR LA MESA ACTUALMENTE ASIGNADA (si existe y no la hemos añadido ya)
        if current_table_id and str(current_table_id) not in seen_table_ids:
            table_ref = db.collection("tables").document(str(current_table_id))
            table_doc = table_ref.get()
            
            if table_doc.exists:
                data = table_doc.to_dict()
                try:
                    current_id = int(current_table_id)
                except ValueError:
                    current_id = str(current_table_id)

                items.append({
                    "id": current_id,
                    "capacity": int(data.get("capacity", 0)),
                    "status": data.get("status", ""),
                    # ... (resto de campos)
                })

        return items
    except Exception as e:
        return {"error": str(e)}
