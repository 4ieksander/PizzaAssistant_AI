from fastapi import APIRouter, Depends
from app.database import get_db
from sqlalchemy.orm import Session
from app.models import Client, Order, OrderPizzas, Pizza, Dough, Ingredient, TranscriptionLog
from app.schemas import InitOrderRequest, OrderSchema, TranscriptionHistoryResponse, TranscriptionItem
from app.utils.logger import get_logger
from app.schemas import OrderItemSummary, OrderSummaryResponse

# path/filename: routers/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List



router = APIRouter()

log = get_logger(__name__)

router = APIRouter()

@router.get("/")
def get_orders(db: Session = Depends(get_db)):
    order_items = db.query(Order).all()
    return order_items


@router.post("/init", response_model=OrderSchema)
def call_and_initiate_order(request: InitOrderRequest, db: Session = Depends(get_db)):
		"""
		Call the order and initiate it for the given client.
		"""
		phone = request.phone
		log.info("Initiating order")
		client = db.query(Client).filter(Client.phone == phone).first()
		if not client:
				log.info(f"Creating new client with phone: {phone}")
				client = Client(phone=phone)
				db.add(client)
				db.commit()
				db.refresh(client)
		log.info(f"Creating new order for client: {client}")
		order = Order(client_id=client.id)
		db.add(order)
		db.commit()
		db.refresh(order)
		return OrderSchema.model_validate(order)



@router.get("/summary/{order_id}", response_model=OrderSummaryResponse)
def get_order_summary(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    total_cost = 0.0
    items_summary: List[OrderItemSummary] = []

    order_pizzas_rows = db.query(OrderPizzas).filter(OrderPizzas.order_id == order_id).all()

    for row in order_pizzas_rows:
        if not row.pizza_id or not row.dough_id:
            continue

        pizza_obj = db.query(Pizza).filter(Pizza.id == row.pizza_id).first()
        dough_obj = db.query(Dough).filter(Dough.id == row.dough_id).first()
        if not pizza_obj or not dough_obj:
            continue

        # Podstawa: bazowe składniki pizzy
        base_ing_price = sum(ing.price for ing in pizza_obj.ingredients)
        base_ing_names = [f"{ing.name} x1" for ing in pizza_obj.ingredients]

        # Dodatkowe składniki z pivot
        extras_price = 0.0
        extra_names = []
        for pivot in row.additional_ingredients_pivot:
            ing_qty = pivot.quantity
            ing = pivot.ingredient
            cost_for_this = ing.price * ing_qty
            extras_price += cost_for_this
            extra_names.append(f"{ing.name} x{ing_qty}")

        # Cena ciasta
        dough_price = dough_obj.price
        # Cena jednej sztuki
        price_each = base_ing_price + extras_price + dough_price
        # Koszt * quantity
        cost = price_each * row.quantity
        total_cost += cost

        # Opis ciasta
        dough_desc = []
        dough_desc.append("duża" if dough_obj.big_size else "mała")
        dough_desc.append("na grubym cieście" if dough_obj.on_thick_pastry else "na cienkim cieście")
        dough_label = " ".join(dough_desc)

        # Połącz nazwy
        all_ingredient_names = base_ing_names + extra_names

        items_summary.append(OrderItemSummary(
            pizza_name=pizza_obj.name,
            dough_desc=dough_label,
            price_each=price_each,
            quantity=row.quantity,
            cost=cost,
            ingredients=all_ingredient_names
        ))

    summary = OrderSummaryResponse(
        order_id=order_id,
        items=items_summary,
        total_cost=total_cost
    )
    return summary

@router.get("/transcript/{order_id}", response_model=TranscriptionHistoryResponse)
def get_transcription_history(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    transcriptions_history: List[TranscriptionItem]= []
    transcriptions = db.query(TranscriptionLog).filter(TranscriptionLog.order_id == order_id).all()
    for row in transcriptions:
        if not row.parsed:
            row.parsed = "N/A"
        if not row.updated_slots:
            row.updated_slots = "N/A"
        if not row.content:
            continue
        transcriptions_history.append(TranscriptionItem(
            id=row.id,
            content=row.content,
            parsed=row.parsed,
            updated_slots=row.updated_slots
        ))
    response = TranscriptionHistoryResponse(
        order_id=order_id,
        items=transcriptions_history
        )
    return response