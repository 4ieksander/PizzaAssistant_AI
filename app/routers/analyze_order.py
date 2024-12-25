# path/filename: routers/analyze_order.py
"""
Plik służy do zaawansowanej analizy tekstu zamówienia
z wykorzystaniem spaCy i fuzzywuzzy.
Obsługuje wielokrotne sztuki, podwójne składniki, rozmiar ciasta itd.
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
	# Można rozszerzyć słownik
	"jeden":    1, "jedna": 1, "dwa": 2, "dwie": 2, "trzy": 3,
	"cztery":   4, "pięć": 5, "sześć": 6, "siedem": 7, "osiem": 8,
	"dziewięć": 9, "dziesięć": 10
	}
# Podwójny, potrójny itd. Gdy spotkamy "podwójny ser", interpretujemy "double cheese".
POLISH_MULTIPLIERS = {
	"podwójny": 2, "potrójny": 3, "poczwórny": 4
	}

# Przykładowe synonimy do atrybutów ciasta
SIZE_SYNONYMS = {
	"duża":    ["duży", "dużą", "wielka", "wielką", "family"],
	"średnia": ["średni", "średnią", "normalna"],
	"mała":    ["mały", "małą"]
	}
THICKNESS_SYNONYMS = {
	"gruba":  ["gruby", "grube", "grubym"],
	"cienka": ["cienki", "cienkie", "cienkim"]
	}
GLUTEN_SYNONYMS = {
	"bezglutenowa": ["bezglutenowe", "bezglutenowy", "bezglutenu"]
	}


class AnalyzeOrderAdvanced:
	"""
	Klasa do zaawansowanej analizy tekstu zamówienia:
	- wyodrębnia liczbę pizz, rodzaj ciasta, liczbę sosów
	- obsługuje 'podwójny ser' i inne extra
	"""
	
	def __init__(self, db_session: Session):
		self.db = db_session
		self.nlp = nlp
		
		# Wczytujemy z bazy listę pizzy:
		self.all_pizzas = self.db.query(Pizza).all()
		self.all_pizza_names = [p.name.lower() for p in self.all_pizzas]
		
		# Wczytujemy rodzaje ciast (można wykorzystać atrybuty: big_size, on_thick_pastry, without_gluten)
		self.all_doughs = self.db.query(Dough).all()
		
		# Można też wczytać dostępne składniki
		self.all_ingredients = self.db.query(Ingredient).all()
		self.all_ingredients_names = [ing.name.lower() for ing in self.all_ingredients]
		
		# Załóżmy, że w polu 'category' mamy w bazie 'sauce' dla sosów
		# (jeśli tak jest, można dynamicznie pobrać):
		self.sauce_list = [ing.name.lower() for ing in self.all_ingredients if ing.category.lower() == "sauce"]
	
	def _map_synonym(self, word: str, synonyms_dict: Dict[str, List[str]]) -> str:
		"""
		Przekształca słowo według synonimów (np. "dużą" -> "duża")
		"""
		for key, synonyms in synonyms_dict.items():
			if word in synonyms:
				return key
		return word
	
	def _detect_number(self, token) -> int:
		"""
		Spróbuj odczytać liczbę. Najpierw sprawdzamy, czy token jest liczbą.
		Jeśli nie, sprawdzamy słownik "POLISH_NUMBERS".
		"""
		if token.like_num:
			try:
				return int(token.text)
			except ValueError:
				return 1
		else:
			# np. "dwie", "trzy"
			if token.lemma_ in POLISH_NUMBERS:
				return POLISH_NUMBERS[token.lemma_]
		return 1
	
	def _detect_multiplier(self, token) -> int:
		"""
		Wyłapujemy "podwójny" (2), "potrójny" (3) itd.
		"""
		if token.lemma_ in POLISH_MULTIPLIERS:
			return POLISH_MULTIPLIERS[token.lemma_]
		return 1
	
	def analyze_text(self, text: str) -> List[dict]:
		"""
		Główna funkcja analizy:
		Zwraca listę 'elementów' zamówienia:
		[
		   {
			 'pizza': <str or None>,
			 'pizza_count': <int>,
			 'dough': { 'big_size': bool, 'on_thick_pastry': bool, 'without_gluten': bool } lub None
			 'sauces': [ (sauce_name, sauce_count) ],
			 'extras': [ (ingredient_name, quantity) ],
			 ...
		   },
		   ...
		]

		Złożone zdania staramy się rozbić heurystycznie.
		Dla uproszczenia – pociągniemy parsem spaCy i gdy zobaczymy
		słowo kluczowe 'pizza', wypełniamy nowy "entry".
		"""
		doc = self.nlp(text.lower())
		results = []
		current_item = {
			"pizza":       None,
			"pizza_count": 1,
			"dough":       {
				"big_size":        False,
				"on_thick_pastry": False,
				"without_gluten":  False
				},
			"sauces":      [],  # np. [("czosnkowy", 1), ("pomidorowy", 2)]
			"extras":      []  # np. [("ser", 2)]
			}
		
		# Heurystyka:
		# - Gdy wykryjemy "pizza" w tokenach, zamykamy stary item i tworzymy nowy.
		# - Wyszukujemy atrybuty (rozmiar ciasta, grubość) i do nich przypisujemy T/F
		# - Wyszukujemy "ser" i sprawdzamy czy w tokenach poprzednich stoi "podwójny"
		
		# Przy większej złożoności można by posługiwać się dependency parse.
		# Tu – prosta heurystyka + sprawdzanie najbliższych tokenów.
		
		i = 0
		while i < len(doc):
			token = doc[i]
			lemma = token.lemma_
			text_ = token.text
			
			# Sprawdzamy, czy token to "pizza" (lub fuzzy do "pizza"?)
			# Dla uproszczenia odwołujemy się do lemma_ == 'pizza'
			if lemma == "pizza":
				# Nowy item w zamówieniu – dotychczasowy zapisz do results, o ile ma cokolwiek
				if current_item["pizza"] or any([v for v in current_item["dough"].values()]):
					results.append(current_item)
				# Nowy "current_item"
				current_item = {
					"pizza":       None,
					"pizza_count": 1,
					"dough":       {
						"big_size":        False,
						"on_thick_pastry": False,
						"without_gluten":  False
						},
					"sauces":      [],
					"extras":      []
					}
			
			# Wyszukiwanie pizzy z bazy przez fuzzy
			# (w praktyce można to zrobić w innym miejscu, np.
			#  dopiero gdy zobaczymy token w stylu "margherita" itp.)
			match_pizza = process.extractOne(text_, self.all_pizza_names, score_cutoff=70)
			if match_pizza:
				# Zapisz tę pizzę
				current_item["pizza"] = match_pizza[0]
				
				# Czy w poprzednich tokenach jest liczba?
				# np. "dwie margherita" => pizza_count=2
				if i > 0:
					prev_token = doc[i - 1]
					count_val = self._detect_number(prev_token)
					current_item["pizza_count"] = count_val
			
			# Wyszukiwanie atrybutów ciasta
			# 1) rozmiar (duża/mała/średnia)
			mapped_size = self._map_synonym(lemma, SIZE_SYNONYMS)
			if mapped_size in ("duża", "mała", "średnia"):
				current_item["dough"]["big_size"] = (mapped_size == "duża")
			
			# 2) grubość
			mapped_thick = self._map_synonym(lemma, THICKNESS_SYNONYMS)
			if mapped_thick == "gruba":
				current_item["dough"]["on_thick_pastry"] = True
			elif mapped_thick == "cienka":
				current_item["dough"]["on_thick_pastry"] = False  # domyślne, ale ustawiamy jawnie
			
			# 3) gluten
			mapped_gluten = self._map_synonym(lemma, GLUTEN_SYNONYMS)
			if mapped_gluten == "bezglutenowa":
				current_item["dough"]["without_gluten"] = True
			
			# Wyszukiwanie sosów (np. "czosnkowy", "pomidorowy")
			# i liczby (np. "trzy sosy pomidorowe"?)
			sauce_match = process.extractOne(text_, self.sauce_list, score_cutoff=70)
			if sauce_match:
				sauce_name = sauce_match[0]
				# Sprawdzamy, czy jest "podwójny" itp. w otoczeniu
				# Tu – wystarczy spojrzeć na poprzedni token:
				sauce_quantity = 1
				if i > 0:
					multiplier_val = self._detect_multiplier(doc[i - 1])
					# + sprawdzamy, czy doc[i-1] jest liczebnikiem
					sauce_quantity *= multiplier_val
					sauce_quantity *= self._detect_number(doc[i - 1])
				current_item["sauces"].append((sauce_name, sauce_quantity))
			
			# Podwójny ser – sprawdzamy:
			# - jeżeli token.lemma_ == "ser", i w poprzednich tokenach "podwójny"
			#   tworzymy extras = ("ser", 2)
			if lemma == "ser":
				# Domyślna ilość sera to 1
				cheese_qty = 1
				# Sprawdzamy, czy poprzedni token to "podwójny" itp.
				if i > 0:
					multiplier_val = self._detect_multiplier(doc[i - 1])
					cheese_qty *= multiplier_val
					cheese_qty *= self._detect_number(doc[i - 1])
				current_item["extras"].append(("ser", cheese_qty))
			
			# Możemy także sprawdzić, czy to inny składnik z bazy (np. “pieczarki”)
			# i jeśli tak, dodać do extras (lub ustawić w samej pizzy).
			ing_match = process.extractOne(text_, self.all_ingredients_names, score_cutoff=85)
			if ing_match and ing_match[0] != "ser":  # bo "ser" już obsłużyliśmy
				# Podobnie, sprawdzamy poprzednie tokeny
				ing_qty = 1
				if i > 0:
					multiplier_val = self._detect_multiplier(doc[i - 1])
					ing_qty *= multiplier_val
					ing_qty *= self._detect_number(doc[i - 1])
				current_item["extras"].append((ing_match[0], ing_qty))
			
			i += 1
		
		# Na koniec dołóż ostatni "item", jeśli cokolwiek tam jest
		if current_item["pizza"] or any([v for v in current_item["dough"].values()]):
			results.append(current_item)
		
		return results


@router.post("/analyze-order")
def analyze_order_advanced(data: AnalyzeOrderRequest, db: Session = Depends(get_db)):
	"""
	Zaawansowana analiza transkrypcji.
	Tworzy/aktualizuje zamówienie w order_pizzas z wieloma pizzami i atrybutami.
	"""
	order = db.query(Order).filter(Order.id == data.order_id).first()
	if not order:
		return {"success": False, "message": f"Zamówienie {data.order_id} nie istnieje."}
	
	analyzer = AnalyzeOrderAdvanced(db)
	parsed_items = analyzer.analyze_text(data.transcription)
	
	if not parsed_items:
		return {"success": False, "message": "Nie wykryto żadnych elementów zamówienia."}
	
	# Dodajemy do bazy
	responses = []
	for item in parsed_items:
		# Znajdź obiekt Pizza
		# item["pizza"] to nazwa 'margherita' itp.
		# W oryginale mamy w all_pizza_names, więc:
		pizza_obj = None
		if item["pizza"]:
			pizza_obj = next((p for p in analyzer.all_pizzas if p.name.lower() == item["pizza"]), None)
		
		# Wyznaczmy ciasto
		dough_obj = None
		# Filtrujemy bazę Dough po kluczach:
		# big_size => item["dough"]["big_size"]
		# on_thick_pastry => ...
		# without_gluten => ...
		# W najprostszej wersji, bierzemy "pierwszy" pasujący wariant:
		dough_obj = db.query(Dough).filter(
			Dough.big_size == item["dough"]["big_size"],
			Dough.on_thick_pastry == item["dough"]["on_thick_pastry"],
			Dough.without_gluten == item["dough"]["without_gluten"]
			).first()
		
		# Wstaw do order_pizzas
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
			responses.append(
				f"{item['pizza_count']}x {pizza_obj.name}"
				f" (duże={item['dough']['big_size']}, grube={item['dough']['on_thick_pastry']}, "
				f"bezglutenowe={item['dough']['without_gluten']})"
				)
			# Dodatkowo obsłużyć extras i sauces w zależności od logiki (np. w osobnej tabeli).
			# Obecnie tylko dopisujemy do 'responses'.
			if item["extras"]:
				responses.append(f"Extras: {item['extras']}")
			if item["sauces"]:
				responses.append(f"Sosy: {item['sauces']}")
		else:
			responses.append(f"Brak pasującej pizzy/ciasta w bazie -> {item}")
	
	return {
		"success":      True,
		"parsed_items": parsed_items,
		"info":         responses
		}
