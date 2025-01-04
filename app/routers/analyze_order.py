# path/filename: routers/analyze_order.py
"""
Rozbudowana wersja algorytmu, podzielona na mniejsze funkcje dla większej czytelności.
Wykrywa kilka osobnych pizz różniących się atrybutami ciasta, dopasowuje nazwy pizz
(fuzzy match), rozróżnia liczbę sztuk, wykrywa sosy, dodatki i braki danych.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple

from sqlalchemy import false
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
    "czwarta": 4,
    "piąta": 5,
    "kolejna": 1,
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
    log.info("Tworzę nowy slot z id=%s")
    return {
        "pizza":        None,
        "pizza_count":  1,
        "dough":        {
            "big_size": None,
            "on_thick_pastry": None,
        },
        "extras":       [],
        "missing_info": []
    }


def _assign_attributes(tokens, slots: List[dict], all_pizzas: List[str],
                       common_attributes: dict):
    """
    Przypisuje do slotów atrybuty takie jak nazwa pizzy, rozmiar, grubość.
    Jeśli nie ma żadnego slotu, zapisuje w 'common_attributes', by potem scalić je do wszystkich.
    """
    last_count = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        txt = t.text.lower()
        lemma = t.lemma_.lower()
        
        #liczebnik
        if lemma in POLISH_NUMBERS or t.like_num:
            if t.like_num:
                try:
                    last_count = int(t.text)
                except:
                    last_count = None
            else:
                last_count = POLISH_NUMBERS.get(lemma, None)
            i += 1
            continue
        
        #rozmiar
        mapped_size = _map_synonym_with_dict(lemma, SIZE_SYNONYMS)
        if mapped_size in ("duża", "mała"):
            if slots:
                slots[-1]["dough"]["big_size"] = (mapped_size == "duża")
            else:
                common_attributes["dough"]["big_size"] = (mapped_size == "duża")
            i += 1
            continue
        
        #grubość
        mapped_thick = _map_synonym_with_dict(lemma, THICKNESS_SYNONYMS)
        if mapped_thick in ("gruba", "cienka"):
            on_thick = (mapped_thick == "gruba")
            if slots:
                slots[-1]["dough"]["on_thick_pastry"] = on_thick
            else:
                common_attributes["dough"]["on_thick_pastry"] = on_thick
            i += 1
            continue
        
        # nazwa pizzy
        matched_pizza = fuzzy_match_pizza(txt, all_pizzas)
        if matched_pizza:
            if not slots:
                slots.append(_create_slot())
            
            slot = slots[-1]
            slot["pizza"] = matched_pizza
            
            if last_count is not None:
                slot["pizza_count"] = last_count
                last_count = None
            i += 1
            continue
        i += 1


def _assign_extras_trigram(tokens, slots: List[dict], all_ingredients: List[str],
                           common_attributes: dict):
    """
    Szuka w tekście 3-gramów w stylu:
      - [z/dodatkową], [podwójną/potrójną?], [nazwę składnika]
    lub odwrotny wariant itd.
    Jeżeli znajdzie, to wstawia do slots[-1]["extras"] np.: (składnik, qty).
    """
    i = 0
    if i == len(tokens) - 2:
        if _about_additional_ing_words(tokens[i].lemma_):
            best_ing, sc = fuzzy_find_ingredient(tokens[i+1].text.lower(), all_ingredients)
            if sc > 70 and best_ing:
                qty = 1
                if slots:
                    slots[-1]["extras"].append((best_ing, qty))
                else:
                    common_attributes["extras"].append((best_ing, qty))
                    
    while i <= len(tokens) - 3:
        if _about_additional_ing_words(tokens[i].lemma_) and _about_additional_ing_words(tokens[i+1].lemma_) and i < len(tokens) - 4:
            i += 1  # aby wykrywanie rozbudowanych fraz było bardziej dokładne
        tri = tokens[i], tokens[i+1], tokens[i+2]
        tri_text = [tok.text.lower() for tok in tri]
        tri_lemma = [tok.lemma_.lower() for tok in tri]
        log.info("TRIGRAM: %s", tri_text)
    
        # CASE A: [z|dodatk*], [multipler], [ingredient]
        if _about_additional_ing_words(tri_lemma[0]):
            multiplier = detect_multiplier_if_any(tri[1])
            best_ing, sc = fuzzy_find_ingredient(tri_text[2], all_ingredients)
            if sc > 70 and best_ing:
                qty = multiplier
                if slots:
                    slots[-1]["extras"].append((best_ing, qty))
                else:
                    common_attributes["extras"].append((best_ing, qty))
                    
                log.info("Dodano składnik: %s x %s", best_ing, qty)
                if len(tokens) >= i + 4:
                    _check_for_another_ing_in_pharse(tokens[i + 3:], all_ingredients, slots, common_attributes)
                
                i += 3
                continue
 
        # CASE B: [z|dodatk*], [ingredient], [multipler/ "i" / "oraz"], OPT [second ingredient]
        if _about_additional_ing_words(tri_lemma[0]):
            best_ing, sc = fuzzy_find_ingredient(tri_text[1], all_ingredients)
            if sc > 70 and best_ing:
                if tri_lemma[2] in ("i", "oraz") and len(tokens) >= i + 3:
                    best_second_ing, sc2 = fuzzy_find_ingredient(tokens[i+3], all_ingredients)
                    if sc2 > 70 and best_second_ing:
                        slots[-1]["extras"].append((best_second_ing, 1))
                    qty = 1
                else:
                    multiplier = detect_multiplier_if_any(tri[2])
                    qty = multiplier if multiplier > 1 else 1
                if not qty:
                    qty = 1
                if slots:
                    slots[-1]["extras"].append((best_ing, qty))
                else:
                    common_attributes["extras"].append((best_ing, qty))
                if len(tokens) >= i + 3:
                    _check_for_another_ing_in_pharse(tokens[i + 3:], all_ingredients, slots, common_attributes)
                
                i += 3
                continue

        # CASE C: [multipler], [dodatk*|z], [ingredient]
        if detect_multiplier_if_any(tri[0]) > 1 and _about_additional_ing_words(tri_lemma[1]):
            best_ing, sc = fuzzy_find_ingredient(tri_text[2], all_ingredients)
            if sc > 70 and best_ing:
                qty = detect_multiplier_if_any(tri[0])
                if slots:
                    slots[-1]["extras"].append((best_ing, qty))
                else:
                    common_attributes["extras"].append((best_ing, qty))
                if len(tokens) >= i + 3:
                    _check_for_another_ing_in_pharse(tokens[i + 3:], all_ingredients, slots, common_attributes)
                
                i += 3
                continue
    
        i += 1

def _about_additional_ing_words(lemma):
    if "dodatk" in lemma.lower() or "z" in lemma.lower():
        return True
    return False

def _check_for_additional_ing(tokens, all_ingredients, slots, common_attributes):
    log.info(tokens)
    if tokens[0].lemma_ in ("i", "oraz") and len(tokens) > 1:
        best_ing, sc = fuzzy_find_ingredient(tokens[1].text.lower(), all_ingredients)
        if sc > 70 and best_ing:
            qty = detect_multiplier_if_any(tokens[0])
            if slots:
                slots[-1]["extras"].append((best_ing, qty))
            else:
                common_attributes["extras"].append((best_ing, qty))
    elif tokens[1].lemma_ in ("i", "oraz") and len(tokens) > 2:
        best_ing, sc = fuzzy_find_ingredient(tokens[2].text.lower(), all_ingredients)
        if sc > 70 and best_ing:
            if slots:
                slots[-1]["extras"].append((best_ing, 1))
            else:
                common_attributes["extras"].append((best_ing, 1))
    elif tokens[0].lemma_ in ("i", "oraz") and len(tokens) > 2:
        best_ing, sc = fuzzy_find_ingredient(tokens[2].text.lower(), all_ingredients)
        if sc > 70 and best_ing:
            qty = detect_multiplier_if_any(tokens[1])
            if slots:
                slots[-1]["extras"].append((best_ing, qty))
            else:
                common_attributes["extras"].append((best_ing, qty))

def _check_for_another_ing_in_pharse(tokens, all_ingredients, slots, common_attributes):
    best_ing, sc = fuzzy_find_ingredient(tokens[0].text.lower(), all_ingredients)
    if sc > 70 and best_ing:
        if slots:
            slots[-1]["extras"].append((best_ing, 1))
        else:
            common_attributes["extras"].append((best_ing, 1))
    else:
        best_ing, sc = fuzzy_find_ingredient(tokens[1].text.lower(), all_ingredients)
        if sc > 70 and best_ing:
            qty = detect_multiplier_if_any(tokens[0])
            if slots:
                slots[-1]["extras"].append((best_ing, qty))
            else:
                common_attributes["extras"].append((best_ing, qty))
                
            

class PizzaParser:
    def __init__(self, db: Session):
        self.db = db
        self.nlp = nlp
        self.all_pizzas = [p.name.lower() for p in db.query(Pizza).all()]
        self.all_ingredients = [ing.name.lower() for ing in db.query(Ingredient).all()]
        self.sauce_list = [
            ing.name.lower() for ing in db.query(Ingredient).filter(Ingredient.category == "sauce")
        ]

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
        _assign_extras_trigram(tokens, slots, self.all_ingredients, common_attributes)

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
                slot["missing_info"].append("Nazwa pizzy")
            if slot["dough"]["big_size"] is None:
                slot["missing_info"].append("Rozmiar")
            if slot["dough"]["on_thick_pastry"] is None:
                slot["missing_info"].append("Grubość ciasta")

        return slots
    def parse_order_in_context(self, text: str, existing_slots: List[dict]) -> List[dict]:
        """
        Wersja parsera, która:
        1) Próbuje normalnie wykryć nowe sloty,
        2) Jeśli brak nowych slotów, próbuje dopisać atrybuty do *ostatniego* (lub wskazanego) istniejącego slotu.
        """
        doc = self.nlp(text.lower())
        tokens = list(doc)
    
        # Najpierw standardowe:
        new_slots: List[dict] = []
        _detect_slots(tokens, new_slots)  # Być może brak 'pizza' => new_slots będzie puste
    
        # Tutaj przypisujemy atrybuty
        # Ale jeśli new_slots jest puste, to 'wymusimy' przypisanie do existing_slots
        slots_to_fill = new_slots if new_slots else existing_slots
    
        # Przypisujemy do slots_to_fill
        common_attributes = {
            "dough": {"big_size": None, "on_thick_pastry": None},
            "extras": []
        }
        _assign_attributes(tokens, slots_to_fill, self.all_pizzas, common_attributes)
        _assign_extras_trigram(tokens, slots_to_fill, self.all_ingredients, common_attributes)
    
        # Scalamy common
        for s in slots_to_fill:
            if s["dough"]["big_size"] is None and common_attributes["dough"]["big_size"] is not None:
                s["dough"]["big_size"] = common_attributes["dough"]["big_size"]
            if s["dough"]["on_thick_pastry"] is None and common_attributes["dough"]["on_thick_pastry"] is not None:
                s["dough"]["on_thick_pastry"] = common_attributes["dough"]["on_thick_pastry"]
            s["extras"].extend(common_attributes["extras"])
    
        # Wyznaczamy braki w slots_to_fill
        for slot in slots_to_fill:
            slot["missing_info"] = []
            if slot["pizza"] is None:
                slot["missing_info"].append("pizza_name")
            if slot["dough"]["big_size"] is None:
                slot["missing_info"].append("size")
            if slot["dough"]["on_thick_pastry"] is None:
                slot["missing_info"].append("thickness")
            # if bezgluten, itp. – zależnie od logiki
    
        # Jeśli stworzono *nowe* sloty, zwracamy existing + new
        # Jeśli new_slots było puste, to zaktualizowaliśmy existing_slots w miejscu
        if new_slots:
            return existing_slots + new_slots
        else:
            return existing_slots

#
# @router.post("/analyze-order")
# def analyze_order(data: AnalyzeOrderRequest, db: Session = Depends(get_db)):
#     order = db.query(Order).filter(Order._id == data.order_id).first()
#     if not order:
#         return {"success": False, "message": f"Zamówienie {data.order_id} nie istnieje."}
#
#     parser = PizzaParser(db)
#     parsed_items = parser.parse_order(data.transcription)
#
#     if not parsed_items:
#         return {"success": False, "message": "Nie wykryto żadnych elementów zamówienia."}
#
#     responses = []
#     for slot in parsed_items:
#         pizza_obj = None
#         if slot["pizza"]:
#             pizza_obj = db.query(Pizza).filter(Pizza.name.ilike(slot["pizza"])).first()
#
#         # Budujemy zapytanie ciasta
#         query = db.query(Dough)
#         if slot["dough"]["big_size"] is not None:
#             query = query.filter(Dough.big_size == slot["dough"]["big_size"])
#         if slot["dough"]["on_thick_pastry"] is not None:
#             query = query.filter(Dough.on_thick_pastry == slot["dough"]["on_thick_pastry"])
#         dough_obj = query.first()
#
#         if pizza_obj and dough_obj:
#             new_item = OrderPizzas(
#                 order_id=order._id,
#                 pizza_id=pizza_obj._id,
#                 dough_id=dough_obj._id,
#                 quantity=slot["pizza_count"]
#                     )
#             db.add(new_item)
#             db.commit()
#             dough_desc = []
#             if slot["dough"]["big_size"] is None:
#                 dough_desc.append("NIE PODANO ROZMIARU (domyślne)")
#             else:
#                 dough_desc.append("duża" if slot["dough"]["big_size"] else "mała/średnia")
#
#             if slot["dough"]["on_thick_pastry"] is None:
#                 dough_desc.append("NIE PODANO GRUBOŚCI (domyślne)")
#             else:
#                 dough_desc.append("grube" if slot["dough"]["on_thick_pastry"] else "cienkie")
#
#             missing = f"(Braki: {slot['missing_info']})" if slot["missing_info"] else ""
#             resp = (
#                 f"{slot['pizza_count']}x {pizza_obj.name}, ciasto: {', '.join(dough_desc)} {missing} | "
#                 f"Extras: {slot['extras']}"
#             )
#             responses.append(resp)
#         else:
#             responses.append(f"Brak pizzy={pizza_obj} lub ciasta={dough_obj} => {slot}")
#
#     return {
#         "success": True,
#         "parsed_items": parsed_items,
#         "info": responses
#     }
