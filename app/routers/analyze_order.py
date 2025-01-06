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
    "duża": ["duży", "dużą", "wielki", "wielką", "family"],
    "mała": ["mały", "małą", "średni"]
}
THICKNESS_SYNONYMS = {
    "gruba": ["gruby", "grube", "grubym"],
    "cienka": ["cienki", "cienkie", "cienkim"]
}
REFERENCE_SLOT_WORDS  = {
    "pierwsza": 1,
    "druga": 2,
    "trzecia": 3,
    "czwarta": 4,
    "piąta": 5,
    "szósta": 6,
    "siódma": 7,
    "ósma": 8,
    "dziewiąta": 9,
    "ostatnia": 0
}
NEW_SLOT_WORDS = {
    "nowa": 1,
    "kolejna": 1,
    "następna": 1,
    "następnie": 1,
    "jeszcze": 1,
    "dodatkowa": 1,
    "dodatkowo": 1,
    "inna": 1,
    "inny": 1,
    "domówić": 1,
    }

REFERENCE_ALL_SLOTS = {
    "wszystek": 0,
    "każda": 0,
    "każdej": 0,
    "każde": 0,
    "każdy": 0,
    "wszystkie": 0,
    "wszystkich": 0,
    "wszystkim": 0,
    "wszystkimi": 0
    }
    
def _map_synonym_with_dict(word: str, synonyms_dict: dict, return_none=False):
    """
    Funkcja pomocnicza do mapowania słowa na klucz, jeśli występuje w słowniku synonimów.
    """
    for key, synonyms in synonyms_dict.items():
        if word in synonyms:
            return key
    if return_none:
        return None
    else:
        return word

def _is_big_pizza_size(lemma) -> bool:
    """
    Sprawdza, czy token to synonim dużego rozmiaru pizzy.
    """
    return _map_synonym_with_dict(lemma, SIZE_SYNONYMS) == "duża"

def detect_number_if_any(token, return_none=False):
    if return_none:
        val = None
    else:
        val = 1
    log.info("token: %s, %s, %s, %s", token.text, token.lemma_, token.like_num, token)
    if token.like_num:
        try:
            val = int(token.text)
        except:
            if return_none:
                val = POLISH_NUMBERS.get(token.text, None)
            else:
                val = POLISH_NUMBERS.get(token.text, 1)
    elif token.lemma_ in POLISH_NUMBERS:
        val = POLISH_NUMBERS[token.lemma_]
    elif token.text in POLISH_NUMBERS:
        val = POLISH_NUMBERS[token.text]
    log.info("Detected number: %s", val)
    
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
    if best_score >= 66:
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


def _detect_slot_references(tokens, existing_slots):
    chosen_slot_index = None
    i = 0
    while i < len(tokens):
        log.info("Jestem w petli %s", i)
        t = tokens[i].lemma_.lower()
        if t in ("do", "w", "ta"):
            if (i + 1) < len(tokens):
                maybe_tej = tokens[i + 1].lemma_.lower()
                if maybe_tej in ("tej"):
                     if (i + 2) < len(tokens):
                        lem =  tokens[i + 2].lemma_.lower()
                        log.info("ref_word: %s -> lema %s", tokens[i+2].text, lem)
                        if lem in REFERENCE_SLOT_WORDS:
                            number = REFERENCE_SLOT_WORDS[lem]
                            slot_idx = number - 1
                            if slot_idx < len(existing_slots):
                                chosen_slot_index = slot_idx
                                break
                        pizza_name = fuzzy_match_pizza(tokens[i+2].text, [s.get("pizza") for s in existing_slots])
                        if pizza_name:
                            for i, slot in enumerate(existing_slots):
                                if slot["pizza"] == pizza_name:
                                    chosen_slot_index = i
                                    break
                elif tokens[i+1] in REFERENCE_SLOT_WORDS:
                    number = REFERENCE_SLOT_WORDS[tokens[i+1]]
                    slot_idx = number - 1
                    if slot_idx < len(existing_slots):
                        chosen_slot_index = slot_idx
                        break
                elif maybe_tej in ("pizzy", "pizze"):
                    if (i + 2) < len(tokens):
                        next_lemma = tokens[i + 2].lemma_.lower()
                        if next_lemma in ("numer") and (i + 3) < len(tokens):
                            if detect_number_if_any(tokens[i+3], return_none=True):
                                slot_idx = detect_number_if_any(tokens[i+3]) -1
                                if slot_idx < len(existing_slots):
                                    chosen_slot_index = slot_idx
                                    break
                        else:
                            pizza_name = fuzzy_match_pizza(tokens[i+2].text, [s.get("pizza") for s in existing_slots])
                            if pizza_name:
                                for i, slot in enumerate(existing_slots):
                                    if slot["pizza"] == pizza_name:
                                        chosen_slot_index = i
                                        break
        i += 1
    return chosen_slot_index


