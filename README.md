# Small projects
Małe projekty realizowane w krótkim czasie. POmogły zaznajomić się z budowaniem gotowych aplikacji dla użytkowników zewnętrzynch

### Best Picker
Prosta aplikacja pozwalająca na wybranie najlepszego kandydata z opcji. Zrealizowana w 2h dla znajomego
Program przyjmuje dane w formacie obrazów, a następnie odpowiednio wyświetla je w formacie drabinki lub King of the Hill (wygrany zostaje)
Użytkownik widzi serię "pojedynków" 1vs1 w którym wybiera zwycięzcę według preferencji.
Finalnie pokazany jest zwycięzka, a następnie statystyku odnośnie ilości wygranych wszystkich opcji.

### Mood borad
Program realizujący pomysł na ekscentryczną ocenę przez użytkownika. Zrealizowany w 3h, głównie przez tworzenie buziek
Zamiast wybierać oceny 1-5 użytkownik przenosi buźkę w miejsce, które najbardziej oddaje jego odczucie.

### Orbiting Chat
Program wyświetlający wiadomości z chatu Twicha jako orbitujące wookół obiektu dający efekt 3D.
#### Problem
Program posiada jedno okienko, które może być wyścietlane na warstwie niżej lub wyżej niż okno docelowe
#### Rozwiązanie
Rozdzielenie wyświetlania na 2 procesy. Jeden "za" oknem docelowych, drugi "przed"
Bot przymjujacy wiadomości wrzucaj je do kolejek tych procesów.

W celu ograniczenia pamięci podręcznej dla 2 procesów wyświetlania, emotki pobierane są do cashe, następnie odczytowane po indexach.

Aby uniknąć potrzeby komunikacji procesów między sobą, wiadomości przychodzące mają znaczniki czasowe ich pozycja oraz TTL jest wyznaczana na jego podstawie, eliminując problemy z opóźnieniem.

Dokładnieszy opis przetwarzania wiadomości w projekcie poprzedzającym PopUp Chat.

#### Dodatkowe funckcjonalności
Skalowanie rozmiaru wiadmości
Implementacja opóźnienia w wyświetlaniu nowych wiadomości, aby uniknąć zasłaniania dla dużej ilości w krótkim czasie

### PopUp Chat
Program wyświetlający wiadomości z chatu Twicha jako powiadomienia typu PopUp.
Służył do nauki pracy z API Twicha o obsługi bota.

#### Problem
1.Potrzeba formatowania wiadomości do formatu wyświetlanie.

2.Obsługa Emotek z Twicha oraz z popularnego rozszerzenia 7tv.

a) Emotki Twicha są przekazywanie nie jako obrazy lecz jako pozycje w wiadomości oraz Id emotki np "superEmotka2 {23-29}". Obraz lub GIF trzeba pobrać zapytaniem do API Twicha
b) Emotki 7tv są wykrywanie jednynie na podstawie odpowiedniej frazy i podmiany jej na emotkę. Frazy są unikalne w zależności od kanału stąd potrzeba pobrania ich i utworzenia słownika

#### Opis
Program pracuje na 2 wątkach: Twich Bot odbierający wiadomości i wątek wyświetlający wiadomości.

Bot wrzuca wiadomości do kolejki, z której zdejmuje je wątek.

### Timer
Prosta aplikacja wyświetlająca odliczanie czasu. Zrealizowana w 4h dla znajomego. 

Ważne było, aby licznik nie zasłaniał innych okienek, więc systemowy się nie nadawał.
Zakłada 2 tryby:
a) Odlicznie - odlicza czas podanych przez użytkownika np. 5min
b) Zegar - odlicza czas do ustawionej godziny
