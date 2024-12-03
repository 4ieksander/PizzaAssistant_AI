from utils.analyze_order import analyze_order

example_orders_by_chat_gpt = [
	"Dzień dobry, poproszę jedną dużą Margheritę i średnią Pepperoni. Do tego jeszcze dwie butelki coli, jeśli można.",
	"Cześć, chciałbym zamówić pizzę Capriciosa na cienkim cieście, dużą. Proszę jeszcze o sos czosnkowy i dodatkowy ser.",
	"Poproszę małą Hawajską i średnią Veggie Supreme. Sosy: jeden pomidorowy i jeden barbecue. Adres podam za chwilę.",
	"Dzień dobry, zamawiam dużą pizzę cztery sery z dodatkowym salami. Do tego mała cola i sos czosnkowy.",
	"Poproszę jedną dużą pizzę wiejską i średnią z owocami morza. Na wiejską proszę dodatkowy boczek, a do obu po sosie czosnkowym.",
	"Dzień dobry, poproszę dużą pizzę Pepperoni z podwójnym serem i dodatkowym sosem czosnkowym. Do tego średnią colę.",
	"Cześć, chciałbym zamówić dwie średnie pizze: jedną Capriciosa, drugą Hawajską. Obie na grubym cieście, proszę.",
	"Poproszę jedną dużą pizzę wegetariańską z dodatkowym serem i jalapeños. Do tego sos pomidorowy i czosnkowy.",
	"Dzień dobry, zamawiam jedną średnią pizzę Pepperoni i jedną dużą cztery sery. Do tego dwa sosy czosnkowe i jedną colę zero.",
	"Cześć, chciałbym zamówić małą pizzę Margherita, a do tego dużą pizzę z szynką, pieczarkami i kukurydzą. Obie na cienkim cieście.",
	"Poproszę dużą pizzę z boczkiem, cebulą i pieczarkami, dodatkowo podwójny ser. Do tego sos czosnkowy i butelkę Pepsi.",
	"Dzień dobry, zamawiam dwie duże pizze: jedną cztery sery, drugą Pepperoni. Proszę także o trzy sosy: dwa czosnkowe i jeden pomidorowy.",
	"Poproszę jedną dużą pizzę z szynką i pieczarkami na grubym cieście. Do tego dwa sosy pomidorowe i jedną Fantę.",
	"Cześć, chciałbym zamówić średnią pizzę Hawajską i dużą pizzę wiejską z dodatkowym boczkiem. Proszę o dostawę na mój adres.",
	"Dzień dobry, poproszę dużą pizzę Pepperoni z podwójnym serem, średnią wegetariańską i butelkę wody gazowanej.",
	"Dzień dobry, chciałbym zamówić dużą pizzę Pepperoni z podwójnym serem i grubym ciastem. Do tego poproszę dwie średnie pizze: jedną Hawajską, drugą cztery sery, obie na cienkim cieście. Do zamówienia chciałbym jeszcze trzy sosy: dwa czosnkowe i jeden pomidorowy. I jeśli macie, to poproszę butelkę coli i Fanty. Adres podam za chwilę.",
	"Cześć, chciałbym zamówić dużą pizzę wiejską z dodatkowym boczkiem i cebulą. Proszę, aby była na cienkim cieście. Do tego jeszcze średnia pizza wegetariańska, ale zamiast papryki poproszę dodatkowe pieczarki. Chciałbym też zamówić trzy sosy: czosnkowy, pomidorowy i barbecue. Na koniec poproszę jedną butelkę Pepsi i jedną Sprite. Dostawa na mój adres domowy.",
	"Dzień dobry, zamawiam dwie pizze: jedną dużą Pepperoni z podwójnym serem i jalapeños, drugą dużą cztery sery z dodatkową szynką. Do tego jeszcze średnią pizzę z szynką, pieczarkami i kukurydzą, ale proszę, żeby ciasto było standardowe. Chciałbym do tego zestaw pięciu sosów – dwa czosnkowe, dwa pomidorowe i jeden barbecue. Jeśli można, to poproszę jeszcze jedną butelkę coli zero i jedną Fantę. Adres podam, gdy będzie gotowe.",
	"Poproszę jedną dużą pizzę Pepperoni z dodatkowym serem, szynką i cebulą, wszystko na grubym cieście. Do tego jeszcze średnią pizzę Margheritę z jalapeños. Chciałbym też zamówić dwie małe pizze: jedną Hawajską i drugą cztery sery, obie na cienkim cieście. Do całego zamówienia poproszę cztery sosy czosnkowe i dwie butelki coli. Płatność będzie kartą.",
	"Dzień dobry, zamawiam dużą pizzę wegetariańską na grubym cieście z dodatkowym serem i jalapeños. Do tego jeszcze średnia Pepperoni z boczkiem i podwójnym serem. Chciałbym też jedną dużą pizzę cztery sery z sosem barbecue jako bazą. Do zamówienia proszę dodać pięć sosów: dwa czosnkowe, dwa pomidorowe i jeden barbecue. Na koniec butelka coli i Fanty. Proszę, żeby dostawa była na godzinę 18:00.",
	"Cześć, chciałbym zamówić trzy pizze: dużą Pepperoni z dodatkowym boczkiem, średnią cztery sery z jalapeños i małą wegetariańską z podwójnym serem. Proszę wszystkie na cienkim cieście. Do tego trzy sosy czosnkowe, dwa barbecue i jedną Fantę. Płatność będzie gotówką, a dostawa na adres podany wcześniej.",
	"Poproszę jedną dużą pizzę Pepperoni z podwójnym serem i sosem barbecue jako bazą. Do tego jeszcze średnia pizza z owocami morza, ale proszę bez cebuli. Chciałbym także zamówić dwie małe pizze: jedną Hawajską i jedną cztery sery z dodatkowym boczkiem. Do tego zestaw czterech sosów: dwa czosnkowe i dwa pomidorowe. Proszę też o jedną colę zero i jedną wodę gazowaną. Czy dostawa jest możliwa do godziny 19:00?",
	"Dzień dobry, chciałbym zamówić dwie duże pizze: jedną Pepperoni z dodatkowym serem i jalapeños, drugą cztery sery z boczkiem. Do tego średnią wegetariańską z podwójnym serem i sosem pomidorowym. Proszę też o cztery sosy czosnkowe i jedną butelkę Pepsi. Płatność będzie kartą przy odbiorze. Adres dostawy ten sam co zawsze.",
	"Cześć, zamawiam dużą pizzę cztery sery z dodatkowym boczkiem, średnią Pepperoni z jalapeños i małą wegetariańską na grubym cieście. Do tego proszę dodać trzy sosy czosnkowe i dwie butelki wody gazowanej. Chciałbym jeszcze dowiedzieć się, czy możecie dostarczyć zamówienie do godziny 20:00. Płatność będzie gotówką.",
	"Poproszę dwie duże pizze: jedną Pepperoni z podwójnym serem i sosem barbecue, drugą Hawajską na cienkim cieście. Do tego jeszcze jedną średnią pizzę cztery sery z dodatkowym jalapeños. Chciałbym także zamówić zestaw pięciu sosów: dwa czosnkowe, dwa pomidorowe i jeden barbecue. Jeśli można, proszę o dwie butelki coli i jedną Sprite. Adres dostawy podam zaraz."
                              ]

for order in example_orders_by_chat_gpt:
	print(analyze_order(order))


