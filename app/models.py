from django.db.models import ManyToOneRel, ManyToManyRel
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Table, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum

class IngredientCategory(enum.Enum):
    VEGETABLE = "vegetable"
    MEAT = "meat"
    DAIRY = "dairy"

# pizza_ingredients = Table(
#     "pizza_ingredients",
#     Base.metadata,
#     Column("pizza_id", Integer, ForeignKey("pizzas.id", ondelete="CASCADE"), primary_key=True),
#     Column("ingredient_id", Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True)
# )
#
# pizza_doughs = Table(
#     "pizza_doughs",
#     Base.metadata,
#     Column("pizza_id", Integer, ForeignKey("pizzas.id", ondelete="CASCADE"), primary_key=True),
#     Column("dough_id", Integer, ForeignKey("doughs.id", ondelete="CASCADE"), primary_key=True)
# )
#
# order_pizzas = Table(
#     "order_pizzas",
#     Base.metadata,
#     Column("order_id", Integer, ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True),
#     Column("pizza_id", Integer, ForeignKey("pizzas.id", ondelete="CASCADE"), primary_key=True)
# )

class Pizza(Base):
    __tablename__ = "pizzas"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False)
    in_menu = Column(Boolean, default=True)
    # ingredients = relationship("Ingredient", secondary=pizza_ingredients, back_populates="pizzas")
    # available_pizza_doughs = relationship("Dough", secondary=pizza_doughs, back_populates="pizzas")

class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(Enum(IngredientCategory), nullable=False)
    price = Column(Float, nullable=False)
    # pizzas = relationship("Pizza", secondary=pizza_ingredients, back_populates="ingredients")

class Dough(Base):
    __tablename__ = "doughs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    big_size = Column(Boolean, default=False)
    on_thick_pastry = Column(Boolean, default=False)
    without_gluten = Column(Boolean, default=False)
    price = Column(Float, nullable=False)
    # pizzas = relationship("Pizza", secondary=pizza_doughs, back_populates="available_pizza_doughs")



class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phone = Column(String, nullable=False)
    # address_id = Column(Integer, ForeignKey("addresses.id"), nullable=True)
    # address = relationship("Address", back_populates="client")
    # orders = relationship("Order", back_populates="client")
    
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_start_time = Column(DateTime, default=datetime.utcnow)
    total_price = Column(Float, nullable=False)
    # client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    # client = relationship("Client", back_populates="orders")
    # pizzas = relationship("Pizza", secondary=order_pizzas ,back_populates="orders")


class Street(Base):
    __tablename__ = "streets"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    # addresses = relationship("Address", back_populates="street")
    
class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # street_id = Column(Integer, ForeignKey("streets.id"), nullable=False)
    # street = relationship("Street", back_populates="addresses")
    building_number = Column(String, nullable=False)
    apartment_number = Column(String, nullable=True)
    # client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    # client = relationship("Client", back_populates="addresses")