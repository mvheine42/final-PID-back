from pydantic import BaseModel, Field

class Category(BaseModel):
    name: str
    type: str