from typing import Any, Dict, List, Union
from fastapi import APIRouter, Depends

from app.models.user import UserLogin, UserRegister, UserForgotPassword, TokenData
from app.models.product import Product
from app.models.category import Category
from app.models.order import Order
from app.models.goal import Goal
from app.models.reservation import Reservation

from app.controller.user_controller import (
    check_level_controller,
    check_level_user_controller,
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
)
from app.controller.order_controller import (
    assign_employee_to_order_controller,
    assign_order_to_table_controller,
    delete_order_items_controller,
    get_average_per_order_controller,
    get_average_per_person_controller,
    get_months_revenue,
    get_wait_time_by_day_filtered_controller,
    get_wait_time_by_product_filtered_controller,
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


@router.post("/login/")
async def login_user(user: UserLogin):
    return login(user)


@router.post("/verify-token/")
async def verify_token_endpoint(token_data: TokenData):
    return token(token_data)


# ------------------------ USER --------------------------

@router.post("/register/")
async def register_user(user_register: UserRegister, user=Depends(verify_token_header)):
    return register(user_register, user)


@router.post("/forgot-password/")
async def forgot_password_user(user: UserForgotPassword):
    return handle_forgot_password(user)

@router.get("/ranking/")
async def ranking(user=Depends(verify_token_header)):
    return ranking_controller()

@router.get("/users/{uid}")
async def get_user(uid: str, user=Depends(verify_token_header)):
    return get_user_by_id(uid, user)


@router.delete("/users/{uid}")
async def delete_user(uid: str, user=Depends(verify_token_header)):
    return delete_user_by_id(uid, user)


# ------------------------ PRODUCTO --------------------------

@router.post("/register-product")
async def register_product(product: Product, user=Depends(verify_token_header)):
    return register_new_product(product)

@router.get("/products")
async def products():
    return get_products()

@router.put("/products/price/{product_id}/{new_price}")
async def update_price(product_id: str, new_price: str, user=Depends(verify_token_header)):
    return update_product_price(product_id, new_price)

@router.put("/products/description/{product_id}/{new_description}")
async def update_description(
    product_id: str,
    new_description: str,
    user=Depends(verify_token_header),
):
    return update_product_description(product_id, new_description)


@router.put("/products/categories/{product_id}/{new_category}")
async def update_categories(product_id: str, new_category: str, user=Depends(verify_token_header)):
    return update_product_categories(product_id, new_category)

@router.delete("/products/{product_id}")
async def delete_product(product_id: str, user=Depends(verify_token_header)):
    return delete_product_by_id(product_id)

@router.get("/products/{product_id}")
async def get_product(product_id: str):
    return get_product_by_id(product_id)

@router.get("/orders/products")
async def check_product_in_in_progress_orders(user=Depends(verify_token_header)):
    return check_product_in_in_progress_orders_controller()

@router.get("/categories")
async def categories():
    return get_all_categories()


@router.post("/register-category")
async def register_category_category_section(category: Category, user=Depends(verify_token_header)):
    return register_new_category(category)

@router.get("/categories/{category_id}")
async def get_category(category_id: str):
    return get_category_by_id_controller(category_id)

@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user=Depends(verify_token_header)):
    return delete_category_controller(category_id)

@router.put("/categories/name/{category_id}/{new_name}")
async def update_category_name(category_id: str, new_name: str, user=Depends(verify_token_header)):
    return update_category_name_controller(category_id, new_name)

@router.get("/categories/products/{category_id}")
async def get_products_by_category(category_id: str):
    return get_products_by_category_controller(category_id)


# ------------------------ TABLES --------------------------

@router.get("/tables")
async def tables(user=Depends(verify_token_header)):
    return get_tables_controller()


@router.get("/tables/{table_id}")
async def get_table(table_id: str, user=Depends(verify_token_header)):
    return get_table_by_id_controller(table_id)


"""@router.put("/tables/status/{table_id}")
async def update_table_status(table_id: str, new_status: str, user=Depends(verify_token_header)):
    return update_table_status_controller(table_id, new_status)"""

@router.put("/tables/order/{table_id}")
async def associate_order_with_table(table_id: str, order_id: int, user=Depends(verify_token_header)):
    return associate_order_with_table_controller(table_id, order_id)


@router.put("/close-table/{table_id}")
async def close_table(table_id: str, body: Dict[str, Union[str, int]], user=Depends(verify_token_header)):
    return close_table_controller(table_id, body)

@router.put("/clean-table/{table_id}")
async def clean_table(table_id: str, body: Dict[str, Union[str, int]], user=Depends(verify_token_header)):
    return clean_table_controller(table_id, body)


# ------------------------ ORDER --------------------------

@router.get("/orders")
async def orders(user=Depends(verify_token_header)):
    return get_orders()

@router.post("/register-order")
async def register_order(order: Order, user=Depends(verify_token_header)):
    return register_new_order(order, user)

@router.post("/external-order")
async def register_external_order(order: Order):
    return register_external_order_controller(order)


@router.put("/assign-order-employee/{orderId}")
async def assign_employee_to_order(orderId: str, user=Depends(verify_token_header)):
    uid = user.get("uid")
    return assign_employee_to_order_controller(orderId, uid)

@router.put("/orders-finalize/{order_id}")
async def finalize_order(order_id: str, user=Depends(verify_token_header)):
    return finalize_order_controller(order_id)


@router.get("/orders/{order_id}")
async def get_order(order_id: str, user=Depends(verify_token_header)):
    return get_order_controller(order_id)


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


