from calendar import monthrange
from datetime import datetime
from typing import Dict, List
from app.db.firebase import db
from app.models.goal import Goal
from fastapi import HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
from google.cloud import firestore
from app.service.category_service import get_categories
from app.service.product_service import products
from google.cloud.firestore_v1 import FieldFilter

def create_goal(goal):
    try:
        # Obtener el siguiente ID disponible
        next_id = get_next_goal_id()

        # Convertir los datos del goal a un formato compatible
        goal_data = goal.dict(by_alias=True, exclude_unset=True)

        # Si la fecha ya es una cadena, no se hace nada

        # Handle category_id gracefully (make sure it's None or a valid string)
        if goal_data.get('categoryId') is None:
            goal_data['categoryId'] = None
        elif not isinstance(goal_data.get('categoryId'), str):
            raise Exception("category_id must be a string or None")

        # Guardar el objetivo en Firestore
        new_goal_ref = db.collection('goals').document(str(next_id))
        new_goal_ref.set(goal_data)

        return next_id
    except Exception as e:
        return {"error": str(e)}
        
def get_next_goal_id():
    """
    Obtiene el próximo ID disponible en la colección 'products'.
    """
    try:
        # Obtener todos los documentos de la colección 'products'
        goals = db.collection('goals').stream()

        # Extraer los IDs existentes y convertirlos a enteros
        existing_ids = [int(goal.id) for goal in goals if goal.id.isdigit()]

        if existing_ids:
            # Encontrar el mayor ID existente y sumar 1
            next_id = max(existing_ids) + 1
        else:
            # Si no hay IDs, comenzamos desde 1
            next_id = 1

        return next_id
    except Exception as e:
        raise Exception(f"Error retrieving next ID from existing goals: {str(e)}")


def get_category_product_mapping():
    """
    Devuelve un dict donde cada key es un category_id
    y el value es una string con todos los product_ids separados por coma.
    Ejemplo:
        {"1": "10,12", "2": "3"}
    """
    try:
        # Obtener productos del servicio existente
        response = products()  
        product_list = response.get("products", [])

        category_to_products = defaultdict(set)

        for product in product_list:
            product_id = product.get("id")
            category_field = product.get("category", "")

            if not product_id:
                continue  # si no tiene id, lo ignoramos

            # Dividimos los IDs de categorías
            category_ids = [c.strip() for c in category_field.split(",") if c.strip()]

            for category_id in category_ids:
                category_to_products[category_id].add(product_id)

        # Convertimos sets → strings ordenadas
        result = {
            category_id: ",".join(sorted(product_ids))
            for category_id, product_ids in category_to_products.items()
        }

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def goals(monthYear: str) -> List[dict]:
    """
    Calcula las metas del mes (MM/YY), sumando el actualIncome correspondiente:
      - Si categoryId es None → suma total de la orden
      - Si categoryId existe → suma por productos de esa categoría

    NO usa índices compuestos:
      - Filtra por status en Firestore
      - Filtra por rango de fechas en Python

    Incluye su propio parser interno para convertir la fecha de las órdenes.
    """
    try:

        # =======================================================
        # 1) PARSEADOR INTERNO DE FECHAS (integrado acá mismo)
        # =======================================================
        def _parse_order_date(value):
            """
            Convierte el campo 'date' de una orden a datetime.
            Soporta:
              - firestore.Timestamp
              - string: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY
            Devuelve None si no se puede parsear.
            """
            if value is None:
                return None

            # Firestore Timestamp
            if hasattr(value, "to_datetime"):
                try:
                    return value.to_datetime()
                except Exception:
                    return None

            # Strings
            if isinstance(value, str):
                value = value[:10]  # cortar si viene con hora
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
                    try:
                        return datetime.strptime(value, fmt)
                    except Exception:
                        continue

            return None

        # =======================================================
        # 2) PARSEAR MES objetivo (MM/YY)
        # =======================================================
        try:
            start_date = datetime.strptime(monthYear, "%m/%y")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid monthYear format. Use MM/YY.")

        # Último día del mes (23:59:59)
        tmp = start_date.replace(day=28) + timedelta(days=4)
        end_date = tmp.replace(day=1) - timedelta(days=1)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # =======================================================
        # 3) Obtener metas del mes
        # =======================================================
        goals_stream = db.collection("goals").where(
            filter=FieldFilter("date", "==", monthYear)
        ).stream()

        # Mapeo categoría → product_ids
        category_products = get_category_product_mapping()

        # =======================================================
        # 4) Cargar TODAS las órdenes FINALIZED (una sola vez)
        # =======================================================
        orders_stream = db.collection("orders").where(
            filter=FieldFilter("status", "==", "FINALIZED")
        ).stream()

        orders_cache = []
        for doc in orders_stream:
            od = doc.to_dict()
            orders_cache.append({
                "date": od.get("date"),
                "total": float(od.get("total", 0) or 0),
                "items": od.get("orderItems", [])
            })

        # =======================================================
        # 5) Procesar CADA goal
        # =======================================================
        output = []

        for goal_doc in goals_stream:
            g = goal_doc.to_dict()
            g["id"] = goal_doc.id

            category_id = g.get("categoryId")
            actual_income = 0.0

            # Productos asociados si es meta por categoría
            if category_id:
                product_list = category_products.get(str(category_id), "")
                associated_products = {p.strip() for p in product_list.split(",") if p.strip()}
            else:
                associated_products = None  # meta general

            # ---------------------------------------------------
            # 6) SUMAR INGRESOS según tipo de meta
            # ---------------------------------------------------
            for od in orders_cache:

                # Fecha de la orden
                order_dt = _parse_order_date(od["date"])
                if not order_dt:
                    continue
                if not (start_date <= order_dt <= end_date):
                    continue

                # META GENERAL
                if associated_products is None:
                    actual_income += od["total"]
                    continue

                # META POR CATEGORÍA
                for item in od["items"] or []:
                    product_id = item.get("product_id")
                    if not product_id:
                        continue
                    if str(product_id) not in associated_products:
                        continue

                    price = float(item.get("product_price", 0) or 0)
                    amount = float(item.get("amount", 0) or 0)
                    actual_income += price * amount

            # ===================================================
            # 7) Persistir y preparar salida
            # ===================================================
            g["actualIncome"] = round(actual_income, 2)

            db.collection("goals").document(goal_doc.id).update({
                "actualIncome": g["actualIncome"]
            })

            output.append(g)

        return output

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

