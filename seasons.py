from datetime import date

# Sezon treningowy (zima): listopad - koniec marca. Sezon użytkowy (lato): kwiecień - koniec
# października. Nazwa sezonu to rok, w którym się kończy (np. "Zima 2024" = lis 2023 - mar 2024).


def season_periods(min_date, max_date):
    periods = []
    y = min_date.year - 1
    while True:
        winter_start = date(y, 11, 1)
        winter_end = date(y + 1, 3, 31)
        summer_start = date(y + 1, 4, 1)
        summer_end = date(y + 1, 10, 31)
        periods.append({"label": f"Zima {y + 1}", "start": winter_start.isoformat(), "end": winter_end.isoformat()})
        periods.append({"label": f"Lato {y + 1}", "start": summer_start.isoformat(), "end": summer_end.isoformat()})
        y += 1
        if summer_start > max_date:
            break
    return periods


def current_period(periods, today):
    today_s = today.isoformat()
    for p in periods:
        if p["start"] <= today_s <= p["end"]:
            return p
    return periods[-1] if periods else None
