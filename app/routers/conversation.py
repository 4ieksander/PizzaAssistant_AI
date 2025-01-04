# path/filename: routers/manage_conversation.py
"""
Obsługa konwersacji i stanu zamówienia.
Teraz: od razu zapisujemy itemy w bazie (order_pizzas), z is_partial=True,
a po uzupełnieniu braków aktualizujemy i ewentualnie zmieniamy is_partial=False.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid

from ..database import get_db
from sqlalchemy.orm import Session

from .analyze_order import PizzaParser
from ..models import Ingredient, Order, Dough, Pizza, OrderPizzas, AdditionalIngredient


router = APIRouter()

CONVERSATION_STATES: Dict[str, dict] = {}

class StartConversationRequest(BaseModel):
    order_id: int
    initial_text: str

class ContinueConversationRequest(BaseModel):
    conversation_id: str
    user_text: str

def _fill_db_item(session: Session, order_id: int, slot: dict) -> int:
    """
    Tworzy NOWY wiersz w order_pizzas wg slotu (jeśli parametry znane)
    i zwraca ID tego wiersza. is_partial = True, o ile braki > 0.
    """
    pizza_id = None
    if slot["pizza"]:
        pizza_obj = session.query(Pizza).filter(Pizza.name.ilike(slot["pizza"])).first()
        if pizza_obj:
            pizza_id = pizza_obj.id

    dough_id = None
    if slot["dough"]["big_size"] is not None and slot["dough"]["on_thick_pastry"] is not None:
        # w prostszej wersji – bo i tak może brakować gluten.
        # (albo jeśli parse dopuszcza "without_gluten", też można filtrować)
        query = session.query(Dough)
        query = query.filter(Dough.big_size == slot["dough"]["big_size"])
        query = query.filter(Dough.on_thick_pastry == slot["dough"]["on_thick_pastry"])
        dough_obj = query.first()
        if dough_obj:
            dough_id = dough_obj.id

    is_partial = (len(slot["missing_info"]) > 0)

    new_item = OrderPizzas(
        order_id=order_id,
        pizza_id=pizza_id if pizza_id is not None else None,
        dough_id=dough_id if dough_id is not None else None,
        quantity=slot.get("pizza_count", 1),
        is_partial=is_partial
    )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)  # żeby mieć new_item.id
    
    for (ing_name, ing_qty) in slot["extras"]:
        ing_obj = session.query(Ingredient).filter(Ingredient.name.ilike(ing_name)).first()
        if ing_obj:
            try:
                new_additional_ingredient = AdditionalIngredient(order_pizza_id=new_item.id,
                                                                                   ingredient_id=ing_obj.id,
                                                                                   quantity=ing_qty)
                session.add(new_additional_ingredient)
            except:
                pass
            slot["extras"] = []
    session.commit()

    return new_item.id

def _update_db_item(session: Session, db_id: int, slot: dict):
    """
    Aktualizuje ISTNIEJĄCY wiersz w order_pizzas,
    wypełniając brakujące parametry i ustawia is_partial = False jeśli slot kompletny.
    """
    db_item = session.query(OrderPizzas).filter(OrderPizzas.id == db_id).first()
    if not db_item:
        return

    # Ustawiamy pizza_id, jeśli slot["pizza"] rozpoznano
    if slot["pizza"]:
        pizza_obj = session.query(Pizza).filter(Pizza.name.ilike(slot["pizza"])).first()
        if pizza_obj:
            db_item.pizza_id = pizza_obj.id

    # Ustawiamy dough_id, jeśli slot ma wypełnione dough
    if slot["dough"]["big_size"] is not None and slot["dough"]["on_thick_pastry"] is not None:
        query = session.query(Dough)
        query = query.filter(Dough.big_size == slot["dough"]["big_size"])
        query = query.filter(Dough.on_thick_pastry == slot["dough"]["on_thick_pastry"])
        dough_obj = query.first()
        if dough_obj:
            db_item.dough_id = dough_obj.id

    # Ilość
    if "pizza_count" in slot:
        db_item.quantity = slot["pizza_count"]
    
    for (ing_name, ing_qty) in slot["extras"]:
        ing_obj = session.query(Ingredient).filter(Ingredient.name.ilike(ing_name)).first()
        if ing_obj:
            try:
                new_additional_ingredient = AdditionalIngredient(order_pizza_id=db_id,
                                                                                   ingredient_id=ing_obj.id,
                                                                                   quantity=ing_qty)
                session.add(new_additional_ingredient)
            except:
                pass
            slot["extras"] = []
    db_item.is_partial = bool(slot["missing_info"])

    session.commit()


@router.post("/start")
def start_conversation(data: StartConversationRequest, db: Session = Depends(get_db)):
    conversation_id = str(uuid.uuid4())
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        return {"success": False, "message": f"Zamówienie {data.order_id} nie istnieje."}

    parser = PizzaParser(db)
    parsed_items = parser.parse_order(data.initial_text)

    if not parsed_items:
        # Tworzymy pusty stan
        CONVERSATION_STATES[conversation_id] = {
            "order_id": data.order_id,
            "status": "waiting_for_order_details",
            "slots": []
        }
        return {
            "conversation_id": conversation_id,
            "message": "Nie zrozumiałem zamówienia. Podaj proszę, co chcesz zamówić."
        }

    # Zapiszmy każdy slot do DB
    for slot in parsed_items:
        db_id = _fill_db_item(db, data.order_id, slot)
        slot["db_id"] = db_id  # zapamiętujemy, który wiersz w bazie to jest

    # Sprawdźmy, czy któryś slot ma braki
    incomplete = any(len(s["missing_info"]) > 0 for s in parsed_items)
    status = "awaiting_missing_info" if incomplete else "all_info_provided"

    # Przechowujemy w pamięci minimalny stan (moglibyśmy nie przechowywać wcale,
    # ale tu np. mamy identyfikację slotów)
    CONVERSATION_STATES[conversation_id] = {
        "order_id": data.order_id,
        "status": status,
        "slots": parsed_items
    }

    msg = "Wszystkie informacje uzupełnione." if not incomplete else (
        "Brakuje parametrów. Proszę dopowiedz szczegóły."
    )
    return {
        "conversation_id": conversation_id,
        "message": msg,
        "parsed_items": parsed_items
    }


# ...
@router.post("/continue")
def continue_conversation(data: ContinueConversationRequest, db: Session = Depends(get_db)):
    conv_state = CONVERSATION_STATES.get(data.conversation_id)
    if not conv_state:
        return {"success": False, "message": "Nie znaleziono konwersacji o tym ID."}

    parser = PizzaParser(db)
    existing_slots = conv_state["slots"]
    updated_slots = parser.parse_order_in_context(data.user_text, existing_slots)

    old_len = len(existing_slots)
    new_len = len(updated_slots)
    if new_len > old_len:
        new_slots = updated_slots[old_len:]
        for s in new_slots:
            # nadaj db_id
            db_id = _fill_db_item(db, conv_state["order_id"], s)
            s["db_id"] = db_id
    else:
        for s in updated_slots:
            if "db_id" not in s:
                db_id = _fill_db_item(db, conv_state["order_id"], s)
                s["db_id"] = db_id

    conv_state["slots"] = updated_slots

    # Każdy slot, jeśli nie ma missing_info => zaktualizuj w bazie (is_partial=False)
    for slot in updated_slots:
        _update_db_item(db, slot["db_id"], slot)
    # Ustalamy status:
    incomplete = any(len(s["missing_info"]) > 0 for s in updated_slots)
    status = "awaiting_missing_info" if incomplete else "all_info_provided"
    

    conv_state["slots"] = updated_slots
    conv_state["status"] = status
    
    msg = "OK"
    if incomplete:
        msg += " – Wciąż brakuje pewnych informacji."
    else:
        msg += " – Wszystkie informacje kompletne."

    return {
        "conversation_id": data.conversation_id,
        "status": conv_state["status"],
        "parsed_items": updated_slots,
        "message": msg
    }