def _detect_pizza_count(tokens, slots: List[dict], all_pizzas: List[str])  -> List[dict]:
    slots_created = False
    i = 0
    while i < len(tokens):
        log.info("Pętla detect_pizza_count: %s", i)
        token = tokens[i]
        lemma = token.lemma_
        if detect_number_if_any(token, return_none=True) and (i + 1) < len(tokens):
            next_lemma = tokens[i + 1].lemma_
            pizza_name = fuzzy_match_pizza(tokens[i+1].text, all_pizzas)
            log.info("next_lemma: %s", next_lemma)
            if "pizz" in next_lemma or pizza_name:
                count_val = detect_number_if_any(token, return_none=True)
                if pizza_name:
                    log.info("Znalazłem pizzę: %s", pizza_name)
                    slot = _create_slot()
                    slot["pizza_count"] = count_val
                    slot["pizza"] =  pizza_name
                    slots.append(slot)
                elif (i +2) < len(tokens) and fuzzy_match_pizza(tokens[i+2].text, all_pizzas):
                    log.info("Znalazłem pizzę przy 2gim podejsciu: %s", tokens[i+2].text)
                    slot = _create_slot()
                    slot["pizza_count"] = count_val
                    slot["pizza"] =  fuzzy_match_pizza(tokens[i+2].text, all_pizzas)
                    slots.append(slot)
                else:
                    for _ in range(count_val):
                        slots.append(_create_slot())
                slots_created = True
                i += 2
            elif  _map_synonym_with_dict(next_lemma, SIZE_SYNONYMS, return_none=True) and (i + 2) < len(tokens):
                log.info("Znalazłem rozmiar pizzy: %s", tokens[i+1].text)
                next_next_lemma = tokens[i + 2].lemma_
                pizza_name = fuzzy_match_pizza(tokens[i+2].text, all_pizzas)
                if "pizz" in next_next_lemma or pizza_name:
                    count_val = detect_number_if_any(tokens[i])
                    if pizza_name:
                        slot = _create_slot()
                        slot["pizza_count"] = count_val
                        slot["pizza"] = pizza_name
                        if _map_synonym_with_dict(next_lemma, SIZE_SYNONYMS) == "duża":
                            slot["dough"]["big_size"] = True
                        else:
                            slot["dough"]["big_size"] = False
                        slot["dough"]["big_size"] = next_lemma == "duża"
                        slots.append(slot)
                    elif (i + 3) < len(tokens) and fuzzy_match_pizza(tokens[i+3].text, all_pizzas):
                        slot = _create_slot()
                        slot["pizza_count"] = count_val
                        slot["pizza"] = fuzzy_match_pizza(tokens[i+3].text, all_pizzas)
                        slots.append(slot)
                    else:
                        for _ in range(count_val):
                            slot = _create_slot()
                            slot["dough"]["big_size"] = _is_big_pizza_size(next_lemma)
                            slots.append(slot)
                    i += 3
                    slots_created = True
                    log.info("slots: %s", slots)
                    continue
            i += 1
            continue

        if (lemma == "pizza" or fuzzy_match_pizza(tokens[i].text, all_pizzas)) and not slots_created:
            slots_created = True
            slot = _create_slot()
            if not lemma in "pizza":
                slot["pizza"] = fuzzy_match_pizza(tokens[i-1].text, all_pizzas)
            slots.append(slot)
            i += 1
            continue
        i += 1
    log.info("slots_created: %s -> %s", slots_created, slots)
    return slots