@router.delete("/delete-order-item/{order_id}")
async def delete_order_item(order_id: str, order_items: List[str], user=Depends(verify_token_header)):
    return delete_order_items_controller(order_id, order_items)


@router.put("/assign-table-and-order/{order_id}/{table_id}")
async def assign_order_to_table(order_id: str, table_id: int, user=Depends(verify_token_header)):
    return assign_order_to_table_controller(order_id, table_id)



# ------------------------ CALORIES / REPORTS --------------------------

@router.put("/add-calories/{product_id}/{calories}")
async def add_calories(product_id: str, calories: float, user=Depends(verify_token_header)):
    return add_food_calories(product_id, calories)


@router.get("/category-revenue")
async def get_category_revenue(user=Depends(verify_token_header)):
    return get_category_revenue_controller()

@router.get("/monthly-revenue")
async def get_monthly_revenue(user=Depends(verify_token_header)):
    return get_months_revenue()

@router.get("/average-per-person/{year}/{month}")
async def get_average_per_person(year: str, month: str, user=Depends(verify_token_header)):
    return get_average_per_person_controller(year, month)


@router.get("/average-per-order/{year}/{month}")
async def get_average_per_order(year: str, month: str, user=Depends(verify_token_header)):
    return get_average_per_order_controller(year, month)


# ------------------------ STOCK --------------------------

@router.put("/update-stock/{product_id}/{stock}")
async def update_stock(product_id: str, stock: str, user=Depends(verify_token_header)):
    return update_stock_controller(product_id, stock)

@router.put("/lower-stock/{product_id}/{stock}")
async def lower_stock(product_id: str, stock: str, user=Depends(verify_token_header)):
    return lower_stock_controller(product_id, stock)

# ------------------------ LEVEL / REWARDS --------------------------

@router.get("/rewards/{level_id}")
async def rewards(level_id: str, user=Depends(verify_token_header)):
    return rewards_controller(level_id)

@router.get("/level/{level_id}")
async def level(level_id: str, user=Depends(verify_token_header)):
    return level_controller(level_id)

@router.get("/check-level/")
async def check_level(user=Depends(verify_token_header)):
    return check_level_controller(user)

@router.get("/check-level-user/{uid}")
async def check_level_user(uid: str, user=Depends(verify_token_header)):
    return check_level_user_controller(uid)

@router.get("/top-level-status/{level_id}")
async def get_top_level_status(level_id: str, user=Depends(verify_token_header)):
    return get_top_level_status_controller(level_id)


@router.get("/reset-monthly-points")
async def reset_monthly_points(user=Depends(verify_token_header)):
    return reset_monthly_points_controller()


# ------------------------ GOAL --------------------------

@router.post("/create-goal")
async def create_goal(goal: Goal, user=Depends(verify_token_header)):
    return create_goal_controller(goal)

@router.get("/goals/{month}/{year}")
async def goals(month: str, year: str, user=Depends(verify_token_header)):
    monthYear = month + "/" + year
    return goals_controller(monthYear)


"""@router.put("/assign-order-employee/{orderId}/{uid}")
async def assign_employee_to_order(orderId: int, uid: str, user=Depends(verify_token_header)):
    return assign_employee_to_order_controller(orderId, uid)"""


# ------------------------ RESERVATION --------------------------

@router.post("/make-reservation")
async def make_reservation(reservation: Reservation):
    return make_reservation_controller(reservation)


@router.get("/available-slots/{reservation_date}")
async def get_available_slots(reservation_date: str):
    return get_available_slots_controller(reservation_date)


@router.get("/reservations/day/{reservation_date}")
async def get_reservations_by_day(reservation_date: str, user=Depends(verify_token_header)):
    return get_reservations_by_day_controller(reservation_date)

@router.post("/cancel-reservation/{reservation_id}")
async def cancel_reservation(reservation_id: int, user=Depends(verify_token_header)):
    return cancel_reservation_controller(reservation_id)


# ------------------------ RESERVATION - TABLE --------------------------

@router.post("/assign-reservation-to-table/{table_id}/{reservation_id}")
async def assign_reservation_to_table(table_id: str, reservation_id: int, user=Depends(verify_token_header)):
    return assign_reservation_to_table_controller(table_id, reservation_id)

@router.get("/tables-available-for-reservation/{reservation_id}")
async def get_available_tables_for_reservation(reservation_id: int, user=Depends(verify_token_header)):
    return get_available_tables_for_reservation_controller(reservation_id)


# ------------------------ ORDER ITEMS / REPORTS --------------------------

@router.put("/orders/serve-item/{order_id}/{item_id}")
async def serve_item(order_id: str, item_id: str, user=Depends(verify_token_header)):
    return serve_order_item_controller(order_id, item_id)

@router.get("/reports/wait-time/products")
async def wait_time_by_product(user=Depends(verify_token_header)):
    return get_wait_time_by_product_controller()

@router.get("/reports/wait-time-products-monthly/{month}/{year}")
async def wait_time_by_product_filtered(month: str, year: str, user=Depends(verify_token_header)):
    return get_wait_time_by_product_filtered_controller(month, year)

@router.get("/reports/wait-time/daily")
async def wait_time_by_day(user=Depends(verify_token_header)):
    return get_wait_time_by_day_controller()

@router.get("/reports/wait-time-monthly/{month}/{year}")
async def wait_time_by_day_filtered(month: str, year: str, user=Depends(verify_token_header)):
    return get_wait_time_by_day_filtered_controller(month, year)
