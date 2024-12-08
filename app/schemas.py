# backend/app/schemas.py
from datetime import datetime
import dataclasses
from pydantic import BaseModel, ConfigDict
from typing import List

class IngredientSchema(BaseModel):
	id: int
	name: str
	category: str
	price: float
	
	class Config:
		from_attributes = True

class DoughSchema(BaseModel):
	id: int
	big_size: bool
	on_thick_pastry: bool
	without_gluten: bool
	price: float
	
	class Config:
		from_attributes = True


class PizzaSchema(BaseModel):
	id: int
	name: str
	in_menu: bool
	ingredients: List[IngredientSchema] = dataclasses.field(default_factory=list)
	available_pizza_doughs: List[DoughSchema] = dataclasses.field(default_factory=list)
	orders: List['OrderSchema'] = dataclasses.field(default_factory=list)

	class Config:
		from_attributes = True


class StreetSchema(BaseModel):
	id: int
	name: str
	
	class Config:
		from_attributes = True


class ClientSchema(BaseModel):
	id: int
	phone: str
	street: 'StreetSchema' = None
	orders: List[int] = dataclasses.field(default_factory=list)
	
	model_config = ConfigDict(from_attributes=True)

# class AddressSchema(BaseModel):
# 	id: int
# 	street: 'StreetSchema'
# 	building_number: str
# 	apartment_number: str
# 	client: 'ClientSchema'
#
# 	class Config:
# 		from_attributes = True

# Model danych wejściowych
class InitOrderRequest(BaseModel):
	phone: str

class Config:
	from_attributes = True


class OrderSchema(BaseModel):
    id: int
    order_start_time: datetime
    total_price: float = None
    client_id: int  # Tylko ID klienta
    pizzas: List[int] = dataclasses.field(default_factory=list)  # Tylko ID pizzy

    model_config = ConfigDict(from_attributes=True)