def _create_slot() -> dict:
    """
    Tworzy nowy slot opisujący pojedynczą sztukę pizzy.
    """
    log.info("Tworzę nowy slot")
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
                       common_attributes: dict, active_slot = None ):
    """
    Przypisuje do slotów atrybuty takie jak nazwa pizzy, rozmiar, grubość.
    Jeśli nie ma żadnego slotu, zapisuje w 'common_attributes', by potem scalić je do wszystkich.
    """
    i = 0
    if active_slot:
        slot = active_slot
    elif slots:
        slot = slots[-1]
    
        
    while i < len(tokens):
        log.info("pętla assign_attributes: %s", i)
        txt = tokens[i].text.lower()
        lemma = tokens[i].lemma_.lower()
                #rozmiar
        mapped_size = _map_synonym_with_dict(lemma, SIZE_SYNONYMS)
        if mapped_size in ("duża", "mała"):
            log.info("mapped_size: %s", mapped_size)
            if slots:
                slot["dough"]["big_size"] = (mapped_size == "duża")
                log.info("dodaje do slotu %s", slot)
            else:
                common_attributes["dough"]["big_size"] = (mapped_size == "duża")
                log.info("dodaje do wspólnych atrybutów")
            i += 1
            continue
        
        #grubość
        mapped_thick = _map_synonym_with_dict(lemma, THICKNESS_SYNONYMS)
        if mapped_thick in ("gruba", "cienka"):
            on_thick = (mapped_thick == "gruba")
            if slots:
                slot["dough"]["on_thick_pastry"] = on_thick
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
            i += 1
            continue
        i += 1


def _assign_extras_trigram(tokens, slots: List[dict], all_ingredients: List[str],
                           common_attributes: dict, active_slot: dict = None):
    """
    Szuka w tekście 3-gramów w stylu:
      - [z/dodatkową], [podwójną/potrójną?], [nazwę składnika]
    lub odwrotny wariant itd.
    Jeżeli znajdzie, to wstawia do slots[-1]["extras"] np.: (składnik, qty).
    """
    log.info("Assigning extras")
    i = 0
    if active_slot:
        slot = active_slot
    elif slots:
        slot = slots[-1]

    if i == len(tokens) - 2:
        if _about_additional_ing_words(tokens[i].lemma_):
            best_ing, sc = fuzzy_find_ingredient(tokens[i+1].text.lower(), all_ingredients)
            if sc > 70 and best_ing:
                qty = 1
                if slots:
                    slot["extras"].append((best_ing, qty))
                else:
                    common_attributes["extras"].append((best_ing, qty))
                    
    while i <= len(tokens) - 3:
        if _about_additional_ing_words(tokens[i].lemma_) and _about_additional_ing_words(tokens[i+1].lemma_) and i < len(tokens) - 4:
            i += 1  # aby wykrywanie rozbudowanych fraz było bardziej dokładne
        tri = tokens[i], tokens[i+1], tokens[i+2]
        tri_text = [tok.text.lower() for tok in tri]
        tri_lemma = [tok.lemma_.lower() for tok in tri]
        log.info("TRIGRAM: %s", tri_text)
        log.info("TRIGRAM: %s LEMMA", tri_lemma)
        # CASE A: [z|dodatk*], [multipler], [ingredient]
        if _about_additional_ing_words(tri_lemma[0]):
            multiplier = detect_multiplier_if_any(tri[1])
            best_ing, sc = fuzzy_find_ingredient(tri_text[2], all_ingredients)
            if sc > 70 and best_ing:
                qty = multiplier
                if slots:
                    slot["extras"].append((best_ing, qty))
                else:
                    common_attributes["extras"].append((best_ing, qty))
                    
                log.info("Dodano składnik: %s x %s", best_ing, qty)
                if len(tokens) >= i + 4:
                    check_for_extra_ingredient(tokens[i + 3:], all_ingredients, slots, common_attributes)
                
                i += 3
                continue
 
        # CASE B: [z|dodatk*], [ingredient], [multipler/ "i" / "oraz"], OPT [second ingredient]
        if _about_additional_ing_words(tri_lemma[0]):
            best_ing, sc = fuzzy_find_ingredient(tri_text[1], all_ingredients)
            if sc > 70 and best_ing:
                if tri_lemma[2] in ("i", "oraz") and len(tokens) >= i + 3:
                    best_second_ing, sc2 = fuzzy_find_ingredient(tokens[i+3], all_ingredients)
                    if sc2 > 70 and best_second_ing and slots:
                        slot["extras"].append((best_second_ing, 1))
                    qty = 1
                else:
                    multiplier = detect_multiplier_if_any(tri[2])
                    qty = multiplier if multiplier > 1 else 1
                if not qty:
                    qty = 1
                if slots:
                    slot["extras"].append((best_ing, qty))
                else:
                    common_attributes["extras"].append((best_ing, qty))
                if len(tokens) >= i + 3:
                    check_for_extra_ingredient(tokens[i + 3:], all_ingredients, slots, common_attributes)
                
                i += 3
                continue

        # CASE C: [multipler], [dodatk*|z], [ingredient]
        if detect_multiplier_if_any(tri[0]) > 1 and _about_additional_ing_words(tri_lemma[1]):
            best_ing, sc = fuzzy_find_ingredient(tri_text[2], all_ingredients)
            if sc > 70 and best_ing:
                qty = detect_multiplier_if_any(tri[0])
                if slots:
                    slot["extras"].append((best_ing, qty))
                else:
                    common_attributes["extras"].append((best_ing, qty))
                if len(tokens) >= i + 3:
                    check_for_extra_ingredient(tokens[i + 3:], all_ingredients, slots, common_attributes)
                
                i += 3
                continue
    
        i += 1

