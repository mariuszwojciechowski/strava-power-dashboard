from strava_client import get_athlete


def main():
    athlete = get_athlete()
    bikes = athlete.get("bikes", [])
    if not bikes:
        print("Brak rowerów na koncie Strava (Ustawienia -> Mój sprzęt).")
        return
    print("gear_id\tnazwa")
    for bike in bikes:
        print(f"{bike['id']}\t{bike.get('nickname') or bike.get('name')}")


if __name__ == "__main__":
    main()
