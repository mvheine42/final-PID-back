from typing import Any, Dict, List, Union
from fastapi import APIRouter, Depends

from app.models.user import UserLogin, UserRegister, UserForgotPassword, TokenData
from app.models.product import Product
from app.models.category import Category
from app.models.order import Order
from app.models.goal import Goal
from app.models.reservation import Reservation
from app.models.order_item import OrderItem
from app.models.table import Table

from app.controller.user_controller import (
    check_level_controller,
    get_top_level_status_controller,
    level_controller,
    login,
    ranking_controller,
    register,
    handle_forgot_password,
    get_user_by_id,
    delete_user_by_id,
    reset_monthly_points_controller,
    rewards_controller,
    token,
)
from app.controller.product_controller import (
    check_product_in_in_progress_orders_controller,
    get_products_by_category_controller,
    lower_stock_controller,
    register_new_product,
    get_products,
    update_product_price,
    update_product_description,
    delete_product_by_id,
    get_product_by_id,
    update_product_categories,
    add_food_calories,
    update_stock_controller,
)
from app.controller.category_controller import (
    delete_category_controller,
    get_all_categories,
    get_category_by_id_controller,
    register_new_category,
    update_category_name_controller,
    get_category_revenue_controller,
)
from app.controller.table_controller import (
    associate_order_with_table_controller,
    clean_table_controller,
    close_table_controller,
    get_table_by_id_controller,
    get_tables_controller,
    update_table_status_controller,
)
from app.controller.order_controller import (
    assign_employee_to_order_controller,
    assign_order_to_table_controller,
    delete_order_items_controller,
    get_average_per_order_controller,
    get_average_per_person_controller,
    get_months_revenue,
    register_new_order,
    finalize_order_controller,
    get_orders,
    get_order_controller,
    add_order_items_controller,
    serve_order_item_controller,
    get_wait_time_by_product_controller,
    get_wait_time_by_day_controller,
    register_external_order_controller
)
from app.controller.goal_controller import create_goal_controller, goals_controller
from app.controller.reservation_controller import (
    make_reservation_controller,
    get_available_slots_controller,
    get_reservations_by_day_controller,
    cancel_reservation_controller,
)
from app.controller.reservation_table_controller import (
    assign_reservation_to_table_controller,
    get_available_tables_for_reservation_controller,
)

from app.dependencies import verify_token as verify_token_header

router = APIRouter()


@router.get("/")
async def root():
    return "Server is running"


# ------------------------ AUTH --------------------------

# Login (PÚBLICO)
@router.post("/login/")
async def login_user(user: UserLogin):
    return login(user)


# Verificar token (PROTEGIDO por Bearer)
@router.post("/verify-token/")
async def verify_token_endpoint(token_data: TokenData, user=Depends(verify_token_header)):
    return token(token_data)


# ------------------------ USER --------------------------

# Registrar usuario (PÚBLICO)
@router.post("/register/")
async def register_user(user_register: UserRegister, user=Depends(verify_token_header)):
    return register(user_register, user)


# Recuperar contraseña (PÚBLICO)
@router.post("/forgot-password/")
async def forgot_password_user(user: UserForgotPassword):
    return handle_forgot_password(user)


# Ranking (PROTEGIDO)
@router.get("/ranking/")
async def ranking(user=Depends(verify_token_header)):
    return ranking_controller()


# Get user (PROTEGIDO)
@router.get("/users/{uid}")
async def get_user(uid: str, user=Depends(verify_token_header)):
    return get_user_by_id(uid, user)


# Delete user (PROTEGIDO)
@router.delete("/users/{uid}")
async def delete_user(uid: str, user=Depends(verify_token_header)):
    return delete_user_by_id(uid, user)


# ------------------------ PRODUCTO --------------------------

# Registrar producto (PROTEGIDO)
@router.post("/register-product")
async def register_product(product: Product, user=Depends(verify_token_header)):
    return register_new_product(product)


# Listar productos (PÚBLICO)
@router.get("/products")
async def products():
    return get_products()


