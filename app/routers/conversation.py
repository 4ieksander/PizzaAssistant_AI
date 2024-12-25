# path/filename: routers/conversation.py
"""
Moduł z przykładową warstwą konwersacyjną do zamówień pizz.
Zarządza stanem konwersacji w pamięci i prosi użytkownika o brakujące parametry.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict
import uuid

from ..database import get_db
from sqlalchemy.orm import Session

from .analyze_order import (
    AdvancedPizzaParser,
    AnalyzeOrderRequest
)
from ..models import Order, order_pizzas

router = APIRouter()

# Tymczasowy "magazyn" stanów konwersacji
CONVERSATION_STATES: Dict[str, dict] = {}
# Struktura np.:
# CONVERSATION_STATES = {
#   "conversation_id_123": {
#       "order_id": 12,
#       "pending_items": [...],
#       "completed_items": [...],
#       "status": "awaiting_missing_info" / "done" / ...
#   },
#   ...
# }

class StartConversationRequest(BaseModel):
    order_id: int
    initial_text: str  # Tekst, którym user rozpoczyna zamówienie

class ContinueConversationRequest(BaseModel):
    conversation_id: str
    user_text: str

@router.post("/conversation/start")
def start_conversation(data: StartConversationRequest, db: Session = Depends(get_db)):
    """
    Inicjuje konwersację.
    1) Generuje unikalne conversation_id.
    2) Analizuje wstępny tekst (np. "poproszę dużą hawajską"),
       sprawdza braki. Jeśli są – wypisuje pytanie.
    3) Zachowuje stan w CONVERSATION_STATES.
    """
    # Tworzymy conversation_id
    conversation_id = str(uuid.uuid4())

    # Sprawdzamy, czy zamówienie istnieje
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        return {"success": False, "message": f"Zamówienie {data.order_id} nie istnieje."}

    # Analiza wstępna
    analyzer = AdvancedPizzaParser(db)
    parsed_items = analyzer.parse_order(data.initial_text)

    if not parsed_items:
        # Nie wykryto nic, ale konwersację mimo to możemy stworzyć
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

    # Podział na itemy kompletne (bez braków) i niekompletne
    complete = []
    incomplete = []
    for item in parsed_items:
        if item["missing_info"]:
            incomplete.append(item)
        else:
            complete.append(item)

    # Wstawiamy do stanu
    CONVERSATION_STATES[conversation_id] = {
        "order_id": data.order_id,
        "pending_items": incomplete,
        "completed_items": complete,
        "status": "awaiting_missing_info" if incomplete else "all_info_provided"
    }

    # Komunikat
    if incomplete:
        # Budujemy listę pytań: np. "Brak size, thickness"
        # Ale w wersji demo wystarczy jeden ogólny prompt
        missing_params = set()
        for inc in incomplete:
            for m in inc["missing_info"]:
                missing_params.add(m)
        msg = f"Wykryto brakujące informacje: {list(missing_params)}. Proszę uzupełnij."
    else:
        msg = "Wszystkie informacje uzupełnione."

    return {
        "conversation_id": conversation_id,
        "message": msg,
        "parsed_items": parsed_items
    }


@router.post("/conversation/continue")
def continue_conversation(data: ContinueConversationRequest, db: Session = Depends(get_db)):
    """
    Kontynuujemy konwersację, np. uzupełniając brakujące informacje
    (rozmiar, grubość) lub “domawiając” kolejne pozycje.
    1) Jeśli status to 'awaiting_missing_info', spróbujmy wstawić brakujące parametry do pending_items.
    2) Możemy też wykryć nowe items (domawianie).
    """
    conv_state = CONVERSATION_STATES.get(data.conversation_id)
    if not conv_state:
        return {"success": False, "message": "Nie znaleziono konwersacji o tym ID."}

    order_id = conv_state["order_id"]
    status = conv_state["status"]
    pending = conv_state["pending_items"]
    completed = conv_state["completed_items"]

    # Analizujemy user_text
    analyzer = AdvancedPizzaParser(db)
    new_parsed_items = analyzer.parse_order(data.user_text)

    if status == "awaiting_missing_info":
        # Spróbujmy “wzbogacić” dotychczasowe pending_items o brakujące parametry
        # Sposobów jest wiele. Na potrzeby dema załóżmy:
        # - bierzemy new_parsed_items[0], atrybuty "dough.big_size", "dough.on_thick_pastry",
        #   i wsadzamy do FIRST pending_item => wypełnia missing_info jeśli pasuje.
        # - lub jeśli user mówi “jeszcze jedną pepperoni” => tworzymy nowy item,
        #   doinstanciowujemy i wrzucamy do completed/pending w zależności, czy braki.

        if new_parsed_items:
            # Najprostsza heurystyka:
            # pobieramy parametry dough z new_parsed_items[0] i przenosimy do pending[0]
            # o ile tam jest brak
            for idx, p_item in enumerate(pending):
                # p_item["missing_info"] np. ["size", "thickness"]
                # weźmy dough z new_parsed_items[0] =>
                #  => "big_size" (jeśli != None, to wypełnij)
                #  => "on_thick_pastry" (j.w.)
                #  => "without_gluten"

                if not new_parsed_items:
                    break
                fill_source = new_parsed_items[0]

                # Uzupełniamy np. "size" (big_size)
                if "size" in p_item["missing_info"]:
                    if fill_source["dough"]["big_size"] is not None:
                        p_item["dough"]["big_size"] = fill_source["dough"]["big_size"]
                        p_item["missing_info"].remove("size")

                # Uzupełniamy "thickness" (on_thick_pastry)
                if "thickness" in p_item["missing_info"]:
                    if fill_source["dough"]["on_thick_pastry"] is not None:
                        p_item["dough"]["on_thick_pastry"] = fill_source["dough"]["on_thick_pastry"]
                        p_item["missing_info"].remove("thickness")

                # If user also gave new info about “podwójny ser” -> extras
                p_item["extras"].extend(fill_source["extras"])

                # If user gave new info about sauce
                p_item["sauces"].extend(fill_source["sauces"])

                # Jesli nic juz nie brakuje w tym p_item => przenosimy do completed
                if not p_item["missing_info"]:
                    completed.append(p_item)
                    pending.pop(idx)
                    break  # Przerywamy pętlę, bo usunęliśmy element z pending

            # A co, jeśli w new_parsed_items były jeszcze inne itemy?
            # - Może user powiedział: “duża, gruba, a dodatkowo jeszcze mała pepperoni”.
            #   Zatem new_parsed_items może zawierać drugą pozycję do domówienia.
            if len(new_parsed_items) > 1:
                extra_items = new_parsed_items[1:]
                for ex in extra_items:
                    if ex["missing_info"]:
                        pending.append(ex)
                    else:
                        completed.append(ex)

        # Sprawdzamy, czy pending jest puste
        if not pending:
            conv_state["status"] = "all_info_provided"
            msg = "Wszystkie parametry zostały uzupełnione."
        else:
            conv_state["status"] = "awaiting_missing_info"
            # Budujemy listę braków
            missing_params = set()
            for inc in pending:
                for m in inc["missing_info"]:
                    missing_params.add(m)
            msg = f"Wciąż brakuje: {list(missing_params)}"

    elif status == "all_info_provided":
        # Być może user “domawia” nową pizzę?
        if not new_parsed_items:
            msg = "Nic nie dodano."
        else:
            # Sprawdzamy, czy te itemy mają braki
            for it in new_parsed_items:
                if it["missing_info"]:
                    pending.append(it)
                else:
                    completed.append(it)
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

    analyzer = AdvancedPizzaParser(db)

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
        if item["dough"]["without_gluten"]:
            query = query.filter(Dough.without_gluten.is_(True))
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
                f"{item['pizza_count']}x {pizza_obj.name} (ciasto: size={item['dough']['big_size']}, thick={item['dough']['on_thick_pastry']}, gluten={item['dough']['without_gluten']})"
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
