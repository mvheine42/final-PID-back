from typing import Any
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str
    price: str 
    description: str
    category: str
    calories: str | float | int
    cost: Any
    imageUrl: str
    stock: str