# path/filename: routers/analyze_order.py
"""
Cel pliku:
Implementacja endpointu, który przyjmuje transkrypcję zamówienia,
analizuje ją za pomocą spacy + fuzzywuzzy i aktualizuje zamówienie w bazie.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models import Order, Pizza, Dough, order_pizzas
from fuzzywuzzy import process
import spacy


router = APIRouter()


class AnalyzeOrderRequest(BaseModel):
	order_id: int
	transcription: str


POLISH_NUMBERS = {
	"jeden": 1, "jedna": 1, "dwa": 2, "dwie": 2, "trzy": 3, "cztery": 4, "pięć": 5,
	"sześć": 6, "siedem": 7, "osiem": 8, "dziewięć": 9, "dziesięć": 10
	}


class AnalyzeOrder:
	"""
	Klasa do analizy tekstu zamówienia.
	Wyszukuje nazwę pizzy, rozmiar, sos itd. i pozwala mapować je przez fuzzywuzzy.
	"""
	
	def __init__(self):
		self.nlp = spacy.load("pl_core_news_md")
		# Przykładowe listy - realnie możemy odpytywać bazę:
		self.pizza_sizes = ["mała", "duża", "średnia"]
		self.sauces = ["pomidorowy", "czosnkowy", "ostry", "łagodny"]
		
		# Synonimy rozmiarów, żeby lematyzacja lepiej trafiała
		self.size_synonyms = {
			"mała":    ["mały", "malutka", "małą"],
			"średnia": ["średni", "średnią"],
			"duża":    ["duży", "dużą", "wielka", "wielką"]
			}
	
	def map_synonym(self, word: str, synonyms_dict: dict) -> str:
		for key, synonyms in synonyms_dict.items():
			if word in synonyms:
				return key
		return word
	
	def detect_pizza_size(self, text: str) -> Optional[str]:
		"""
		Przykładowy fuzzy match do ustalenia rozmiaru pizzy
		"""
		result = process.extractOne(text, self.pizza_sizes, score_cutoff=70)
		return result[0] if result else None
	
	def analyze_text(self, text: str) -> dict:
		"""
		Zwraca informacje z transkryptu:
		  - 'pizza_type' (string lub None),
		  - 'size' (string lub None),
		  - 'quantity' (int, default=1),
		  - 'sauce' (string lub None).
		"""
		doc = self.nlp(text.lower())
		
		# Domyślne wartości
		found_size = None
		found_pizza_type = None
		found_sauce = None
		found_quantity = 1
		
		for token in doc:
			# Sprawdzamy, czy któryś token to liczba lub słowo-liczba
			# (np. "trzy", "cztery" itp.)
			if token.like_num:
				try:
					found_quantity = int(token.text)
				except ValueError:
					pass
			elif token.lemma_ in POLISH_NUMBERS:
				found_quantity = POLISH_NUMBERS[token.lemma_]
			
			# Detekcja rozmiaru na bazie synonimów
			mapped_lemma = self.map_synonym(token.lemma_, self.size_synonyms)
			if not found_size:
				candidate_size = self.detect_pizza_size(mapped_lemma)
				if candidate_size:
					found_size = candidate_size
			
			# (Dalej) ewentualna detekcja sosu
			if not found_sauce:
				sauce_res = process.extractOne(token.text, self.sauces, score_cutoff=80)
				if sauce_res:
					found_sauce = sauce_res[0]
		
		# Wersja skrócona: wyszukiwanie czegokolwiek, co mogłoby przypominać nazwę pizzy
		# (Margherita, Pepperoni, itp.) wymaga obszerniejszej logiki.
		# Możemy np. zrobić prosty test / fuzzy do listy pizzy z bazy już w samym endpoint.
		# Tutaj "found_pizza_type" jest puste, a endpoint dopiero z fuzzywuzzy dobierze.
		return {
			"pizza_type": found_pizza_type,
			"size":       found_size,
			"quantity":   found_quantity,
			"sauce":      found_sauce
			}


@router.post("/analyze-order")
def analyze_order(data: AnalyzeOrderRequest, db: Session = Depends(get_db)):
	"""
	Odbiera transkrypcję od frontu,
	analizuje i aktualizuje istniejące zamówienie w tabeli order_pizzas.
	"""
	# 1) Znalezienie zamówienia
	order = db.query(Order).filter(Order.id == data.order_id).first()
	if not order:
		return {
			"success": False,
			"message": f"Zamówienie {data.order_id} nie istnieje."
			}
	
	# 2) Analiza tekstu
	analyzer = AnalyzeOrder()
	extraction = analyzer.analyze_text(data.transcription)
	
	# 3) Próba fuzzywuzzy dopasowania do pizzy w bazie
	# Pobieramy wszystkie nazwy pizzy, by dopasować
	all_pizzas = db.query(Pizza).all()
	pizza_names = [p.name.lower() for p in all_pizzas]
	
	# Zakładamy, że "pizza_type" to jakieś słowo w transkrypcji.
	# Do uproszczenia – weźmy wszystko i użyjmy max dopasowania:
	best_match_pizza = None
	best_score = 0
	
	for token in data.transcription.lower().split():
		match_res = process.extractOne(token, pizza_names, score_cutoff=60)
		if match_res and match_res[1] > best_score:
			best_score = match_res[1]
			best_match_pizza = match_res[0]
	
	# 4) Jeśli mamy pizzę
	final_pizza = None
	if best_match_pizza:
		# Znajdź obiekt Pizza z oryginalną nazwą (nie lower)
		final_pizza = next((p for p in all_pizzas if p.name.lower() == best_match_pizza), None)
	
	# 5) Dopasowanie do Dough/rozmiaru (podobna logika fuzzy)
	# Na bazie "extraction['size']" np. "duża" / "mała" itp.
	# Zakładamy, że w DB jest:
	# - big_size: True/False
	# - Atrybut "on_thick_pastry" ...
	# Przykładowo: "duża" => big_size=True, "mała"/"średnia" => big_size=False itp.
	size_map = {
		"duża":    True,
		"mała":    False,
		"średnia": False
		}
	is_big = size_map.get(extraction["size"], False)
	
	# Wybieramy najtańsze ciasto pasujące do big_size:
	final_dough = db.query(Dough).filter(Dough.big_size == is_big).order_by(Dough.price.asc()).first()
	
	# 6) Dodajemy do order_pizzas, jeśli final_pizza i final_dough istnieją
	if final_pizza and final_dough:
		db.execute(
			order_pizzas.insert().values(
				order_id=order.id,
				pizza_id=final_pizza.id,
				dough_id=final_dough.id,
				quantity=extraction["quantity"]
				)
			)
		db.commit()
		return {
			"success": True,
			"message": (
				f"Dodano do zamówienia {extraction['quantity']}x pizza '{final_pizza.name}' "
				f"(rozmiar: {'duża' if is_big else 'mała/średnia'}) "
				f"z sosem: {extraction['sauce']}"
			)
			}
	else:
		return {
			"success": False,
			"message": (
				"Nie udało się znaleźć pasującej pizzy lub ciasta w bazie. "
				f"Detekcja => pizza: {extraction['pizza_type']}, rozmiar: {extraction['size']}"
			)
			}
