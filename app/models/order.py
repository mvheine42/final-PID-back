from typing import Any, List, Optional
from app.models.order_item import OrderItem
from pydantic import BaseModel, Field

class Order(BaseModel):
    status: str
    amountOfPeople: int
    tableNumber: int
    date: str
    time: str
    total: str
    orderItems: List[OrderItem]
    employee: str
    employee_name: Optional[str] = None