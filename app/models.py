import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Table, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class IngredientCategory(enum.Enum):
    VEGETABLE = "vegetable"
    MEAT = "meat"
    DAIRY = "dairy"
    
############################################
# Many-to-many relationship tables
pizza_doughs = Table(
    "pizza_doughs",
    Base.metadata,
    Column("pizza_id", Integer, ForeignKey("pizzas.id", ondelete="CASCADE"), primary_key=True),
    Column("dough_id", Integer, ForeignKey("doughs.id", ondelete="CASCADE"), primary_key=True),
)

class PizzaIngredient(Base):
    __tablename__ = "pizza_ingredients"
    pizza_id = Column(Integer, ForeignKey("pizzas.id"), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), primary_key=True)
    quantity = Column(Integer, nullable=False)
    
    pizza = relationship("Pizza", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="pizzas")

class OrderPizzaDough(Base):
    __tablename__ = "order_pizza_doughs"
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True)
    pizza_id = Column(Integer, ForeignKey("pizzas.id", ondelete="CASCADE"), primary_key=True)
    dough_id = Column(Integer, ForeignKey("doughs.id", ondelete="CASCADE"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=1)  # Liczba zamówionych pizz

    order = relationship("Order", back_populates="order_pizza_doughs")
    pizza = relationship("Pizza")
    dough = relationship("PizzaDough")
############################################
    
############################################
# Models
class Pizza(Base):
    __tablename__ = "pizzas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    in_menu = Column(Boolean, default=True)
    available_pizza_doughs = relationship("Dough", secondary="pizza_doughs", back_populates="pizzas")
    ingredients = relationship("Ingredient", back_populates="pizzas")

class Dough(Base):
    __tablename__ = "doughs"
    id = Column(Integer, primary_key=True, index=True)
    big_size = Column(Boolean, default=False)
    on_thick_pastry = Column(Boolean, default=False)
    without_gluten = Column(Boolean, default=False)
    price = Column(Float, nullable=False)
    pizzas = relationship("Pizza", secondary="pizza_doughs", back_populates="available_pizza_doughs")
    
class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    category = Column(Enum(IngredientCategory), nullable=False)
    in_stock = Column(Boolean, default=True)
    pizzas = relationship("Pizza", back_populates="ingredients")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_start_time = Column(DateTime, default=datetime.utcnow)
    total_price = Column(Float, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"))
    client = relationship("Client", back_populates="orders")
    order_pizza_doughs = relationship("OrderPizzaDough", back_populates="order")

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=False)
    orders = relationship("Order", back_populates="client")
