# /backend/database_interactions.py
from sqlalchemy.orm import Session
from .models import Pizza, Ingredient, Order, Client, Dough, IngredientCategory


# Pizza CRUD
def add_pizza(session: Session, name: str, in_menu: bool, dough_ids: list[int], ingredient_ids: list[int]):
	new_pizza = Pizza(name=name, in_menu=in_menu)
	session.add(new_pizza)
	session.flush()  # Assigns ID before associating relationships
	
	# Add relationships
	for dough_id in dough_ids:
		dough = session.get(Dough, dough_id)
		if dough:
			new_pizza.available_pizza_doughs.append(dough)
	
	for ingredient_id in ingredient_ids:
		ingredient = session.get(Ingredient, ingredient_id)
		if ingredient:
			new_pizza.ingredients.append(ingredient)
	
	session.commit()
	return new_pizza


def get_pizza_by_id(session: Session, pizza_id: int):
	return session.get(Pizza, pizza_id)


def update_pizza(session: Session, pizza_id: int, **kwargs):
	pizza = session.get(Pizza, pizza_id)
	if not pizza:
		return None
	for key, value in kwargs.items():
		if hasattr(pizza, key):
			setattr(pizza, key, value)
	session.commit()
	return pizza


def delete_pizza(session: Session, pizza_id: int):
	pizza = session.get(Pizza, pizza_id)
	if pizza:
		session.delete(pizza)
		session.commit()
	return pizza


# Ingredient CRUD
def add_ingredient(session: Session, name: str, price: float, category: str, in_stock: bool = True):
    new_ingredient = Ingredient(
        name=name,
        price=price,
        category=IngredientCategory(category),
        in_stock=in_stock,
    )
    session.add(new_ingredient)
    session.commit()
    return new_ingredient

def get_all_ingredients(session: Session):
    return session.query(Ingredient).all()

def get_ingredients_by_category(session: Session, category: str):
    return session.query(Ingredient).filter(Ingredient.category == IngredientCategory(category)).all()

def update_ingredient(session: Session, ingredient_id: int, **kwargs):
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        return None
    for key, value in kwargs.items():
        if hasattr(ingredient, key):
            setattr(ingredient, key, value)
    session.commit()
    return ingredient

def delete_ingredient(session: Session, ingredient_id: int):
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient:
        session.delete(ingredient)
        session.commit()
    return ingredient

# Order CRUD
def add_order(session: Session, client_id: int, total_price: float, pizza_doughs: list[dict]):
    new_order = Order(client_id=client_id, total_price=total_price)
    session.add(new_order)
    session.flush()  # Assigns ID before associating relationships

    for pd in pizza_doughs:
        order_pizza_dough = OrderPizzaDough(
            order_id=new_order.id,
            pizza_id=pd["pizza_id"],
            dough_id=pd["dough_id"],
            quantity=pd.get("quantity", 1),
        )
        session.add(order_pizza_dough)
    session.commit()
    return new_order

def get_all_orders(session: Session):
    return session.query(Order).all()

def get_order_by_id(session: Session, order_id: int):
    return session.get(Order, order_id)

def update_order(session: Session, order_id: int, **kwargs):
    order = session.get(Order, order_id)
    if not order:
        return None
    for key, value in kwargs.items():
        if hasattr(order, key):
            setattr(order, key, value)
    session.commit()
    return order

def delete_order(session: Session, order_id: int):
    order = session.get(Order, order_id)
    if order:
        session.delete(order)
        session.commit()
    return order

# Client CRUD
def add_client(session: Session, name: str, phone: str, address: str):
    new_client = Client(name=name, phone=phone, address=address)
    session.add(new_client)
    session.commit()
    return new_client

def get_all_clients(session: Session):
    return session.query(Client).all()

def get_client_with_orders(session: Session, client_id: int):
    client = session.get(Client, client_id)
    if client:
        return {"client": client, "orders": client.orders}
    return None

def update_client(session: Session, client_id: int, **kwargs):
    client = session.get(Client, client_id)
    if not client:
        return None
    for key, value in kwargs.items():
        if hasattr(client, key):
            setattr(client, key, value)
    session.commit()
    return client

def delete_client(session: Session, client_id: int):
    client = session.get(Client, client_id)
    if client:
        session.delete(client)
        session.commit()
    return client