def _about_additional_ing_words(lemma):
    if "dodatk" in lemma.lower() or "z" in lemma.lower():
        return True
    return False

def check_for_extra_ingredient(tokens, all_ingredients, slots, common_attributes, active_slot: dict = None):
    if active_slot:
        slot = active_slot
    elif slots:
        slot = slots[-1]
    def add_extra_ingredient(ingredient, quantity):
        """Dodaje składnik do odpowiedniego miejsca (slotów lub wspólnych atrybutów)."""
        log.info("Dodano składnik: %s x %s", ingredient, quantity)
        if slots:
            slot["extras"].append((ingredient, quantity))
        else:
            common_attributes["extras"].append((ingredient, quantity))

    if tokens and tokens[0].lemma_ in ("i", "oraz"):
        if len(tokens) > 2:
            qty = detect_multiplier_if_any(tokens[1])
            best_ing, sc = fuzzy_find_ingredient(tokens[2].text.lower(), all_ingredients)
        elif len(tokens) > 1:
            qty = 1
            best_ing, sc = fuzzy_find_ingredient(tokens[1].text.lower(), all_ingredients)
        else:
            return
    else:
        best_ing, sc = fuzzy_find_ingredient(tokens[0].text.lower(), all_ingredients)
        if sc > 70 and best_ing:
            qty = 1
            add_extra_ingredient(best_ing, qty)
            return
        if len(tokens) > 1:
            qty = detect_multiplier_if_any(tokens[0])
            best_ing, sc = fuzzy_find_ingredient(tokens[1].text.lower(), all_ingredients)
    if sc > 70 and best_ing:
        add_extra_ingredient(best_ing, qty)
        
        
