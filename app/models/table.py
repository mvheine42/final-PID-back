from typing import Any
from pydantic import BaseModel, Field

class Table(BaseModel):
    status: str
    capacity: int
    order_id: int
    current_reservation_id: int = 0