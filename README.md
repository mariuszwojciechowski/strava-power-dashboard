# Strava - piki mocy i prędkości

Lokalna aplikacja webowa: pobiera Twoje przejazdy rowerowe ze Stravy, liczy piki mocy
(2, 3, 5, 8, 10, 15, 20, 30, 40, 50, 60 min) i szacowane FTP dla wybranych rowerów oraz
pokazuje ich zmianę w czasie (pojedyncze przejazdy, najlepszy wynik w miesiącu, średnia
krocząca 3-miesięczna), a także prędkości maksymalne i eksploatację komponentów. Dane są
cache'owane lokalnie w SQLite, więc kolejne uruchomienia nie odpytują całej historii od nowa.

Każdy użytkownik uruchamia własną, w pełni niezależną kopię aplikacji (własny plik `.env`,
własna baza danych, własne tokeny) - nic nie jest współdzielone między instalacjami.

## 1. Instalacja

```bash
cd strava-power-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Uruchomienie i konfiguracja

```bash
./start.sh
```

Otwórz [http://localhost:5050/settings](http://localhost:5050/settings) - cała konfiguracja
odbywa się teraz w przeglądarce, bez edytowania plików ani terminala:

1. **Aplikacja Strava API** - załóż własną na
   [strava.com/settings/api](https://www.strava.com/settings/api) (pole "Authorization
   Callback Domain" ustaw na `localhost`), wklej Client ID i Client Secret.
2. **Autoryzacja** - jeden klik na "Autoryzuj przez Stravę", zaloguj się i zatwierdź dostęp.
3. **Wybór rowerów** - po autoryzacji zobaczysz listę wszystkich swoich rowerów ze Stravy;
   zaznacz dowolną ich liczbę i opcjonalnie zmień nazwę wyświetlaną w dashboardzie.

## 3. Pierwsza synchronizacja (cała historia)

W dashboardzie kliknij przycisk "Synchronizuj ze Stravą" (dla wielu lat historii może to
potrwać dłużej - limit API Stravy: 100 zapytań / 15 min, 1000 / dzień). Kolejne kliknięcia
pobierają już tylko nowe przejazdy. To samo można zrobić z terminala: `python sync.py`.

## 4. Zarządzanie aplikacją

```bash
./start.sh   # uruchomienie w tle (nohup) - działa dalej po zamknięciu terminala/Claude Code
./stop.sh    # zatrzymanie
tail -f app.log   # logi na bieżąco
```

Po ponownym uruchomieniu komputera trzeba odpalić `./start.sh` jeszcze raz ręcznie - to nie
jest usługa systemowa startująca automatycznie.

## Jak liczone są piki mocy

Dla każdego przejazdu z danymi z pomiaru mocy pobierany jest strumień czas+watt, próbkowany
do rozdzielczości 1 Hz (interpolacja liniowa), a następnie liczona jest najwyższa średnia
krocząca dla każdego z 11 okien czasowych - dokładnie ten sam sposób, w jaki liczy się
krzywą mocy (power curve) w narzędziach typu Golden Cheetah/TrainingPeaks.
