-- Wypełnienie tabeli ingredients
INSERT INTO ingredients (name, category, price) VALUES
('Pomidor', 'vegetable', 1.5),
('Mozzarella', 'dairy', 2),
('Bazylia', 'vegetable', 1),
('Salami', 'meat', 2.5),
('Pieczarki', 'vegetable', 1.5),
('Parmezan', 'dairy', 2),
('Kurczak', 'meat', 3),
('Szynka', 'meat', 2.5),
('Ananas', 'fruit', 2),
('Oliwki', 'vegetable', 1.5),
('Papryka', 'vegetable', 1.5),
('Kukurydza', 'vegetable', 1.5),
('Cebula', 'vegetable', 1.5),
('Kapary', 'vegetable', 1.5),
('Krewetki', 'seafood', 4),
('Łosoś', 'seafood', 3.5),
('Sardynki', 'seafood', 3),
('Owoce morza', 'seafood', 4.5),
('Tuńczyk', 'seafood', 3);

-- Wypełnienie tabeli doughs
INSERT INTO doughs (big_size, on_thick_pastry, without_gluten, price) VALUES
(false, false, false, 7.0),
(false, true, false, 9.0),
(true, false, false, 11.0),
(true, true, false, 13.0),
(false, false, true, 10.0),
(true, false, true, 14.0);

-- Wypełnienie tabeli pizzas
INSERT INTO pizzas (name, in_menu) VALUES
('Margherita', true),
('Pepperoni', true),
('Wegetariańska', true),
('Hawajska', false),
('Capriciosa', false);

-- Wypełnienie tabeli streets
INSERT INTO streets (name) VALUES
('Rynek'),
('ul. Piłsudskiego'),
('ul. Świdnicka'),
('ul. Legnicka'),
('ul. Powstańców Śląskich'),
('ul. Grabiszyńska'),
('ul. Wysoka'),
('ul. Karkonoska'),
('ul. Hallera'),
('ul. Nowowiejska'),
('ul. Sienkiewicza'),
('ul. Kościuszki'),
('ul. Krakowska'),
('ul. Traugutta'),
('ul. Borowska'),
('ul. Kamienna'),
('ul. Długa'),
('ul. Oławska'),
('ul. Zwycięska'),
('ul. Krzywoustego'),
('ul. Strzegomska'),
('ul. Pułaskiego'),
('ul. Mickiewicza'),
('ul. Plac Grunwaldzki'),
('ul. Jana Pawła II'),
('ul. Celtycka');


-- Wypełnienie tabeli pizza_ingredients
INSERT INTO pizza_ingredients (pizza_id, ingredient_id) VALUES
(1, 1), -- Margherita: Pomidor
(1, 2), -- Margherita: Mozzarella
(1, 3), -- Margherita: Bazylia
(2, 1), -- Pepperoni: Pomidor
(2, 2), -- Pepperoni: Mozzarella
(2, 4), -- Pepperoni: Pepperoni
(3, 1), -- Wegetariańska: Pomidor
(3, 2), -- Wegetariańska: Mozzarella
(3, 3), -- Wegetariańska: Bazylia
(3, 5), -- Wegetariańska: Pieczarka
(4, 1), -- Hawajska: Pomidor
(4, 2), -- Hawajska: Mozzarella
(4, 3), -- Hawajska: Bazylia
(4, 9), -- Hawajska: Ananas
(4, 10), -- Hawajska: Oliwki
(5, 1), -- Capriciosa: Pomidor
(5, 2), -- Capriciosa: Mozzarella
(5, 3), -- Capriciosa: Bazylia
(5, 5), -- Capriciosa: Pieczarka
(5, 8), -- Capriciosa: Szynka
(5, 10); -- Capriciosa: Oliwki


-- Wypełnienie tabeli pizza_doughs
INSERT INTO pizza_doughs (pizza_id, dough_id) VALUES
(1, 1), -- Margherita: small, thin, with gluten
(1, 2), -- Margherita: big, thin, with gluten
(2, 1), -- Pepperoni: small, thin, with gluten
(2, 3), -- Pepperoni: small, thick, with gluten
(3, 4); -- Vegetarian: big, thick, gluten-free

-- Wypełnienie tabeli clients
INSERT INTO clients (phone, address) VALUES
('123-456-789', 'ul. Pleśniowa 123'),
('987-654-321', 'ul. Pomidorowa 321');

-- Wypełnienie tabeli orders
INSERT INTO orders (order_start_time, total_price, client_id) VALUES
('2024-12-08 18:00:00', 12.5, 1),
('2024-12-08 19:00:00', 15.0, 2);

INSERT INTO order_pizzas (order_id, pizza_id, dough_id, quantity) VALUES
(1, 1, 2, 1), -- Order 1: Margherita
(1, 3, 4, 1), -- Order 1: Vegetarian
(2, 2, 1, 2);-- Order 2: Pepperoni