# Actualizar precio producto (PROTEGIDO)
@router.put("/products/price/{product_id}/{new_price}")
async def update_price(product_id: str, new_price: str, user=Depends(verify_token_header)):
    return update_product_price(product_id, new_price)


# Actualizar descripción producto (PROTEGIDO)
@router.put("/products/description/{product_id}/{new_description}")
async def update_description(
    product_id: str,
    new_description: str,
    user=Depends(verify_token_header),
):
    return update_product_description(product_id, new_description)


# Actualizar categorías de un producto (PROTEGIDO)
@router.put("/products/categories/{product_id}/{new_category}")
async def update_categories(product_id: str, new_category: str, user=Depends(verify_token_header)):
    return update_product_categories(product_id, new_category)


# Eliminar producto (PROTEGIDO)
@router.delete("/products/{product_id}")
async def delete_product(product_id: str, user=Depends(verify_token_header)):
    return delete_product_by_id(product_id)


# Obtener producto por ID (PÚBLICO)
@router.get("/products/{product_id}")
async def get_product(product_id: str):
    return get_product_by_id(product_id)


# Chequear productos en órdenes en progreso (PROTEGIDO)
@router.get("/orders/products")
async def check_product_in_in_progress_orders(user=Depends(verify_token_header)):
    return check_product_in_in_progress_orders_controller()


# ------------------------ CATEGORIA --------------------------

# Listar categorías (PÚBLICO)
@router.get("/categories")
async def categories():
    return get_all_categories()


# Registrar categoría (PROTEGIDO) – segunda definición (misma ruta, mismo controlador)
@router.post("/register-category")
async def register_category_category_section(category: Category, user=Depends(verify_token_header)):
    return register_new_category(category)


# Obtener categoría por ID (PÚBLICO)
@router.get("/categories/{category_id}")
async def get_category(category_id: str):
    return get_category_by_id_controller(category_id)


# Eliminar categoría (PROTEGIDO)
@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user=Depends(verify_token_header)):
    return delete_category_controller(category_id)


# Actualizar nombre de categoría (PROTEGIDO)
@router.put("/categories/name/{category_id}/{new_name}")
async def update_category_name(category_id: str, new_name: str, user=Depends(verify_token_header)):
    return update_category_name_controller(category_id, new_name)

# Obtener productos por categoría (PÚBLICO)
@router.get("/categories/products/{category_id}")
async def get_products_by_category(category_id: str):
    return get_products_by_category_controller(category_id)


# ------------------------ TABLES --------------------------

# Listar mesas (PROTEGIDO)
@router.get("/tables")
async def tables(user=Depends(verify_token_header)):
    return get_tables_controller()


# Obtener mesa por ID (PROTEGIDO)
@router.get("/tables/{table_id}")
async def get_table(table_id: str, user=Depends(verify_token_header)):
    return get_table_by_id_controller(table_id)


# Actualizar estado de mesa (PROTEGIDO)
@router.put("/tables/status/{table_id}")
async def update_table_status(table_id: str, new_status: str, user=Depends(verify_token_header)):
    return update_table_status_controller(table_id, new_status)


# Asociar orden con mesa (PROTEGIDO)
@router.put("/tables/order/{table_id}")
async def associate_order_with_table(table_id: str, order_id: int, user=Depends(verify_token_header)):
    return associate_order_with_table_controller(table_id, order_id)


# Cerrar mesa (PROTEGIDO)
@router.put("/close-table/{table_id}")
async def close_table(
    table_id: str,
    body: Dict[str, Union[str, int]],
    user=Depends(verify_token_header),
):
    print(body)
    return close_table_controller(table_id, body)


# Limpiar mesa (PROTEGIDO)
@router.put("/clean-table/{table_id}")
async def clean_table(
    table_id: str,
    body: Dict[str, Union[str, int]],
    user=Depends(verify_token_header),
):
    print(body)
    return clean_table_controller(table_id, body)


# ------------------------ ORDER --------------------------

# Listar órdenes (PROTEGIDO)
@router.get("/orders")
async def orders(user=Depends(verify_token_header)):
    return get_orders()


