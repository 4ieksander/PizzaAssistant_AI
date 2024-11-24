from pydantic import BaseModel, Field
from enum import Enum
from typing import List

# Kategoria składnika
class IngredientCategory(str, Enum):
    VEGETABLE = "vegetable"
    MEAT = "meat"
    DAIRY = "dairy"

# Serializer dla danych wejściowych
class IngredientCreate(BaseModel):
    name: str
    price: float = Field(..., gt=0)  # Cena musi być większa niż 0
    category: IngredientCategory
    in_stock: bool = True

# Serializer dla danych wyjściowych
class IngredientResponse(BaseModel):
    id: int
    name: str
    price: float
    category: str
    in_stock: bool

    class Config:
        orm_mode = True
