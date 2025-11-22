from typing import Any, Optional
from pydantic import BaseModel, Field
from app.models.product import Product
import uuid
from datetime import datetime

# Modelo para registrar un nuevo producto
class OrderItem(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    served_at: Optional[str] = None
    product_id: str
    product_name: str
    product_price: str
    amount: int