def merge_and_find_missing(slots: List[dict], common_attributes: dict):
    for slot in slots:          # scal wspólne z slotami
        if slot["dough"]["big_size"] is None and common_attributes["dough"]["big_size"] is not None:
            slot["dough"]["big_size"] = common_attributes["dough"]["big_size"]
        if slot["dough"]["on_thick_pastry"] is None and common_attributes["dough"][
            "on_thick_pastry"] is not None:
            slot["dough"]["on_thick_pastry"] = common_attributes["dough"]["on_thick_pastry"]
        slot["extras"].extend(common_attributes["extras"])
    
    for slot in slots:      # Wyznacz braki
        slot["missing_info"] = []
        if slot["pizza"] is None:
            slot["missing_info"].append("Nazwa pizzy")
        if slot["dough"]["big_size"] is None:
            slot["missing_info"].append("Rozmiar")
        if slot["dough"]["on_thick_pastry"] is None:
            slot["missing_info"].append("Grubość ciasta")


class PizzaParser:
    def __init__(self, db: Session):
        self.db = db
        self.nlp = nlp
        self.all_pizzas = [p.name.lower() for p in db.query(Pizza).all()]
        self.all_ingredients = [ing.name.lower() for ing in db.query(Ingredient).all()]

    def parse_order(self, text: str) -> List[dict]:
        doc = self.nlp(text.lower())
        tokens = list(doc)
        
        for token in doc:
            log.info(f"{token.text}: {token.pos_}, {token.dep_}, {token.head.text}")
        # for chunk in doc.noun_chunks:
        #     log.info(chunk.text)
        log.info("Text: %s", text)
        log.info("Tokens: %s", tokens)
        log.info("Tokens Lemma %s", [t.lemma_ for t in tokens])
        # log.info("Existing slots: %s", existing_slots)
        common_attributes = {
            "dough": {
                "big_size": None,
                "on_thick_pastry": None,
            },
            "extras": []
        }
        slots: List[dict] = []
        slots = _detect_pizza_count(tokens, slots,  self.all_pizzas)

        _assign_attributes(tokens, slots, self.all_pizzas, common_attributes)
        _assign_extras_trigram(tokens, slots, self.all_ingredients, common_attributes)
    
        merge_and_find_missing(slots, common_attributes)
        
        return slots
    
    def parse_order_in_context(self, text: str, existing_slots: List[dict]) -> List[dict]:
        log.info(40*"-x-")
        reference_to_all = False
        doc = self.nlp(text.lower())
        tokens = list(doc)
        for token in doc:
            log.info(f"{token.text}: {token.pos_}, {token.dep_}, {token.head.text}")
        log.info("Text: %s", text)
        log.info("Tokens: %s", tokens)
        log.info("Tokens Lemma %s", [t.lemma_ for t in tokens])
        log.info("Existing slots: %s", existing_slots)
        
        slot_idx_ref = _detect_slot_references(tokens, existing_slots)
        common_attributes = {"dough": {"big_size": None, "on_thick_pastry": None}, "extras": []}
        
        if slot_idx_ref is not None:
            active_slot = existing_slots[slot_idx_ref]
            _assign_attributes(tokens, existing_slots, self.all_pizzas, common_attributes, active_slot)
            _assign_extras_trigram(tokens, existing_slots, self.all_ingredients, common_attributes, active_slot)
            merge_and_find_missing([active_slot], common_attributes)
            return existing_slots
        
        else:
            new_slots: List[dict] = []
            if existing_slots:
                for idx, slot in enumerate(existing_slots):
                    if slot['missing_info']:
                        new_slots.append(slot)
                        existing_slots.pop(idx)
                slots_to_fill = new_slots
            else:
                new_slots = _detect_pizza_count(tokens, new_slots, self.all_pizzas)
                slots_to_fill = new_slots if new_slots else existing_slots
            for token in tokens:
                if token.text.lower() in REFERENCE_ALL_SLOTS:
                    reference_to_all = True
            if reference_to_all:
                _assign_attributes(tokens, [], self.all_pizzas, common_attributes)
                _assign_extras_trigram(tokens, [], self.all_ingredients, common_attributes)
            else:
                _assign_attributes(tokens, slots_to_fill, self.all_pizzas, common_attributes)
                _assign_extras_trigram(tokens, slots_to_fill, self.all_ingredients, common_attributes)
            
            merge_and_find_missing(slots_to_fill, common_attributes)
            
            return existing_slots + new_slots if new_slots else existing_slots

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
