from typing import Any
from pydantic import BaseModel, Field

# Modelo para registrar un nuevo producto
class Product(BaseModel):
    id: int = Field(default=None)  # Make id optional
    name: str
    price: str  # Ensure product_price is non-negative
    description: str
    category: str
    calories: str | float | int
    cost: Any
    imageUrl: str
    stock: str