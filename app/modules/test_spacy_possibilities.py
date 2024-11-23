import spacy

# Load the spaCy model
nlp = spacy.load("pl_core_news_md")

# Example text
text = ("Firma apple ma siedzibę w Cupertino w Kalifornii. Steve Jobs był współzałożycielem firmy."
        "Jabłka są pyszne, ale wolę pomarańcze.")

# Process the text
doc = nlp(text)

# Tokenization
print("Tokens:")
for token in doc:
    print(token.text)

# Part-of-Speech Tagging
print("\nPOS Tags:")
for token in doc:
    print(f"{token.text}: {token.pos_}")

# Named Entity Recognition
print("\nNamed Entities:")
for ent in doc.ents:
    print(f"{ent.text}: {ent.label_}")

# Dependency Parsing
print("\nDependencies:")
for token in doc:
    print(f"{token.text}: {token.dep_} -> {token.head.text}")

# Vector Representation
print("\nVector Representation:")
for token in doc:
    print(f"{token.text}: {token.vector[:5]}...")  # Print first 5 dimensions of the vector

# Similarity
doc1 = nlp("I like apples")
doc2 = nlp("I enjoy oranges")
similarity = doc1.similarity(doc2)
print(f"\nSimilarity between 'I like apples' and 'I enjoy oranges': {similarity}")