from typing import Any, Dict, List, Union
from fastapi import APIRouter
from app.models.user import UserLogin, UserRegister, UserForgotPassword, TokenData
from app.models.product import Product
from app.models.category import Category
from app.models.order import Order
from app.models.goal import Goal
from app.models.reservation import Reservation
from app.controller.user_controller import check_level_controller, get_top_level_status_controller, level_controller, login, ranking_controller, register, handle_forgot_password, get_user_by_id, delete_user_by_id, reset_monthly_points_controller, rewards_controller, token
from app.controller.product_controller import check_product_in_in_progress_orders_controller, get_products_by_category_controller, lower_stock_controller, register_new_product, get_products, update_product_price, update_product_description, delete_product_by_id, get_product_by_id, update_product_categories, add_food_calories, update_stock_controller
from app.controller.category_controller import delete_category_controller, get_all_categories, get_category_by_id_controller, register_new_category, update_category_name_controller, get_category_revenue_controller
from app.controller.table_controller import associate_order_with_table_controller, clean_table_controller, close_table_controller, get_table_by_id_controller, get_tables_controller, update_table_status_controller
from app.controller.order_controller import assign_employee_to_order_controller, assign_order_to_table_controller, delete_order_items_controller, get_average_per_order_controller, get_average_per_person_controller, get_months_revenue, register_new_order, finalize_order_controller, get_orders, get_order_controller, add_order_items, serve_order_item_controller, get_wait_time_by_product_controller, get_wait_time_by_day_controller
from app.controller.goal_controller import create_goal_controller, goals_controller
from app.controller.reservation_controller import make_reservation_controller, get_available_slots_controller, get_reservations_by_day_controller, cancel_reservation_controller
from app.controller.reservation_table_controller import assign_reservation_to_table_controller, get_available_tables_for_reservation_controller
from app.models.order_item import OrderItem
from app.models.table import Table

router = APIRouter()

@router.get("/")
async def root():
    return "Server is running"

# Ruta para iniciar sesión
@router.post("/login/")
async def login_user(user: UserLogin):
    return login(user)


@router.post("/verify-token/")
async def verify_token(token_data: TokenData):
    return token(token_data)

#------------------------USER--------------------------
# Ruta para registrar un nuevo usuario
@router.post("/register/")
async def register_user(user: UserRegister):
    return register(user)

# Ruta para recuperación de contraseña
@router.post("/forgot-password/")
async def forgot_password_user(user: UserForgotPassword):
    return handle_forgot_password(user)

@router.get("/ranking/")
async def ranking():
    return ranking_controller()

@router.get("/users/{uid}")
async def get_user(uid: str):
    return get_user_by_id(uid)

@router.delete("/users/{uid}")
async def delete_user(uid: str):
    return delete_user_by_id(uid)

#------------------------PRODUCTO--------------------------

#validaciones
@router.post("/register-product")
async def register_product(product: Product):
    print(product)
    return register_new_product(product) 

@router.get("/products")
async def products():
    return get_products()

@router.put("/products/price/{product_id}/{new_price}")
async def update_price(product_id: str, new_price: str):
    return update_product_price(product_id, new_price)

@router.put("/products/description/{product_id}/{new_description}")
async def update_description(product_id: str, new_description: str):
    return update_product_description(product_id, new_description)

@router.put("/products/categories/{product_id}/{new_category}")
async def update_categories(product_id: str, new_category: str):
    return update_product_categories(product_id, new_category)

@router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    return delete_product_by_id(product_id)

@router.get("/products/{product_id}")
async def get_product(product_id: str):
    return get_product_by_id(product_id)

@router.post("/register-category")
async def register_category(category: Category):
    return register_new_category(category)

@router.get("/categories/products/{category_id}")
async def get_products_by_category(category_id: str):
    return get_products_by_category_controller(category_id)

@router.get("/orders/products")
async def check_product_in_in_progress_orders():
    return check_product_in_in_progress_orders_controller()


#------------------------CATEGORIA--------------------------

@router.get("/categories")
async def categories():
    return get_all_categories()

@router.post("/register-category")
async def register_category(category: Category):
    return register_new_category(category) 

@router.get("/categories/{category_id}")
async def get_category(category_id: str):
    return get_category_by_id_controller(category_id)

@router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    return delete_category_controller(category_id)

@router.put("/categories/name/{category_id}/{new_name}")
async def update_category_name(category_id: str, new_name: str):
    return update_category_name_controller(category_id, new_name)


'''@router.get("/default-categories")
async def get_default_categories():
    return get_default_categories_controller()'''

#-----------------TABLES------------------------
@router.get("/tables")
async def tables():
    return get_tables_controller()

@router.get("/tables/{table_id}")
async def get_table(table_id: str):
    return get_table_by_id_controller(table_id)

@router.put("/tables/status/{table_id}")
async def update_table_status(table_id: str, new_status: str):
    return update_table_status_controller(table_id, new_status)

@router.put("/tables/order/{table_id}")
async def associate_order_with_table(table_id: str, order_id: int):
    return associate_order_with_table_controller(table_id, order_id)

