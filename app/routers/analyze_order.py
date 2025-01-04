# path/filename: routers/analyze_order.py
"""
Rozbudowana wersja algorytmu, podzielona na mniejsze funkcje dla większej czytelności.
Wykrywa kilka osobnych pizz różniących się atrybutami ciasta, dopasowuje nazwy pizz
(fuzzy match), rozróżnia liczbę sztuk, wykrywa sosy, dodatki i braki danych.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
import spacy
from fuzzywuzzy import fuzz

from app.utils.logger import get_logger
from app.database import get_db
from app.models import Order, OrderPizzas, Pizza, Dough, Ingredient


log = get_logger(__name__)
router = APIRouter()
nlp = spacy.load("pl_core_news_md")

class AnalyzeOrderRequest(BaseModel):
    order_id: int
    transcription: str


POLISH_NUMBERS = {
    "jeden": 1, "jedna": 1, "dwa": 2, "dwie": 2, "trzy": 3,
    "cztery": 4, "pięć": 5, "sześć": 6, "siedem": 7, "osiem": 8,
    "dziewięć": 9, "dziesięć": 10
}
POLISH_MULTIPLIERS = {
    "podwójny": 2, "potrójny": 3, "poczwórny": 4
}
SIZE_SYNONYMS = {
    "duża": ["duży", "dużą", "wielka", "wielką", "family"],
    "mała": ["mały", "małą", "średnia"]
}
THICKNESS_SYNONYMS = {
    "gruba": ["gruby", "grube", "grubym"],
    "cienka": ["cienki", "cienkie", "cienkim"]
}
REFERENCE_WORDS_FOR_NEXT = {
    "jedna": 1,
    "druga": 2,
    "trzecia": 3,
    "czwarta": 4
}


def _map_synonym_with_dict(word: str, synonyms_dict: dict) -> str:
    """
    Funkcja pomocnicza do mapowania słowa na klucz, jeśli występuje w słowniku synonimów.
    """
    for key, synonyms in synonyms_dict.items():
        if word in synonyms:
            return key
    return word


def detect_number_if_any(token) -> int:
    """
    Zwraca int, jeśli to liczba lub polskie słowo-liczba, w przeciwnym razie 1.
    """
    val = 1
    log.debug("like num: %s", token.like_num)
    log.debug("tokken lema: %s", token.lemma_)
    log.debug("token text: %s", token.text)
    
    if token.like_num:
        try:
            val = int(token.text)
        except:
            pass
    elif token.lemma_ in POLISH_NUMBERS:
        val = POLISH_NUMBERS[token.lemma_]
    return val


def detect_multiplier_if_any(token) -> int:
    """
    Podwójny, potrójny, poczwórny => zwiększa wielokrotność.
    """
    if token.lemma_ in POLISH_MULTIPLIERS:
        return POLISH_MULTIPLIERS[token.lemma_]
    return 1


def fuzzy_match_pizza(candidate: str, pizza_names: List[str]) -> Optional[str]:
    """
    Używamy fuzzywuzzy, by ustalić najlepsze dopasowanie do nazwy pizzy.
    Zwraca nazwę pizzy lub None, jeśli score za niski.
    """
    best_score = 0
    best_name = None
    for p_name in pizza_names:
        score = fuzz.ratio(candidate, p_name)
        if score > best_score:
            best_score = score
            best_name = p_name
    if best_score >= 60:
        return best_name
    return None


def fuzzy_find_ingredient(txt: str, ingredients: List[str]) -> Tuple[str, int]:
    """
    Przeszukuje listę 'ingredients' w fuzzywuzzy, zwracając (najlepsza_nazwa, score).
    """
    best_score = 0
    best_ing = None
    for ing in ingredients:
        sc = fuzz.ratio(txt, ing)
        if sc > best_score:
            best_score = sc
            best_ing = ing
    return (best_ing, best_score)


def _detect_slots(tokens, slots: List[dict]) -> bool:
    """
    Wyszukuje w tokenach fragmenty 'dwa/trzy pizze' lub 'pizza'
    i dodaje odpowiednią liczbę slotów. Zwraca True, jeśli rozbiliśmy
    liczbę slotów, w przeciwnym razie False (dla logiki 'pierwsze spotkanie z pizza').
    """
    total_slots_created = False
    i = 0
    while i < len(tokens):
        t = tokens[i]
        lemma = t.lemma_

        # Sprawdź, czy to “dwie/dwa/trzy” i dalej “pizza/pizze”
        if lemma in POLISH_NUMBERS and (i + 1) < len(tokens):
            next_lemma = tokens[i + 1].lemma_
            if "pizza" in next_lemma:
                count_val = POLISH_NUMBERS[lemma]
                for _ in range(count_val):
                    slots.append(_create_slot())
                total_slots_created = True
                i += 2
                continue

        # Sprawdź, czy to “pizza” w liczbie pojedynczej (bez 'dwie/trzy')
        if lemma == "pizza" and not total_slots_created:
            slots.append(_create_slot())
            total_slots_created = True
            i += 1
            continue

        i += 1

    return total_slots_created


def _create_slot() -> dict:
    """
    Tworzy nowy slot opisujący pojedynczą sztukę pizzy.
    """
    return {
        "pizza": None,
        "pizza_count": 1,
        "dough": {
            "big_size": None,
            "on_thick_pastry": None,
        },
        "extras": [],
        "missing_info": []
    }


def _assign_attributes(tokens, slots: List[dict], all_pizzas: List[str],
                       common_attributes: dict):
    """
    Przypisuje do slotów atrybuty takie jak nazwa pizzy, rozmiar, grubość.
    Jeśli nie ma żadnego slotu, zapisuje w 'common_attributes', by potem scalić je do wszystkich.
    """
    i = 0
    while i < len(tokens):
        t = tokens[i]
        txt = t.text
        lemma = t.lemma_

        # Dopasowanie nazwy pizzy
        matched_pizza = fuzzy_match_pizza(txt, all_pizzas)
        if matched_pizza:
            if not slots:
                slots.append(_create_slot())

            slot = slots[-1]
            slot["pizza"] = matched_pizza
            if i > 0 and tokens[i - 1].lemma_ in POLISH_NUMBERS:
                slot["pizza_count"] = POLISH_NUMBERS[tokens[i - 1].lemma_]
            i += 1
            continue

        # Rozmiar
        mapped_size = _map_synonym_with_dict(lemma, SIZE_SYNONYMS)
        if mapped_size in ("duża", "mała"):
            if slots:
                slots[-1]["dough"]["big_size"] = (mapped_size == "duża")
            else:
                common_attributes["dough"]["big_size"] = (mapped_size == "duża")
            i += 1
            continue

        # Grubość
        mapped_thick = _map_synonym_with_dict(lemma, THICKNESS_SYNONYMS)
        if mapped_thick in ("gruba", "cienka"):
            on_thick = True if mapped_thick == "gruba" else False

            assigned = False
            if i > 0 and tokens[i - 1].lemma_ in REFERENCE_WORDS_FOR_NEXT:
                slot_idx = REFERENCE_WORDS_FOR_NEXT[tokens[i - 1].lemma_] - 1
                if slot_idx < len(slots):
                    slots[slot_idx]["dough"]["on_thick_pastry"] = on_thick
                    assigned = True

            if not assigned:
                if slots:
                    slots[-1]["dough"]["on_thick_pastry"] = on_thick
                else:
                    common_attributes["dough"]["on_thick_pastry"] = on_thick

            i += 1
            continue
        i += 1


def _assign_extras(tokens, slots: List[dict], all_ingredients: List[str],
                    common_attributes: dict):
    """
    Wyszukuje w tekście wzorce typu: 'z sosem', 'dodatkowy ser', itp.
    Wykorzystuje heurystyki liczby i mnożnika (np. 'trzema sosami', 'podwójny ser').
    """
    i = 0
    while i < len(tokens):
        t = tokens[i]
        txt = t.text.lower()

        if i > 0:
            prev_txt = tokens[i - 1].text.lower()
            if "z" in prev_txt or "dodatk" in prev_txt:
                    best_ing, ing_score = fuzzy_find_ingredient(txt, all_ingredients)
                    if ing_score > 70:
                            ing_qty = 1
                            if i - 2 >= 0:
                                    ing_qty *= detect_number_if_any(tokens[i - 2])
                                    ing_qty *= detect_multiplier_if_any(tokens[i - 2])

                            if slots:
                                slots[-1]["extras"].append((best_ing, ing_qty))
                            else:
                                common_attributes["extras"].append((best_ing, ing_qty))
        i += 1


class PizzaParser:
    def __init__(self, db: Session):
        self.db = db
        self.nlp = nlp
        self.all_pizzas = [p.name.lower() for p in db.query(Pizza).all()]
        self.all_ingredients = [ing.name.lower() for ing in db.query(Ingredient).all()]

    def parse_order(self, text: str) -> List[dict]:
        doc = self.nlp(text.lower())
        tokens = list(doc)

        common_attributes = {
            "dough": {
                "big_size": None,
                "on_thick_pastry": None,
            },
            "extras": []
        }
        slots: List[dict] = []

        _assign_attributes(tokens, slots, self.all_pizzas, common_attributes)
        _assign_extras(tokens, slots, self.all_ingredients, common_attributes)

        # 4) Scalamy atrybuty wspólne, jeśli nie zostały one nadpisane
        for s in slots:
            if common_attributes["dough"]["big_size"] is not None and s["dough"]["big_size"] is None:
                s["dough"]["big_size"] = common_attributes["dough"]["big_size"]
            if common_attributes["dough"]["on_thick_pastry"] is not None and s["dough"]["on_thick_pastry"] is None:
                s["dough"]["on_thick_pastry"] = common_attributes["dough"]["on_thick_pastry"]
            s["extras"].extend(common_attributes["extras"])

        # 5) Wyznaczamy braki
        for slot in slots:
            if slot["pizza"] is None:
                slot["missing_info"].append("pizza_name")
            if slot["dough"]["big_size"] is None:
                slot["missing_info"].append("size")
            if slot["dough"]["on_thick_pastry"] is None:
                slot["missing_info"].append("thickness")

        return slots
    
    def parse_order_in_context(self, text: str, existing_slots: List[dict]) -> List[dict]:
        """
        Wersja parsera, która:
        1) Próbuje normalnie wykryć nowe sloty,
        2) Jeśli brak nowych slotów, próbuje dopisać atrybuty do *ostatniego* (lub wskazanego) istniejącego slotu.
        """
        doc = self.nlp(text.lower())
        tokens = list(doc)
    
        new_slots: List[dict] = []
        _detect_slots(tokens, new_slots)
    
        slots_to_fill = new_slots if new_slots else existing_slots
    
        common_attributes = {
            "dough": {"big_size": None, "on_thick_pastry": None},
            "extras": []
        }
        _assign_attributes(tokens, slots_to_fill, self.all_pizzas, common_attributes)
        _assign_extras(tokens, slots_to_fill, self.all_ingredients, common_attributes)
    
        for s in slots_to_fill:
            if s["dough"]["big_size"] is None and common_attributes["dough"]["big_size"] is not None:
                s["dough"]["big_size"] = common_attributes["dough"]["big_size"]
            if s["dough"]["on_thick_pastry"] is None and common_attributes["dough"]["on_thick_pastry"] is not None:
                s["dough"]["on_thick_pastry"] = common_attributes["dough"]["on_thick_pastry"]
            s["extras"].extend(common_attributes["extras"])
    
        for slot in slots_to_fill:
            slot["missing_info"] = []
            if slot["pizza"] is None:
                slot["missing_info"].append("pizza_name")
            if slot["dough"]["big_size"] is None:
                slot["missing_info"].append("size")
            if slot["dough"]["on_thick_pastry"] is None:
                slot["missing_info"].append("thickness")

        if new_slots:
            return existing_slots + new_slots
        else:
            return existing_slots


@router.post("/analyze-order")
def analyze_order(data: AnalyzeOrderRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        return {"success": False, "message": f"Zamówienie {data.order_id} nie istnieje."}

    parser = PizzaParser(db)
    parsed_items = parser.parse_order(data.transcription)

    if not parsed_items:
        return {"success": False, "message": "Nie wykryto żadnych elementów zamówienia."}

    responses = []
    for slot in parsed_items:
        pizza_obj = None
        if slot["pizza"]:
            pizza_obj = db.query(Pizza).filter(Pizza.name.ilike(slot["pizza"])).first()

        # Budujemy zapytanie ciasta
        query = db.query(Dough)
        if slot["dough"]["big_size"] is not None:
            query = query.filter(Dough.big_size == slot["dough"]["big_size"])
        if slot["dough"]["on_thick_pastry"] is not None:
            query = query.filter(Dough.on_thick_pastry == slot["dough"]["on_thick_pastry"])
        dough_obj = query.first()

        if pizza_obj and dough_obj:
            new_item = OrderPizzas(
                order_id=order.id,
                pizza_id=pizza_obj.id,
                dough_id=dough_obj.id,
                quantity=slot["pizza_count"]
                    )
            db.add(new_item)
            db.commit()
            dough_desc = []
            if slot["dough"]["big_size"] is None:
                dough_desc.append("NIE PODANO ROZMIARU (domyślne)")
            else:
                dough_desc.append("duża" if slot["dough"]["big_size"] else "mała/średnia")

            if slot["dough"]["on_thick_pastry"] is None:
                dough_desc.append("NIE PODANO GRUBOŚCI (domyślne)")
            else:
                dough_desc.append("grube" if slot["dough"]["on_thick_pastry"] else "cienkie")

            missing = f"(Braki: {slot['missing_info']})" if slot["missing_info"] else ""
            resp = (
                f"{slot['pizza_count']}x {pizza_obj.name}, ciasto: {', '.join(dough_desc)} {missing} | "
                f"Extras: {slot['extras']}"
            )
            responses.append(resp)
        else:
            responses.append(f"Brak pizzy={pizza_obj} lub ciasta={dough_obj} => {slot}")

    return {
        "success": True,
        "parsed_items": parsed_items,
        "info": responses
    }
