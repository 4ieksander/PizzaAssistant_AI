# path/filename: routers/manage_conversation.py
"""
Obsługa konwersacji i stanu zamówienia.
Zarządza sekwencją dialogu, używa parsera (PizzaParser) do interpretacji wypowiedzi.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List
import uuid

from ..database import get_db
from sqlalchemy.orm import Session

from .analyze_order import PizzaParser, AnalyzeOrderRequest
from ..models import Order, order_pizzas

router = APIRouter()

CONVERSATION_STATES: Dict[str, dict] = {}


class StartConversationRequest(BaseModel):
    order_id: int
    initial_text: str


class ContinueConversationRequest(BaseModel):
    conversation_id: str
    user_text: str


def _split_completed_incomplete(parsed_items: List[dict]) -> (List[dict], List[dict]):
    """
    Dzieli listę itemów na kompletne (bez braków) i niekompletne (wymagają więcej danych).
    """
    complete = []
    incomplete = []
    for item in parsed_items:
        if item["missing_info"]:
            incomplete.append(item)
        else:
            complete.append(item)
    return complete, incomplete


def _merge_item_data(pending_item: dict, fill_source: dict):
    """
    Uzupełnia brakujące parametry w pending_item danymi z fill_source (jeśli zostały tam wykryte).
    Przykład: brakujące 'size' => pobieramy fill_source["dough"]["big_size"], jeśli nie jest None.
    """
    # Rozmiar
    if "size" in pending_item["missing_info"]:
        if fill_source["dough"]["big_size"] is not None:
            pending_item["dough"]["big_size"] = fill_source["dough"]["big_size"]
            pending_item["missing_info"].remove("size")

    # Grubość
    if "thickness" in pending_item["missing_info"]:
        if fill_source["dough"]["on_thick_pastry"] is not None:
            pending_item["dough"]["on_thick_pastry"] = fill_source["dough"]["on_thick_pastry"]
            pending_item["missing_info"].remove("thickness")

    # Extras i sauces
    pending_item["extras"].extend(fill_source["extras"])


def _add_extra_items(new_items: List[dict], pending: List[dict], completed: List[dict]):
    """
    Jeśli w nowo zinterpretowanym tekście są pozycje (np. user dodał kolejną pizzę),
    dodajemy je do pending lub completed w zależności od braków.
    """
    for ex in new_items:
        if ex["missing_info"]:
            pending.append(ex)
        else:
            completed.append(ex)


@router.post("/start")
def start_conversation(data: StartConversationRequest, db: Session = Depends(get_db)):
    conversation_id = str(uuid.uuid4())
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        return {"success": False, "message": f"Zamówienie {data.order_id} nie istnieje."}

    analyzer = PizzaParser(db)
    parsed_items = analyzer.parse_order(data.initial_text)

    # Jeśli parser nie zrozumiał niczego
    if not parsed_items:
        CONVERSATION_STATES[conversation_id] = {
            "order_id": data.order_id,
            "pending_items": [],
            "completed_items": [],
            "status": "waiting_for_order_details"
        }
        return {
            "conversation_id": conversation_id,
            "message": "Nie zrozumiałem zamówienia. Podaj proszę, co chcesz zamówić."
        }

    # Oddzielamy kompletne i niekompletne
    complete, incomplete = _split_completed_incomplete(parsed_items)

    # Ustawiamy stan
    status = "awaiting_missing_info" if incomplete else "all_info_provided"
    CONVERSATION_STATES[conversation_id] = {
        "order_id": data.order_id,
        "pending_items": incomplete,
        "completed_items": complete,
        "status": status
    }

    # Komunikat
    if incomplete:
        missing_params = set()
        for inc in incomplete:
            missing_params.update(inc["missing_info"])
        msg = f"Wykryto brakujące informacje: {list(missing_params)}. Proszę uzupełnij."
    else:
        msg = "Wszystkie informacje uzupełnione."

    return {
        "conversation_id": conversation_id,
        "message": msg,
        "parsed_items": parsed_items
    }


@router.post("/continue")
def continue_conversation(data: ContinueConversationRequest, db: Session = Depends(get_db)):
    conv_state = CONVERSATION_STATES.get(data.conversation_id)
    if not conv_state:
        return {"success": False, "message": "Nie znaleziono konwersacji o tym ID."}

    order_id = conv_state["order_id"]
    status = conv_state["status"]
    pending = conv_state["pending_items"]
    completed = conv_state["completed_items"]

    analyzer = PizzaParser(db)
    new_parsed_items = analyzer.parse_order(data.user_text)

    if status == "awaiting_missing_info":
        # Spróbujmy uzupełnić braki w pending (heurystyka: bierzemy dane z new_parsed_items[0])
        if new_parsed_items:
            fill_source_items = new_parsed_items[:]  # kopia
            for idx, p_item in enumerate(pending):
                if not fill_source_items:
                    break
                # Pierwszy element z fill_source_items
                fill_source = fill_source_items[0]
                _merge_item_data(p_item, fill_source)

                # Jeśli wypełniliśmy wszystkie braki, przenieś do completed
                if not p_item["missing_info"]:
                    completed.append(p_item)
                    pending.pop(idx)
                    fill_source_items.pop(0)  # zużyliśmy fill_source
                    break

            # Sprawdź, czy były kolejne itemy
            if len(fill_source_items) > 0:
                _add_extra_items(fill_source_items, pending, completed)

        # Oceniamy status
        if not pending:
            conv_state["status"] = "all_info_provided"
            msg = "Wszystkie parametry zostały uzupełnione."
        else:
            conv_state["status"] = "awaiting_missing_info"
            missing_params = set()
            for inc in pending:
                missing_params.update(inc["missing_info"])
            msg = f"Wciąż brakuje: {list(missing_params)}"

    elif status == "all_info_provided":
        # Być może user domawia nową pizzę
        if not new_parsed_items:
            msg = "Nic nie dodano."
        else:
            # Sprawdzamy braki i dodajemy
            _add_extra_items(new_parsed_items, pending, completed)
            if pending:
                conv_state["status"] = "awaiting_missing_info"
                msg = "Dodano nową pozycję, ale brakuje informacji. Podaj proszę szczegóły."
            else:
                msg = "Dodano nową pozycję. Wszystkie informacje kompletne."

    # Aktualizujemy stan
    CONVERSATION_STATES[data.conversation_id] = conv_state

    return {
        "conversation_id": data.conversation_id,
        "status": conv_state["status"],
        "pending_items": conv_state["pending_items"],
        "completed_items": conv_state["completed_items"],
        "message": msg
    }



@router.post("/conversation/finish")
def finish_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """
    Zamyka konwersację, przenosząc 'completed_items' do bazy (order_pizzas).
    (opcjonalnie można to robić w trakcie,
     ale tu pokazujemy jako osobny krok "zatwierdzenia").
    """
    conv_state = CONVERSATION_STATES.get(conversation_id)
    if not conv_state:
        return {"success": False, "message": "Nie znaleziono konwersacji o tym ID."}

    if conv_state["status"] == "awaiting_missing_info":
        return {
            "success": False,
            "message": "Nie można zakończyć – są jeszcze brakujące informacje."
        }

    order_id = conv_state["order_id"]
    completed_items = conv_state["completed_items"]

    # Zapisujemy do bazy
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"success": False, "message": f"Zamówienie {order_id} nie istnieje."}

    analyzer = PizzaParser(db)

    added_info = []
    for item in completed_items:
        # Znajdź Pizza
        pizza_obj = None
        if item["pizza"]:
            pizza_obj = next(
                (p for p in analyzer.all_pizzas if p.name.lower() == item["pizza"]),
                None
            )

        # Znajdź ciasto
        query = db.query(Dough)
        if item["dough"]["big_size"] is not None:
            query = query.filter(Dough.big_size == item["dough"]["big_size"])
        if item["dough"]["on_thick_pastry"] is not None:
            query = query.filter(Dough.on_thick_pastry == item["dough"]["on_thick_pastry"])
        dough_obj = query.first()

        if pizza_obj and dough_obj:
            db.execute(
                order_pizzas.insert().values(
                    order_id=order.id,
                    pizza_id=pizza_obj.id,
                    dough_id=dough_obj.id,
                    quantity=item["pizza_count"]
                )
            )
            db.commit()
            added_info.append(
                f"{item['pizza_count']}x {pizza_obj.name} (ciasto: size={item['dough']['big_size']}, thick={item['dough']['on_thick_pastry']})"
            )
        else:
            added_info.append(f"Nie dodano: {item}")

    # Oczyszczamy konwersację (opcjonalnie)
    del CONVERSATION_STATES[conversation_id]

    return {
        "success": True,
        "message": "Zamówienie zaktualizowane.",
        "added_items": added_info
    }
