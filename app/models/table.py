from typing import Any
from pydantic import BaseModel, Field

# Modelo para registrar un nuevo producto
class Table(BaseModel):
    status: str
    capacity: int
    order_id: int
    current_reservation_id: int = 0