# Registrar nueva orden (PROTEGIDO)
@router.post("/register-order")
async def register_order(order: Order, user=Depends(verify_token_header)):
    print(order)
    return register_new_order(order, user)

# PUBLIC — External order (sin token)
@router.post("/external-order")
async def register_external_order(order: Order):
    return register_external_order_controller(order)



# Asignar orden a mesa (PROTEGIDO)
@router.put("/assign-order-employee/{orderId}")
async def assign_employee_to_order(orderId: str, user=Depends(verify_token_header)):
    uid = user.get("uid")  # ← del token
    return assign_employee_to_order_controller(orderId, uid)



# Finalizar orden (PROTEGIDO) – primera definición
@router.put("/orders/finalize/{order_id}")
async def finalize_order(order_id: str, user=Depends(verify_token_header)):
    return finalize_order_controller(order_id)


# Obtener orden por ID (PROTEGIDO)
@router.get("/orders/{order_id}")
async def get_order(order_id: str, user=Depends(verify_token_header)):
    return get_order_controller(order_id)


# Actualizar items de la orden (PROTEGIDO)
@router.put("/orders/order-items/{order_id}")
async def update_order_items(
    order_id: str,
    body: Dict[str, Any],
    user=Depends(verify_token_header),
):
    print("Request body:", body)
    new_order_items = body.get("new_order_items", [])
    total = body.get("new_order_total", "")
    return add_order_items_controller(order_id, new_order_items, total)


# Eliminar ítems de una orden (PROTEGIDO)
@router.delete("/delete-order-item/{order_id}")
async def delete_order_item(order_id: str, order_items: List[str], user=Depends(verify_token_header)):
    return delete_order_items_controller(order_id, order_items)


# Finalizar orden (PROTEGIDO) – segunda definición
@router.put("/orders-finalize/{order_id}")
async def finalize_order_again(order_id: str, user=Depends(verify_token_header)):
    return finalize_order_controller(order_id)

# Asignar orden a mesa (PROTEGIDO)
@router.put("/assign-order-to-table/{order_id}/{table_id}")
async def assign_order_to_table(order_id: str, table_id: int, user=Depends(verify_token_header)):
    actor_uid = user.get("uid")
    return assign_order_to_table_controller(order_id, table_id)



# ------------------------ CALORIES / REPORTS --------------------------

# Agregar calorías a producto (PROTEGIDO)
@router.put("/add-calories/{product_id}/{calories}")
async def add_calories(product_id: str, calories: float, user=Depends(verify_token_header)):
    return add_food_calories(product_id, calories)


# Revenue por categoría (PROTEGIDO)
@router.get("/category-revenue")
async def get_category_revenue(user=Depends(verify_token_header)):
    return get_category_revenue_controller()


# Revenue mensual (PROTEGIDO)
@router.get("/monthly-revenue")
async def get_monthly_revenue(user=Depends(verify_token_header)):
    return get_months_revenue()


# Promedio por persona (PROTEGIDO)
@router.get("/average_per_person/{year}/{month}")
async def get_average_per_person(year: str, month: str, user=Depends(verify_token_header)):
    return get_average_per_person_controller(year, month)


# Promedio por orden (PROTEGIDO)
@router.get("/averare_per_order/{year}/{month}")
async def get_average_per_order(year: str, month: str, user=Depends(verify_token_header)):
    return get_average_per_order_controller(year, month)


# Promedio por persona mensual (PROTEGIDO)
@router.get("/average_per_person_monthly}")
async def get_average_per_person_monthly(user=Depends(verify_token_header)):
    return get_average_per_person_controller()

# ------------------------ STOCK --------------------------

# Actualizar stock (PROTEGIDO)
@router.put("/update-stock/{product_id}/{stock}")
async def update_stock(product_id: str, stock: str, user=Depends(verify_token_header)):
    return update_stock_controller(product_id, stock)


# Bajar stock (PROTEGIDO)
@router.put("/lower-stock/{product_id}/{stock}")
async def lower_stock(product_id: str, stock: str, user=Depends(verify_token_header)):
    return lower_stock_controller(product_id, stock)

