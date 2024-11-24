import spacy
from fuzzywuzzy import process
from nltk.tokenize import MWETokenizer

nlp = spacy.load("pl_core_news_md")

def analyze_order(text):
    doc = nlp(text)
    items = []
    for token in doc:
        if token.pos_ == "NOUN":  # Wyszukaj nazwy rzeczy (np. pizza, cola)
            items.append(token.text)
    return items

class AnalyzeOrder:
    def __init__(self):
        self.nlp = spacy.load("pl_core_news_md")
        self.pizza_sizes = ["mała", "średnia", "duża"]
        self.pizza_types = ["margherita", "pepperoni", "hawajska", "wegetariańska"]
        self.sauces = ["pomidorowy", "czosnkowy", "ostry", "łagodny"]

        self.size_synonyms = {
            "mała": ["mały", "małą"],
            "średnia": ["średni", "średnią"],
            "duża": ["duży", "dużą", "wielka", "wielką"]
        }

    def map_synonym(self, word, synonyms_dict):
        for key, synonyms in synonyms_dict.items():
            if word in synonyms:
                return key
        return word

    def detect_pizza_size(self, text):
        size = process.extractOne(text, self.pizza_sizes, score_cutoff=70)
        return size[0] if size else None

    def detect_pizza_type(self, text):
        pizza_type = process.extractOne(text, self.pizza_types, score_cutoff=80)
        return pizza_type[0] if pizza_type else None

    def detect_sauce(self, text):
        sauce = process.extractOne(text, self.sauces, score_cutoff=80)
        return sauce[0] if sauce else None

    def analyze_order(self, order_text):
        doc = self.nlp(order_text)
        detected_size = None
        detected_pizza_type = None
        detected_sauce = None

        for token in doc:
            if token.is_alpha and not token.is_stop:
                lemma = token.lemma_.lower()
                mapped_lemma = self.map_synonym(lemma, self.size_synonyms)
                if not detected_size:
                    detected_size = self.detect_pizza_size(mapped_lemma)
                if not detected_pizza_type:
                    detected_pizza_type = self.detect_pizza_type(token.text.lower())
                if not detected_sauce:
                    detected_sauce = self.detect_sauce(token.text.lower())

        return detected_size, detected_pizza_type, detected_sauce

    def  show_lemmatization(self, text):
        doc = self.nlp(text)
        for token in doc:
            print(token.text, token.lemma_)
        return [f"{token} -> {token.lemma_} " for token in doc]


if __name__ == "__main__":
    aoft = AnalyzeOrder()
    order_text = "Chciałbym zamówić dużą pizzę margherita z ostrą papryką"
    detected_size, detected_pizza_type, detected_sauce = aoft.analyze_order(order_text)
    print(f"Detected size: {detected_size}")
    print(f"Detected pizza type: {detected_pizza_type}")
    print(f"Detected sauce: {detected_sauce}")

