"""
FastAPI app with endpoints for managing pizzas, ingredients, orders, and clients.
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Pizza, Ingredient, Order, Client
from .database_interactions import (
    add_pizza, get_pizza_by_id, update_pizza, delete_pizza,
    add_ingredient, get_all_ingredients, get_ingredients_by_category, update_ingredient, delete_ingredient,
    add_order, get_all_orders, get_order_by_id, update_order, delete_order,
    add_client, get_all_clients, get_client_with_orders, update_client, delete_client
)

# FastAPI instance
app = FastAPI()

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pizza endpoints
@app.post("/pizzas/")
def create_pizza(name: str, in_menu: bool, dough_ids: list[int], ingredient_ids: list[int], db: Session = Depends(get_db)):
    pizza = add_pizza(db, name=name, in_menu=in_menu, dough_ids=dough_ids, ingredient_ids=ingredient_ids)
    return {"message": "Pizza created successfully", "pizza": pizza}

@app.get("/pizzas/{pizza_id}")
def read_pizza(pizza_id: int, db: Session = Depends(get_db)):
    pizza = get_pizza_by_id(db, pizza_id)
    if not pizza:
        raise HTTPException(status_code=404, detail="Pizza not found")
    return {"pizza": pizza}

@app.put("/pizzas/{pizza_id}")
def update_pizza_endpoint(pizza_id: int, name: str = None, in_menu: bool = None, db: Session = Depends(get_db)):
    pizza = update_pizza(db, pizza_id, name=name, in_menu=in_menu)
    if not pizza:
        raise HTTPException(status_code=404, detail="Pizza not found")
    return {"message": "Pizza updated successfully", "pizza": pizza}

@app.delete("/pizzas/{pizza_id}")
def delete_pizza_endpoint(pizza_id: int, db: Session = Depends(get_db)):
    pizza = delete_pizza(db, pizza_id)
    if not pizza:
        raise HTTPException(status_code=404, detail="Pizza not found")
    return {"message": "Pizza deleted successfully", "pizza": pizza}


# Ingredient endpoints
@app.post("/ingredients/")
def create_ingredient(name: str, price: float, category: str, in_stock: bool = True, db: Session = Depends(get_db)):
    ingredient = add_ingredient(db, name=name, price=price, category=category, in_stock=in_stock)
    return {"message": "Ingredient created successfully", "ingredient_id": ingredient.id}

@app.get("/ingredients/")
def read_all_ingredients(db: Session = Depends(get_db)):
    ingredients = get_all_ingredients(db)
    return {"ingredients": [{"id": ing.id, "name": ing.name, "price": ing.price, "category": ing.category.value} for ing in ingredients]}

@app.get("/ingredients/category/{category}")
def read_ingredients_by_category(category: str, db: Session = Depends(get_db)):
    ingredients = get_ingredients_by_category(db, category)
    if not ingredients:
        raise HTTPException(status_code=404, detail="No ingredients found in this category")
    return {"ingredients": [{"id": ing.id, "name": ing.name, "price": ing.price, "category": ing.category.value} for ing in ingredients]}

@app.put("/ingredients/{ingredient_id}")
def update_ingredient_endpoint(ingredient_id: int, name: str = None, price: float = None, in_stock: bool = None, db: Session = Depends(get_db)):
    ingredient = update_ingredient(db, ingredient_id, name=name, price=price, in_stock=in_stock)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return {"message": "Ingredient updated successfully", "ingredient": {"id": ingredient.id, "name": ingredient.name, "price": ingredient.price}}

@app.delete("/ingredients/{ingredient_id}")
def delete_ingredient_endpoint(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = delete_ingredient(db, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return {"message": "Ingredient deleted successfully", "ingredient_id": ingredient.id}

# Complete integration of FastAPI app with all endpoints (pizzas and ingredients for now)

# Pizza endpoints (from earlier implementation)
@app.post("/pizzas/")
def create_pizza(name: str, in_menu: bool, dough_ids: list[int], ingredient_ids: list[int], db: Session = Depends(get_db)):
    pizza = add_pizza(db, name=name, in_menu=in_menu, dough_ids=dough_ids, ingredient_ids=ingredient_ids)
    return {"message": "Pizza created successfully", "pizza": pizza.id}

@app.get("/pizzas/{pizza_id}")
def read_pizza(pizza_id: int, db: Session = Depends(get_db)):
    pizza = get_pizza_by_id(db, pizza_id)
    if not pizza:
        raise HTTPException(status_code=404, detail="Pizza not found")
    return {"pizza": {"id": pizza.id, "name": pizza.name, "in_menu": pizza.in_menu}}

@app.put("/pizzas/{pizza_id}")
def update_pizza_endpoint(pizza_id: int, name: str = None, in_menu: bool = None, db: Session = Depends(get_db)):
    pizza = update_pizza(db, pizza_id, name=name, in_menu=in_menu)
    if not pizza:
        raise HTTPException(status_code=404, detail="Pizza not found")
    return {"message": "Pizza updated successfully", "pizza": {"id": pizza.id, "name": pizza.name}}

@app.delete("/pizzas/{pizza_id}")
def delete_pizza_endpoint(pizza_id: int, db: Session = Depends(get_db)):
    pizza = delete_pizza(db, pizza_id)
    if not pizza:
        raise HTTPException(status_code=404, detail="Pizza not found")
    return {"message": "Pizza deleted successfully", "pizza_id": pizza.id}

# Ingredient endpoints
@app.post("/ingredients/")
def create_ingredient(name: str, price: float, category: str, in_stock: bool = True, db: Session = Depends(get_db)):
    ingredient = add_ingredient(db, name=name, price=price, category=category, in_stock=in_stock)
    return {"message": "Ingredient created successfully", "ingredient_id": ingredient.id}

@app.get("/ingredients/")
def read_all_ingredients(db: Session = Depends(get_db)):
    ingredients = get_all_ingredients(db)
    return {"ingredients": [{"id": ing.id, "name": ing.name, "price": ing.price, "category": ing.category.value} for ing in ingredients]}

@app.get("/ingredients/category/{category}")
def read_ingredients_by_category(category: str, db: Session = Depends(get_db)):
    ingredients = get_ingredients_by_category(db, category)
    if not ingredients:
        raise HTTPException(status_code=404, detail="No ingredients found in this category")
    return {"ingredients": [{"id": ing.id, "name": ing.name, "price": ing.price, "category": ing.category.value} for ing in ingredients]}

@app.put("/ingredients/{ingredient_id}")
def update_ingredient_endpoint(ingredient_id: int, name: str = None, price: float = None, in_stock: bool = None, db: Session = Depends(get_db)):
    ingredient = update_ingredient(db, ingredient_id, name=name, price=price, in_stock=in_stock)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return {"message": "Ingredient updated successfully", "ingredient": {"id": ingredient.id, "name": ingredient.name, "price": ingredient.price}}

@app.delete("/ingredients/{ingredient_id}")
def delete_ingredient_endpoint(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = delete_ingredient(db, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return {"message": "Ingredient deleted successfully", "ingredient_id": ingredient.id}

# The current app includes endpoints for pizzas and ingredients.
# Next: Orders and clients endpoints. Let me know if you'd like to proceed.
# Adding endpoints for orders to FastAPI app

# Order endpoints
@app.post("/orders/")
def create_order(client_id: int, total_price: float, pizza_doughs: list[dict], db: Session = Depends(get_db)):
    """
    Create a new order with associated pizzas and doughs.
    pizza_doughs: List of dictionaries with pizza_id, dough_id, and quantity.
    """
    order = add_order(db, client_id=client_id, total_price=total_price, pizza_doughs=pizza_doughs)
    return {"message": "Order created successfully", "order_id": order.id}

@app.get("/orders/")
def read_all_orders(db: Session = Depends(get_db)):
    orders = get_all_orders(db)
    return {"orders": [{"id": order.id, "total_price": order.total_price, "status": order.status} for order in orders]}

@app.get("/orders/{order_id}")
def read_order(order_id: int, db: Session = Depends(get_db)):
    order = get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order": {
            "id": order.id,
            "total_price": order.total_price,
            "status": order.status,
            "client_id": order.client_id,
        }
    }

@app.put("/orders/{order_id}")
def update_order_endpoint(order_id: int, total_price: float = None, status: str = None, db: Session = Depends(get_db)):
    order = update_order(db, order_id, total_price=total_price, status=status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order updated successfully", "order": {"id": order.id, "total_price": order.total_price, "status": order.status}}

@app.delete("/orders/{order_id}")
def delete_order_endpoint(order_id: int, db: Session = Depends(get_db)):
    order = delete_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted successfully", "order_id": order.id}

# Adding endpoints for clients to FastAPI app

# Client endpoints
@app.post("/clients/")
def create_client(name: str, phone: str, address: str, db: Session = Depends(get_db)):
    """
    Create a new client.
    """
    client = add_client(db, name=name, phone=phone, address=address)
    return {"message": "Client created successfully", "client_id": client.id}

@app.get("/clients/")
def read_all_clients(db: Session = Depends(get_db)):
    clients = get_all_clients(db)
    return {"clients": [{"id": client.id, "name": client.name, "phone": client.phone, "address": client.address} for client in clients]}

@app.get("/clients/{client_id}")
def read_client_with_orders(client_id: int, db: Session = Depends(get_db)):
    client_data = get_client_with_orders(db, client_id)
    if not client_data:
        raise HTTPException(status_code=404, detail="Client not found")
    client, orders = client_data["client"], client_data["orders"]
    return {
        "client": {
            "id": client.id,
            "name": client.name,
            "phone": client.phone,
            "address": client.address,
            "orders": [{"id": order.id, "total_price": order.total_price, "status": order.status} for order in orders],
        }
    }

@app.put("/clients/{client_id}")
def update_client_endpoint(client_id: int, name: str = None, phone: str = None, address: str = None, db: Session = Depends(get_db)):
    client = update_client(db, client_id, name=name, phone=phone, address=address)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client updated successfully", "client": {"id": client.id, "name": client.name}}

@app.delete("/clients/{client_id}")
def delete_client_endpoint(client_id: int, db: Session = Depends(get_db)):
    client = delete_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully", "client_id": client.id}

