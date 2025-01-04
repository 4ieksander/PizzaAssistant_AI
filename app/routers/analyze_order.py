# path/filename: routers/analyze_order.py
"""
Rozbudowana wersja algorytmu, która radzi sobie lepiej z takimi przypadkami, jak:
- "Chciałbym zamówić dwie duże pizze margarity, jedna na grubym a druga na cienkim cieście
  z dodatkowym serem i z trzema sosami łagodnymi."
- Wykrywa faktycznie 2 osobne pizze, bo mają różne atrybuty grubości.
- Fuzzy match 'margarity' => 'margherita'
- Ogranicza losowe dopasowanie 'ananas' czy 'bazylia' w tym tekście.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
import spacy
from fuzzywuzzy import fuzz  # zamiast extractOne, użyjemy jednego z metod fuzzy

from ..database import get_db
from ..models import Order, Pizza, Dough, order_pizzas, Ingredient


router = APIRouter()
nlp = spacy.load("pl_core_news_md")


class AnalyzeOrderRequest(BaseModel):
	order_id: int
	transcription: str


# Słowniki liczb i mnożników
POLISH_NUMBERS = {
	"jeden":    1, "jedna": 1, "dwa": 2, "dwie": 2, "trzy": 3,
	"cztery":   4, "pięć": 5, "sześć": 6, "siedem": 7, "osiem": 8,
	"dziewięć": 9, "dziesięć": 10
	}
POLISH_MULTIPLIERS = {
	"podwójny": 2, "potrójny": 3, "poczwórny": 4
	}
SIZE_SYNONYMS = {
	"duża":    ["duży", "dużą", "wielka", "wielką", "family"],
	"mała":    ["mały", "małą", "średnia"]
	}
THICKNESS_SYNONYMS = {
	"gruba":  ["gruby", "grube", "grubym"],
	"cienka": ["cienki", "cienkie", "cienkim"]
	}
GLUTEN_SYNONYMS = {
	"bezglutenowa": ["bezglutenowe", "bezglutenowy", "bezglutenu"]
	}

REFERENCE_WORDS_FOR_NEXT = {
	"jedna":   1,
	"druga":   2,
	"trzecia": 3,
	"czwarta": 4}


def fuzzy_match_pizza(candidate: str, pizza_names: List[str]) -> Optional[str]:
	best_score = 0
	best_name = None
	for p_name in pizza_names:
		score = fuzz.ratio(candidate, p_name)  # lub partial_ratio
		if score > best_score:
			best_score = score
			best_name = p_name
	# Wymuśmy np. próg 60-70
	if best_score >= 60:
		return best_name
	return None


class AdvancedPizzaParser:
	"""
	Parser, który radzi sobie z wieloma pizzami i atrybutami w jednym zdaniu:
	1. Wykrywa liczbę i 'pizze' => tworzy X 'slotów' (np. "dwie pizze" => 2 sloty),
	   wypełnia je wykrytą nazwą, rozmiarem.
	2. Gdy znajdzie formułę 'jedna / druga / trzecia' => ustawia atrybut w danym slocie.
	3. Na koniec, jeśli user podaje atrybuty bez wspomnienia 'jedna/druga',
	   traktujemy je jako atrybut dla wszystkich dotychczas 'otwartych' slotów.
	4. Ograniczamy dopasowanie składników do sytuacji, gdy stoi przed nimi "z", "dodatkowy/dodatkową", itp.
	"""
	
	def __init__(self, db: Session):
		self.db = db
		self.nlp = nlp
		
		self.all_pizzas = [p.name.lower() for p in db.query(Pizza).all()]
		self.all_ingredients = [ing.name.lower() for ing in db.query(Ingredient).all()]
		self.sauce_list = [
			ing.name.lower() for ing in db.query(Ingredient).filter(Ingredient.category == "sauce")
			]
	
	def parse_order(self, text: str) -> List[dict]:
		"""
		Zwraca listę dictów opisujących poszczególne pizze:
		[
		  {
			"pizza": "margherita",
			"pizza_count": 1,
			"dough": {...},
			"sauces": [...],
			"extras": [...],
			"missing_info": [...]
		  },
		  ...
		]
		"""
		doc = self.nlp(text.lower())
		
		results: List[dict] = []
		# tymczasowy obiekt "szablonu" (gdy user nie używa 'jedna/druga', staje się atrybutem wspólnym)
		common_attributes = {
			"dough":  {
				"big_size":        None,
				"on_thick_pastry": None,
				"without_gluten":  False
				},
			"sauces": [],
			"extras": []
			}
		
		# Każdy slot = {'pizza': None, 'count':1, 'dough':..., 'extras':..., 'missing_info':...}
		def create_slot():
			return {
				"pizza":        None,
				"pizza_count":  1,
				"dough":        {
					"big_size":        None,
					"on_thick_pastry": None,
					"without_gluten":  False
					},
				"sauces":       [],
				"extras":       [],
				"missing_info": []
				}
		
		# Będziemy mieć listę slotów
		slots: List[dict] = []
		
		# Wstępna logika:
		# 1) Szukamy wzorca: <NUM> (pizze) <pizza_name>? => tworzymy tyle slotów
		# 2) “duża/mała” => dopisujemy do slotów, jeśli jeszcze nie przydzielono
		# 3) “jedna/druga/trzecia” => przerzucamy atrybut do odpowiedniego slotu
		# 4) pozostałe atrybuty => jeśli występują w sekwencji z “z / dodatkowo” itp.,
		#    przypisujemy do (ostatniego) slotu lub do wszystkich, zależnie od heurystyki
		
		tokens = list(doc)
		i = 0
		total_slots_created = False  # sygnalizuje, że już rozbiliśmy na x slotów
		while i < len(tokens):
			t = tokens[i]
			lemma = t.lemma_
			txt = t.text
			
			# Sprawdź, czy to “dwie/dwa/trzy” i za chwilę “pizza/pizze”
			if lemma in POLISH_NUMBERS:
				# popatrzmy w przód, czy występuje “pizza/pizze”
				if i + 1 < len(tokens):
					next_lemma = tokens[i + 1].lemma_
					if "pizza" in next_lemma:  # prosta heurystyka
						count_val = POLISH_NUMBERS[lemma]
						# sprawdźmy, czy user podał nazwę pizzy w najbliższych słowach
						# (np. “dwie duże pizze margarity”)
						# Stworzymy 'count_val' slotów
						for _ in range(count_val):
							slots.append(create_slot())
						
						total_slots_created = True
						i += 2  # bo zużyliśmy i+1
						continue
			
			# Sprawdź, czy to “pizza” w liczbie pojedynczej bez “dwie/trzy”
			# => 1 slot
			if lemma == "pizza" and not total_slots_created:
				# user powiedział “jedna pizza margherita” bez “jeden/jedna”
				# => stwórz 1 slot
				slots.append(create_slot())
				total_slots_created = True
				i += 1
				continue
			
			# Fuzzy match do pizzy, np. “margarity” => “margherita”
			matched_pizza = fuzzy_match_pizza(txt, self.all_pizzas)
			if matched_pizza:
				# Wstaw do *ostatniego slotu*, o ile istnieje –
				# inaczej stwórz nowy
				if not slots:
					slots.append(create_slot())
					total_slots_created = True
				
				last_slot = slots[-1]
				last_slot["pizza"] = matched_pizza
				
				# ewentualnie sprawdzamy, czy w poprzednim tokenie jest “dwie/dwa/trzy”
				if i > 0:
					prev = tokens[i - 1].lemma_
					if prev in POLISH_NUMBERS:
						last_slot["pizza_count"] = POLISH_NUMBERS[prev]
				i += 1
				continue
			
			# Rozmiar
			mapped_size = _map_synonym_with_dict(lemma, SIZE_SYNONYMS)
			if mapped_size in ("duża", "mała", "średnia"):
				if slots:
					slots[-1]["dough"]["big_size"] = (mapped_size == "duża")
				else:
					common_attributes["dough"]["big_size"] = (mapped_size == "duża")
				i += 1
				continue
			
			# Grubość
			mapped_thick = _map_synonym_with_dict(lemma, THICKNESS_SYNONYMS)
			if mapped_thick == "gruba":
				# Może dotyczyć “jednej” z kilku pizz.
				# sprawdź, czy user powiedział “jedna”
				# np. “jedna na grubym, druga na cienkim”
				# w takiej sytuacji: jeśli jest “jedna” w okolicy,
				# przypisujemy do slotu #1, “druga” => do slotu #2 itd.
				# w prostszej wersji => if last lemma is “jedna” => slot[0]
				assigned = False
				if i > 0 and tokens[i - 1].lemma_ in REFERENCE_WORDS_FOR_NEXT:
					slot_idx = REFERENCE_WORDS_FOR_NEXT[tokens[i - 1].lemma_] - 1
					if slot_idx < len(slots):
						slots[slot_idx]["dough"]["on_thick_pastry"] = True
						assigned = True
				if not assigned:
					# wstaw do *ostatniego slotu* albo do common attributes
					if slots:
						slots[-1]["dough"]["on_thick_pastry"] = True
					else:
						common_attributes["dough"]["on_thick_pastry"] = True
				i += 1
				continue
			
			elif mapped_thick == "cienka":
				assigned = False
				if i > 0 and tokens[i - 1].lemma_ in REFERENCE_WORDS_FOR_NEXT:
					slot_idx = REFERENCE_WORDS_FOR_NEXT[tokens[i - 1].lemma_] - 1
					if slot_idx < len(slots):
						slots[slot_idx]["dough"]["on_thick_pastry"] = False
						assigned = True
				if not assigned:
					if slots:
						slots[-1]["dough"]["on_thick_pastry"] = False
					else:
						common_attributes["dough"]["on_thick_pastry"] = False
				i += 1
				continue
			
			# Bezglutenowa
			mapped_gluten = _map_synonym_with_dict(lemma, GLUTEN_SYNONYMS)
			if mapped_gluten == "bezglutenowa":
				if slots:
					slots[-1]["dough"]["without_gluten"] = True
				else:
					common_attributes["dough"]["without_gluten"] = True
				i += 1
				continue
			
			# Sosy / extras – heurystyka: sprawdzamy czy jest “z” / “dodatkowy” / “z trzema”
			# (poniżej dość uproszczone)
			if i > 0:
				prev_txt = tokens[i - 1].text.lower()
				# “z” / “z trzema” / “dodatkowym”?
				if "z" in prev_txt or "dodatk" in prev_txt:
					# sprawdzamy, czy to sos
					if txt in self.sauce_list:
						# a może user powiedział “trzema sosami łagodnymi” => i jest tam ‘łagodny’
						# Spróbujmy odczytać liczbę z ewentualnie poprzednich tokenów
						sauce_qty = 1
						# spójrz wstecz
						if i - 2 >= 0:
							sauce_qty *= detect_number_if_any(tokens[i - 2])
							sauce_qty *= detect_multiplier_if_any(tokens[i - 2])
						
						# wstaw do *ostatniego slotu*
						if slots:
							slots[-1]["sauces"].append((txt, sauce_qty))
						else:
							common_attributes["sauces"].append((txt, sauce_qty))
					else:
						# Może to inny składnik => ser?
						if txt == "ser":
							cheese_qty = 1
							# sprawdź poprzedni token
							if i - 2 >= 0:
								cheese_qty *= detect_number_if_any(tokens[i - 2])
								cheese_qty *= detect_multiplier_if_any(tokens[i - 2])
							if slots:
								slots[-1]["extras"].append(("ser", cheese_qty))
							else:
								common_attributes["extras"].append(("ser", cheese_qty))
						else:
							# fuzzy do all_ingredients
							best_ing, ing_score = fuzzy_find_ingredient(txt, self.all_ingredients)
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
		
		# Po przejściu przez wszystkie tokeny – dołącz common attributes do każdego slotu
		for s in slots:
			if common_attributes["dough"]["big_size"] is not None and s["dough"]["big_size"] is None:
				s["dough"]["big_size"] = common_attributes["dough"]["big_size"]
			if common_attributes["dough"]["on_thick_pastry"] is not None and s["dough"]["on_thick_pastry"] is None:
				s["dough"]["on_thick_pastry"] = common_attributes["dough"]["on_thick_pastry"]
			if common_attributes["dough"]["without_gluten"]:
				s["dough"]["without_gluten"] = True
			
			# scalamy sauces i extras
			s["sauces"].extend(common_attributes["sauces"])
			s["extras"].extend(common_attributes["extras"])
		
		# Gdy user wcale nie powiedział “dwie pizze” ->  moze 1 slot: quantity=2
		# (Zostawiamy tak, bo to zależy od interpretacji)
		
		# Ostatecznie ustalamy missing_info
		results = slots
		for slot in results:
			if slot["pizza"] is None:
				slot["missing_info"].append("pizza_name")
			if slot["dough"]["big_size"] is None:
				slot["missing_info"].append("size")
			if slot["dough"]["on_thick_pastry"] is None:
				slot["missing_info"].append("thickness")
		
		return results


# Funkcje pomocnicze

def _map_synonym_with_dict(word: str, synonyms_dict: dict) -> str:
	for key, synonyms in synonyms_dict.items():
		if word in synonyms:
			return key
	return word


def detect_number_if_any(token) -> int:
	"""
	Zwraca int, jeśli to liczba lub polskie słowo-liczba, w przeciwnym razie 1
	"""
	val = 1
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
	Podwójny, potrójny...
	"""
	if token.lemma_ in POLISH_MULTIPLIERS:
		return POLISH_MULTIPLIERS[token.lemma_]
	return 1


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