@router.put("/close-table/{table_id}")
async def close_table(table_id: str, body: Dict[str, Union[str, int]]):
    print(body)
    return close_table_controller(table_id, body)

@router.put("/clean-table/{table_id}")
async def clean_table(table_id: str, body: Dict[str, Union[str, int]]):
    print(body)
    return clean_table_controller(table_id, body)

#----------------ORDER-------------------------

@router.get("/orders")
async def orders():
    return get_orders()

@router.post("/register-order")
async def register_order(order: Order):
    print(order)
    return register_new_order(order) 

@router.put("/asign-order-table/{order_id}/{table_id}")
async def assign_order_to_table(order_id: str, table_id: int):
    return assign_order_to_table_controller(order_id, table_id)

@router.put("/orders/finalize/{order_id}")
async def finalize_order(order_id: str):
    return finalize_order_controller(order_id)

@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    return get_order_controller(order_id)

@router.put("/orders/order-items/{order_id}")
async def update_order_items(order_id: str, body: Dict[str, Any]):
    print("Request body:", body)
    new_order_items = body.get("new_order_items", [])
    total = body.get("new_order_total", "")
    return add_order_items(order_id, new_order_items, total)

@router.delete("/delete-order-item/{order_id}")
async def delete_order_item(order_id: str, order_items: List[str]):
    return delete_order_items_controller(order_id, order_items)

@router.put("/orders-finalize/{order_id}")
async def finalize_order(order_id: str):
    return finalize_order_controller(order_id)

#-----------------CALORIES----------------------

@router.put("/add-calories/{product_id}/{calories}")
async def add_calories(product_id: str, calories: float):
    return add_food_calories(product_id, calories)

@router.get("/category-revenue")
async def get_category_revenue():
    return get_category_revenue_controller()

@router.get("/monthly-revenue")
async def get_monthly_revenue():
    return get_months_revenue()

@router.get("/average_per_person/{year}/{month}")
async def get_average_per_person(year: str, month: str):
    return get_average_per_person_controller(year, month)

@router.get("/averare_per_order/{year}/{month}")
async def get_average_per_order(year: str, month: str):
    return get_average_per_order_controller(year, month)

@router.get("/average_per_person_monthly}")
async def get_average_per_person():
    return get_average_per_person_controller()

@router.put("/update-stock/{product_id}/{stock}")
async def update_stock(product_id: str, stock: str):
    return update_stock_controller(product_id, stock)

@router.put("/lower-stock/{product_id}/{stock}")
async def lower_stock(product_id: str, stock: str):
    return lower_stock_controller(product_id, stock)

@router.get("/rewards/{level_id}")
async def rewards(level_id: str):
    return rewards_controller(level_id)

@router.get("/level/{level_id}")
async def level(level_id: str):
    return level_controller(level_id)

@router.get("/check-level/{uid}")
async def check_level(uid: str):
    return check_level_controller(uid)

@router.get("/top-level-status/{level_id}")
async def get_top_level_status(level_id: str):
    return get_top_level_status_controller(level_id)

@router.get("/reset-monthly-points")
async def reset_monthly_points():
    return reset_monthly_points_controller()

#------------------------------------GOAL-------------------------------------------

@router.post("/create-goal")
async def create_goal(goal: Goal):
    return create_goal_controller(goal)

@router.get("/goals/{month}/{year}")
async def goals(month: str, year: str):
    monthYear = month + '/' + year
    return goals_controller(monthYear)

@router.put("/assign-order-employee/{orderId}/{uid}")
async def assign_employee_to_order(orderId: int, uid: str):
    return assign_employee_to_order_controller(orderId, uid)

#-----------------------------RESERVATION-------------------------------------

@router.post("/make-reservation")
async def make_reservation(reservation: Reservation):
    return make_reservation_controller(reservation)

@router.get("/available-slots/{reservation_date}")
async def get_available_slots(reservation_date: str):
    return get_available_slots_controller(reservation_date)

@router.get("/reservations/day/{reservation_date}")
async def get_reservations_by_day(reservation_date: str):
    return get_reservations_by_day_controller(reservation_date)

@router.post("/cancel-reservation/{reservation_id}")
async def cancel_reservation(reservation_id: int):
    return cancel_reservation_controller(reservation_id)

#-----------------------------RESERVATION-TABLE-------------------------------------

@router.post("/assign-reservation-to-table/{table_id}/{reservation_id}")
async def assign_reservation_to_table(table_id: str, reservation_id: int):
    return assign_reservation_to_table_controller(table_id, reservation_id)

@router.get("/tables-available-for-reservation/{reservation_id}")
async def get_available_tables_for_reservation(reservation_id: int):
    return get_available_tables_for_reservation_controller(reservation_id)

#-----------------------------ORDER-ITEMS-------------------------------------

@router.put("/orders/serve-item/{order_id}/{item_id}")
async def serve_item(order_id: str, item_id: str):
    return serve_order_item_controller(order_id, item_id)

@router.get("/reports/wait-time/products")
async def wait_time_by_product():
    return get_wait_time_by_product_controller()

@router.get("/reports/wait-time/daily")
async def wait_time_by_day():
    return get_wait_time_by_day_controller()