# ------------------------ LEVEL / REWARDS --------------------------
# Rewards (PROTEGIDO)
@router.get("/rewards/{level_id}")
async def rewards(level_id: str, user=Depends(verify_token_header)):
    return rewards_controller(level_id)


# Level (PROTEGIDO)
@router.get("/level/{level_id}")
async def level(level_id: str, user=Depends(verify_token_header)):
    return level_controller(level_id)


# Check level (PROTEGIDO)
@router.get("/check-level/")
async def check_level(user=Depends(verify_token_header)):
    return check_level_controller(user)


# Top level status (PROTEGIDO)
@router.get("/top-level-status/{level_id}")
async def get_top_level_status(level_id: str, user=Depends(verify_token_header)):
    return get_top_level_status_controller(level_id)


# Reset monthly points (PROTEGIDO)
@router.get("/reset-monthly-points")
async def reset_monthly_points(user=Depends(verify_token_header)):
    return reset_monthly_points_controller()


# ------------------------ GOAL --------------------------

# Crear goal (PROTEGIDO)
@router.post("/create-goal")
async def create_goal(goal: Goal, user=Depends(verify_token_header)):
    return create_goal_controller(goal)


# Obtener goals por mes/año (PROTEGIDO)
@router.get("/goals/{month}/{year}")
async def goals(month: str, year: str, user=Depends(verify_token_header)):
    monthYear = month + "/" + year
    return goals_controller(monthYear)


# Asignar empleado a orden (PROTEGIDO)
"""@router.put("/assign-order-employee/{orderId}/{uid}")
async def assign_employee_to_order(orderId: int, uid: str, user=Depends(verify_token_header)):
    return assign_employee_to_order_controller(orderId, uid)"""


# ------------------------ RESERVATION --------------------------

# Crear reserva (PÚBLICO)
@router.post("/make-reservation")
async def make_reservation(reservation: Reservation):
    return make_reservation_controller(reservation)


# Slots disponibles (PÚBLICO)
@router.get("/available-slots/{reservation_date}")
async def get_available_slots(reservation_date: str):
    return get_available_slots_controller(reservation_date)


# Obtener reservas por día (PROTEGIDO)
@router.get("/reservations/day/{reservation_date}")
async def get_reservations_by_day(reservation_date: str, user=Depends(verify_token_header)):
    return get_reservations_by_day_controller(reservation_date)


# Cancelar reserva (PROTEGIDO)
@router.post("/cancel-reservation/{reservation_id}")
async def cancel_reservation(reservation_id: int, user=Depends(verify_token_header)):
    return cancel_reservation_controller(reservation_id)


# ------------------------ RESERVATION - TABLE --------------------------

# Asignar reserva a mesa (PROTEGIDO)
@router.post("/assign-reservation-to-table/{table_id}/{reservation_id}")
async def assign_reservation_to_table(
    table_id: str,
    reservation_id: int,
    user=Depends(verify_token_header),
):
    return assign_reservation_to_table_controller(table_id, reservation_id)


# Mesas disponibles para reserva (PROTEGIDO)
@router.get("/tables-available-for-reservation/{reservation_id}")
async def get_available_tables_for_reservation(reservation_id: int, user=Depends(verify_token_header)):
    return get_available_tables_for_reservation_controller(reservation_id)


# ------------------------ ORDER ITEMS / REPORTS --------------------------

# Servir ítem de orden (PROTEGIDO)
@router.put("/orders/serve-item/{order_id}/{item_id}")
async def serve_item(order_id: str, item_id: str, user=Depends(verify_token_header)):
    return serve_order_item_controller(order_id, item_id)


# Tiempo de espera por producto (PROTEGIDO)
@router.get("/reports/wait-time/products")
async def wait_time_by_product(user=Depends(verify_token_header)):
    return get_wait_time_by_product_controller()


# Tiempo de espera diario (PROTEGIDO)
@router.get("/reports/wait-time/daily")
async def wait_time_by_day(user=Depends(verify_token_header)):
    return get_wait_time_by_day_controller()
