from app.db.firebase import db
from fastapi import HTTPException # <-- Importante, lo estabas usando

def get_tables_service():
    """
    Servicio para obtener todas las tables desde Firebase.
    """
    try:
        tables_ref = db.collection('tables').stream()
        tables = []
        for table in tables_ref:
            tab = table.to_dict()
            tab['id'] = table.id
            tables.append(tab)
        return tables
    except Exception as e:
        return {"error": str(e)}

def get_table_by_id(table_id: str):
    try:
        table_ref = db.collection('tables').document(table_id).get()
        if table_ref.exists:
            table = table_ref.to_dict()
            table['id'] = table_ref.id
            return table
        else:
            return None 
    except Exception as e:
        return {"error": str(e)}

def update_table_status(table_id: str, new_status: str):
        try:
            tables_ref = db.collection('tables').document(table_id)
            if tables_ref.get().exists:
                tables_ref.update({"status": new_status})
                return {"message": "Table status updated successfully"}
            else:
                return {"error": "Table not found"}
        except Exception as e:
            return {"error": str(e)}

# ---
# --- ¡AQUÍ ESTÁ LA FUNCIÓN CORREGIDA! ---
# ---
def associate_order_with_table(table_id: str, order_id: str):
    """
    Servicio para asociar una orden y poner la mesa en 'BUSY'.
    Acepta mesas que estén 'FREE' (cliente sin reserva)
    o 'RESERVED' (cliente con reserva que llegó).
    """
    try:
        table_ref = db.collection('tables').document(table_id)
        table_doc = table_ref.get()

        if not table_doc.exists:
            return {"error": "Table not found"}
        
        table_data = table_doc.to_dict()
        current_status = table_data.get("status")

        # --- ¡VALIDACIÓN MEJORADA! ---
        # Solo permitimos crear órdenes si la mesa está Libre o Reservada.
        if current_status not in ("FREE", "RESERVED"):
            return {"error": f"La mesa está '{current_status}' y no se le puede asignar una orden."}
        
        # --- ¡EL "PASE" LÓGICO Y EL BUG FIX! ---
        # Pasa a BUSY, asigna la orden, Y LIMPIA LA RESERVA.
        table_ref.update({
            "status": "BUSY",
            "order_id": str(order_id),
            "current_reservation_id": 0 # <-- ¡AQUÍ ESTÁ LA LÍNEA QUE TE FALTABA!
        })
        
        return {"message": "Order associated with table successfully"}

    except Exception as e:
        return {"error": str(e)}


def close_table_service(table_id: str):
    """
    Pasa la mesa de 'BUSY' a 'FINISHED' y limpia el order_id.
    """
    try:
        table_ref = db.collection('tables').document(str(table_id))
        table_doc = table_ref.get()

        if not table_doc.exists:
            raise HTTPException(status_code=404, detail="Table not found")

        table_data = table_doc.to_dict()
        if table_data.get("status") != "BUSY":
            raise HTTPException(status_code=400, detail=f"La mesa no está 'Ocupada', no se puede cerrar. Estado actual: {table_data.get('status')}")

        # --- NUEVA VALIDACIÓN DE SEGURIDAD ---
        order_id = table_data.get("order_id")
        if order_id:
            # Buscamos la orden asociada
            order_ref = db.collection('orders').document(str(order_id))
            order_doc = order_ref.get()
            
            if order_doc.exists:
                items = order_doc.to_dict().get("orderItems", [])
                # Filtramos los que NO tienen fecha de servido
                pending_items = [i for i in items if not i.get("served_at")]
                
                if pending_items:
                    # Si quedó alguno, explotamos (Error 400)
                    raise HTTPException(
                        status_code=400, 
                        detail=f"No se puede cerrar: Hay {len(pending_items)} ítems sin servir."
                    )
        # -------------------------------------

        table_ref.update({
            "status": "FINISHED",
            "order_id": 0
        })

        return {"message": "Table closed successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

def clean_table_service(table_id: str):
    """
    Pasa la mesa de 'FINISHED' a 'FREE'.
    """
    try:
        table_ref = db.collection('tables').document(str(table_id))
        table_doc = table_ref.get()

        if not table_doc.exists:
            raise HTTPException(status_code=404, detail="Table not found")

        # --- ¡VALIDACIÓN AÑADIDA! ---
        table_data = table_doc.to_dict()
        if table_data.get("status") != "FINISHED":
            raise HTTPException(status_code=400, detail=f"La mesa no está 'Terminada', no se puede limpiar. Estado actual: {table_data.get('status')}")

        table_ref.update({
            "status": "FREE",
            "order_id": 0
        })

        return {"message": "Table cleaned successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))