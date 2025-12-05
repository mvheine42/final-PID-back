from app.db.firebase import db
from datetime import datetime

from app.date_time_utils import BA_TZ, now_ba

def assign_reservation_to_table_service(table_id: str, reservation_id: int):
    """
    Lógica de negocio para asociar reserva -> mesa.
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
            return {"error": f"Invalid table status '{status}' for assignment"}
        
        # --- 3) Verificar que la reserva exista ---
        res_ref = db.collection("reservations").document(str(reservation_id))
        res_doc = res_ref.get()
        if not res_doc.exists:
            return {"error": "Reservation not found"}
        
        # Definimos la variable reservation
        reservation = res_doc.to_dict()
        
        # Validación de fecha
        res_date_str = reservation.get("reservationDate")
        today_iso = now_ba().date().isoformat()
        if res_date_str != today_iso:
            return {
                "error": "RESERVATION_NOT_FOR_TODAY",
                "detail": f"La reserva es para el día {res_date_str}, no para hoy ({today_iso})."
            }
        
        # --- NUEVA VALIDACIÓN: 2 horas antes (TODO EN HORARIO BA) ---
        from datetime import timedelta
        
        res_time_str = reservation.get("reservationTime")  # e.g., "14:30" or "14:30:00"
        if not res_time_str:
            return {"error": "Reservation time is missing"}
        
        # Parsear la hora de la reserva (formato HH:MM o HH:MM:SS)
        try:
            if len(res_time_str.split(':')) == 2:
                res_time = datetime.strptime(res_time_str, "%H:%M").time()
            else:
                res_time = datetime.strptime(res_time_str, "%H:%M:%S").time()
        except ValueError:
            return {"error": f"Invalid reservation time format: {res_time_str}"}
        
        # Combinar fecha y hora de la reserva (naive, en BA)
        res_date = datetime.fromisoformat(res_date_str).date()
        res_datetime_naive = datetime.combine(res_date, res_time)
        
        # Convertir a aware en zona BA
        res_datetime_ba = res_datetime_naive.replace(tzinfo=BA_TZ)
        
        # Obtener hora actual en Buenos Aires (aware)
        current_datetime_ba = now_ba()
        
        # Calcular diferencia
        time_until_reservation = res_datetime_ba - current_datetime_ba
        
        # Validar que estemos dentro de las 2 horas previas
        if time_until_reservation > timedelta(hours=2):
            hours_remaining = time_until_reservation.total_seconds() / 3600
            return {
                "error": "TOO_EARLY_TO_ASSIGN",
                "detail": f"No se puede asignar mesa hasta 2 horas antes de la reserva. Faltan {hours_remaining:.1f} horas.",
                "reservation_time": res_time_str,
                "current_time_ba": current_datetime_ba.strftime("%H:%M:%S")
            }

        # --- Validaciones adicionales ---
        existing_table_id = reservation.get("table_id", "")
        if existing_table_id not in ("", None, 0):
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
        
        # Backlink en reservation
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
                try: 
                    current_id = int(table_id_str)
                except ValueError:
                    current_id = table_id_str

                items.append({
                    "id": current_id,
                    "capacity": int(data.get("capacity", 0)),
                    "status": data.get("status", ""),
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
                })

        return items
    except Exception as e:
        return {"error": str(e)}
    
def reservation_by_id_service(reservation_id: int):
    """
    Servicio para obtener una reserva por su ID.
    """
    try:
        res_ref = db.collection("reservations").document(str(reservation_id))
        res_doc = res_ref.get()
        if res_doc.exists:
            reservation = res_doc.to_dict()
            reservation["id"] = int(res_doc.id) if res_doc.id.isdigit() else res_doc.id
            return reservation
        else:
            return {"error": "Reservation not found"}
    except Exception as e:
        return {"error": str(e)}