@router.post("/analyze-order-advanced")
def analyze_order_advanced(data: AnalyzeOrderRequest, db: Session = Depends(get_db)):
	"""
	Przykładowe użycie nowego parsera "AdvancedPizzaParser",
	który próbuje rozpoznać bardziej złożone zdania i
	uniknąć błędnych dopasowań 'margarity' => 'hawajska'.
	"""
	order = db.query(Order).filter(Order.id == data.order_id).first()
	if not order:
		return {"success": False, "message": f"Zamówienie {data.order_id} nie istnieje."}
	
	parser = AdvancedPizzaParser(db)
	parsed_items = parser.parse_order(data.transcription)
	
	if not parsed_items:
		return {"success": False, "message": "Nie wykryto żadnych elementów zamówienia."}
	
	# Zapis w bazie i budowa odpowiedzi
	responses = []
	for slot in parsed_items:
		# Szukamy obiektu Pizza
		pizza_obj = None
		if slot["pizza"]:
			pizza_obj = db.query(Pizza).filter(Pizza.name.ilike(slot["pizza"])).first()
		
		# Dobieramy ciasto
		query = db.query(Dough)
		if slot["dough"]["big_size"] is not None:
			query = query.filter(Dough.big_size == slot["dough"]["big_size"])
		if slot["dough"]["on_thick_pastry"] is not None:
			query = query.filter(Dough.on_thick_pastry == slot["dough"]["on_thick_pastry"])
		if slot["dough"]["without_gluten"]:
			query = query.filter(Dough.without_gluten == True)
		dough_obj = query.first()
		
		if pizza_obj and dough_obj:
			db.execute(
				order_pizzas.insert().values(
					order_id=order.id,
					pizza_id=pizza_obj.id,
					dough_id=dough_obj.id,
					quantity=slot["pizza_count"]
					)
				)
			db.commit()
			
			# Komunikat
			dough_desc = []
			if slot["dough"]["big_size"] is None:
				dough_desc.append("NIE PODANO ROZMIARU (domyślne)")
			else:
				dough_desc.append("duża" if slot["dough"]["big_size"] else "mała/średnia")
			
			if slot["dough"]["on_thick_pastry"] is None:
				dough_desc.append("NIE PODANO GRUBOŚCI (domyślne)")
			else:
				dough_desc.append("grube" if slot["dough"]["on_thick_pastry"] else "cienkie")
			
			if slot["dough"]["without_gluten"]:
				dough_desc.append("bezglutenowe")
			
			if slot["missing_info"]:
				missing = f"(Braki: {slot['missing_info']})"
			else:
				missing = ""
			
			resp = (f"{slot['pizza_count']}x {pizza_obj.name}, ciasto: {', '.join(dough_desc)} {missing} "
			        f"| Extras: {slot['extras']} | Sosy: {slot['sauces']}")
			responses.append(resp)
		else:
			responses.append(f"Brak pizzy={pizza_obj} lub ciasta={dough_obj} => {slot}")
	
	return {
		"success":      True,
		"parsed_items": parsed_items,
		"info":         responses
		}
