# path/filename: routers/analyze_order.py
"""
Rozszerzona wersja obsługująca 'domawianie' (np. "jeszcze poproszę dużą hawajską").
Wykorzystuje spaCy + fuzzywuzzy do analizy transkrypcji i generowania zamówień.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from fuzzywuzzy import process
import spacy

from ..database import get_db
from ..models import Order, Pizza, Dough, order_pizzas, Ingredient

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
	"średnia": ["średni", "średnią", "normalna"],
	"mała": ["mały", "małą"]
}
THICKNESS_SYNONYMS = {
	"gruba": ["gruby", "grube", "grubym"],
	"cienka": ["cienki", "cienkie", "cienkim"]
}
GLUTEN_SYNONYMS = {
	"bezglutenowa": ["bezglutenowe", "bezglutenowy", "bezglutenu"]
}

# Dodatkowe słowa wywołujące "nową pozycję" (domawianie)
ADDITIONAL_KEYWORDS = {"jeszcze", "dodatkowo", "kolejną", "kolejny", "kolejne", "następną", "następny"}


class AnalyzeOrderAdvanced:
	"""
	Zaawansowana klasa do analizy tekstu zamówienia:
	- wyodrębnia liczbę pizz, rodzaj ciasta (rozmiar, grubość, gluten),
	- obsługuje 'podwójny ser' i inne extra,
	- identyfikuje brakujące informacje,
	- pozwala obsługiwać 'jeszcze'/'dodatkowo' => domawianie kolejnej pizzy.
	"""
	def __init__(self, db_session: Session):
		self.db = db_session
		self.nlp = nlp

		# Pobieramy listę pizzy z bazy
		self.all_pizzas = self.db.query(Pizza).all()
		self.all_pizza_names = [p.name.lower() for p in self.all_pizzas]

		# Pobieramy rodzaje ciast
		self.all_doughs = self.db.query(Dough).all()

		# Pobieramy składniki
		self.all_ingredients = self.db.query(Ingredient).all()
		self.all_ingredients_names = [ing.name.lower() for ing in self.all_ingredients]

		# Zakładamy, że w polu 'category' mamy 'sauce' do sosów
		self.sauce_list = [
			ing.name.lower() for ing in self.all_ingredients
			if ing.category and ing.category.lower() == "sauce"
		]

	def _map_synonym(self, word: str, synonyms_dict: Dict[str, List[str]]) -> str:
		for key, synonyms in synonyms_dict.items():
			if word in synonyms:
				return key
		return word

	def _detect_number(self, token) -> int:
		if token.like_num:
			try:
				return int(token.text)
			except ValueError:
				return 1
		else:
			if token.lemma_ in POLISH_NUMBERS:
				return POLISH_NUMBERS[token.lemma_]
		return 1

	def _detect_multiplier(self, token) -> int:
		if token.lemma_ in POLISH_MULTIPLIERS:
			return POLISH_MULTIPLIERS[token.lemma_]
		return 1

	def _start_new_item_due_to_keyword(self, token_text: str) -> bool:
		"""
		Sprawdza, czy słowo jest w zbiorze 'ADDITIONAL_KEYWORDS' => sygnał nowej pizzy
		"""
		if token_text.lower() in ADDITIONAL_KEYWORDS:
			return True
		return False

	def analyze_text(self, text: str) -> List[dict]:
		"""
		Główna metoda analizująca transkrypt i zwracająca listę itemów zamówienia.
		Teraz także reaguje na słowa w stylu "jeszcze", "dodatkowo" –
		co interpretujemy jako rozpoczęcie nowej pozycji (jeśli zaraz potem
		pojawi się nazwa pizzy lub 'pizza').
		"""
		doc = self.nlp(text.lower())
		results = []

		# Funkcja pomocnicza do tworzenia pustego itemu
		def _new_item():
			return {
				"pizza": None,
				"pizza_count": 1,
				"dough": {
					"big_size": None,
					"on_thick_pastry": None,
					"without_gluten": False
				},
				"sauces": [],
				"extras": [],
				"missing_info": []
			}

		current_item = _new_item()

		i = 0
		while i < len(doc):
			token = doc[i]
			lemma = token.lemma_
			text_ = token.text

			# 1) Sprawdzamy “start nowej pozycji”:
			# - jeśli jest to "pizza"
			# - lub słowo kluczowe "jeszcze", “dodatkowo” etc. i zaraz potem (lub w najbliższych tokenach) pojawia się pizza
			# Dla uproszczenia: Gdy widzimy “jeszcze” to natychmiast “zamyka” poprzedni item i tworzy nowy.
			if lemma == "pizza" or self._start_new_item_due_to_keyword(text_):
				# jeśli current_item jest wypełnione, zapisz do results
				has_info = any([
					current_item["pizza"],
					current_item["dough"]["big_size"] is not None,
					current_item["dough"]["on_thick_pastry"] is not None
				])
				if has_info:
					results.append(current_item)
				# nowy item
				current_item = _new_item()

				# Jeśli lemma == "pizza", to nie “przeskakujemy” tokena,
				# bo zaraz może być dopasowanie do "hawajska", "pepperoni" etc.
				# natomiast jeśli to "jeszcze", to raczej przeskakujemy, bo “jeszcze” samo
				# nie jest pizzą.
				if lemma != "pizza":
					i += 1
					continue

			# 2) Dopasowanie do listy pizzy
			match_pizza = process.extractOne(text_, self.all_pizza_names, score_cutoff=70)
			if match_pizza:
				current_item["pizza"] = match_pizza[0]
				# ewentualna liczba w poprzednim tokenie => “dwie pepperoni”
				if i > 0:
					prev_token = doc[i-1]
					num_val = self._detect_number(prev_token)
					current_item["pizza_count"] = num_val

			# 3) Rozmiar (mała/duża/średnia)
			mapped_size = self._map_synonym(lemma, SIZE_SYNONYMS)
			if mapped_size in ("duża", "mała", "średnia"):
				current_item["dough"]["big_size"] = (mapped_size == "duża")

			# 4) Grubość (gruba/cienka)
			mapped_thick = self._map_synonym(lemma, THICKNESS_SYNONYMS)
			if mapped_thick == "gruba":
				current_item["dough"]["on_thick_pastry"] = True
			elif mapped_thick == "cienka":
				current_item["dough"]["on_thick_pastry"] = False

			# 5) Bezglutenowa
			mapped_gluten = self._map_synonym(lemma, GLUTEN_SYNONYMS)
			if mapped_gluten == "bezglutenowa":
				current_item["dough"]["without_gluten"] = True

			# 6) Sosy
			sauce_match = process.extractOne(text_, self.sauce_list, score_cutoff=70)
			if sauce_match:
				sauce_name = sauce_match[0]
				sauce_quantity = 1
				if i > 0:
					multiplier_val = self._detect_multiplier(doc[i-1])
					sauce_quantity *= multiplier_val
					sauce_quantity *= self._detect_number(doc[i-1])
				current_item["sauces"].append((sauce_name, sauce_quantity))

			# 7) Ser (podwójny itp.)
			if lemma == "ser":
				cheese_qty = 1
				if i > 0:
					cheese_qty *= self._detect_multiplier(doc[i-1])
					cheese_qty *= self._detect_number(doc[i-1])
				current_item["extras"].append(("ser", cheese_qty))

			# 8) Inne składniki z bazy
			ing_match = process.extractOne(text_, self.all_ingredients_names, score_cutoff=85)
			if ing_match and ing_match[0] != "ser":
				ing_qty = 1
				if i > 0:
					ing_qty *= self._detect_multiplier(doc[i-1])
					ing_qty *= self._detect_number(doc[i-1])
				current_item["extras"].append((ing_match[0], ing_qty))

			i += 1

		# na koniec dołóż ostatni item
		has_info = any([
			current_item["pizza"],
			current_item["dough"]["big_size"] is not None,
			current_item["dough"]["on_thick_pastry"] is not None
		])
		if has_info:
			results.append(current_item)

		# ustalamy brakujące informacje
		for item in results:
			if item["dough"]["big_size"] is None:
				item["missing_info"].append("size")
			if item["dough"]["on_thick_pastry"] is None:
				item["missing_info"].append("thickness")

		return results


@router.post("/analyze-order-advanced")
def analyze_order_advanced(data: AnalyzeOrderRequest, db: Session = Depends(get_db)):
	"""
	Zaawansowana analiza transkrypcji, obsługująca wielokrotne “domawianie” (słowa kluczowe typu "jeszcze",
	“dodatkowo”), np. "poproszę dużą hawajską, jeszcze małą pepperoni".
	Zapisujemy do order_pizzas i zwracamy, czego brakowało oraz co dodano.
	"""
	order = db.query(Order).filter(Order.id == data.order_id).first()
	if not order:
		return {"success": False, "message": f"Zamówienie {data.order_id} nie istnieje."}

	analyzer = AnalyzeOrderAdvanced(db)
	parsed_items = analyzer.analyze_text(data.transcription)

	if not parsed_items:
		return {"success": False, "message": "Nie wykryto żadnych elementów zamówienia."}

	responses = []
	for item in parsed_items:
		pizza_obj = None
		if item["pizza"]:
			pizza_obj = next(
				(p for p in analyzer.all_pizzas if p.name.lower() == item["pizza"]),
				None
			)

		# Dopasuj ciasto
		query = db.query(Dough)
		# Używamy .is_() dla None,
		# ale tutaj logicznie bierzemy "pierwsze" pasujące (ignorując None – bo to “niewspomniane”).
		if item["dough"]["big_size"] is not None:
			query = query.filter(Dough.big_size == item["dough"]["big_size"])
		if item["dough"]["on_thick_pastry"] is not None:
			query = query.filter(Dough.on_thick_pastry == item["dough"]["on_thick_pastry"])
		if item["dough"]["without_gluten"]:
			query = query.filter(Dough.without_gluten.is_(True))

		dough_obj = query.first()

		if pizza_obj and dough_obj:
			# Zapis do order_pizzas
			try:
				db.execute(
					order_pizzas.insert().values(
						order_id=order.id,
						pizza_id=pizza_obj.id,
						dough_id=dough_obj.id,
						quantity=item["pizza_count"]
					)
				)
				db.commit()
			except:
				return {"success": False, "message": f"Błąd zapisu do bazy danych: \norder {order}"
				                                     f"\npizza: {pizza_obj}\ndough: {dough_obj}"}
			# Komunikat
			dough_desc = []
			if item["dough"]["big_size"] is None:
				dough_desc.append("NIE PODANO ROZMIARU (domyślne ciasto)")
			else:
				dough_desc.append("duża" if item["dough"]["big_size"] else "mała/średnia")

			if item["dough"]["on_thick_pastry"] is None:
				dough_desc.append("NIE PODANO GRUBOŚCI (domyślne ciasto)")
			else:
				dough_desc.append("grube" if item["dough"]["on_thick_pastry"] else "cienkie")

			if item["dough"]["without_gluten"]:
				dough_desc.append("bezglutenowe")

			missing = item["missing_info"]
			if missing:
				missing_str = f"Brakujące parametry: {missing}"
			else:
				missing_str = ""

			resp_msg = f"[OK] {item['pizza_count']}x {pizza_obj.name} => ciasto: {', '.join(dough_desc)}. {missing_str}"
			# Extras / sosy
			if item["extras"]:
				resp_msg += f" | Extras: {item['extras']}"
			if item["sauces"]:
				resp_msg += f" | Sosy: {item['sauces']}"

			responses.append(resp_msg)
		else:
			info = "[BRAK]" if not pizza_obj else ""
			info2 = "[BRAK]" if not dough_obj else ""
			responses.append(f"Nie dodano do zamówienia: pizza={info}, ciasto={info2} => {item}")

	return {
		"success": True,
		"parsed_items": parsed_items,
		"info": responses
	}
