from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Table, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base, engine
import enum


pizza_ingredients = Table(
    "pizza_ingredients",
    Base.metadata,
    Column("pizza_id", Integer, ForeignKey("pizzas.id", ondelete="CASCADE"), primary_key=True),
    Column("ingredient_id", Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True)
)

class AdditionalIngredient(Base):
    __tablename__ = "additional_ingredients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_pizza_id = Column(Integer, ForeignKey("order_pizzas.id", ondelete="CASCADE"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="CASCADE"))
    quantity = Column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint('order_pizza_id', 'ingredient_id', name='_order_pizza_ingredient_uc'),)

    # Relacje
    order_pizza = relationship("OrderPizzas", back_populates="additional_ingredients_pivot")
    ingredient = relationship("Ingredient", back_populates="additional_ingredients_pivot")
    

class OrderPizzas(Base):
    __tablename__ = "order_pizzas"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    pizza_id = Column(Integer, ForeignKey("pizzas.id", ondelete="CASCADE"), nullable=True)
    dough_id = Column(Integer, ForeignKey("doughs.id", ondelete="CASCADE"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    is_partial = Column(Boolean, nullable=False, default=True)
    additional_ingredients_pivot = relationship("AdditionalIngredient", back_populates="order_pizza")

class Pizza(Base):
    __tablename__ = "pizzas"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False)
    in_menu = Column(Boolean, default=True)
    ingredients = relationship("Ingredient", secondary=pizza_ingredients, back_populates="pizzas")
    orders = relationship("Order", secondary='order_pizzas', back_populates="pizzas")

class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    pizzas = relationship("Pizza", secondary=pizza_ingredients, back_populates="ingredients")
    additional_ingredients_pivot = relationship("AdditionalIngredient", back_populates="ingredient")


class Dough(Base):
    __tablename__ = "doughs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    big_size = Column(Boolean, nullable=True)
    on_thick_pastry = Column(Boolean, nullable=True)
    price = Column(Float, nullable=False)

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phone = Column(String, nullable=False, unique=True)
    street_id = Column(Integer, ForeignKey("streets.id"), nullable=True)
    street = relationship("Street", back_populates="clients", lazy="joined")
    apartment = Column(String, nullable=True)
    orders = relationship("Order", back_populates="client")

    
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_start_time = Column(DateTime, default=datetime.utcnow)
    total_price = Column(Float, nullable=False, default=0)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    client = relationship("Client", back_populates="orders")
    pizzas = relationship("Pizza", secondary='order_pizzas' ,back_populates="orders")

class Street(Base):
    __tablename__ = "streets"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    clients = relationship("Client", back_populates="street")
    
    
#     # addresses = relationship("Address", back_populates="street")
#
# class Address(Base):
#     __tablename__ = "addresses"
#     # id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#     # street_id = Column(Integer, ForeignKey("streets.id"), nullable=False)
#     street = relationship("Street", back_populates="addresses")
#     building_number = Column(String, nullable=False)
#     apartment_number = Column(String, nullable=True)
#     # client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
#     # client = relationship("Client", back_populates="addresses")
#
# Base.metadata.create_all(bind=engine)