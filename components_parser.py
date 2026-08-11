import re
from datetime import datetime

TYPE_MAP = {
    "Front Tire": "Opona przednia",
    "Rear Tire": "Opona tylna",
    "Front Brake Pads": "Klocki przód",
    "Rear Brake Pads": "Klocki tył",
    "Front Brake Rotor": "Tarcza przednia",
    "Rear Brake Rotor": "Tarcza tylna",
    "Cassette": "Kaseta",
}

CHAIN_HISTORY_TYPE = "Łańcuch (pełne życie, sprzed rotacji)"
SEALANT_TYPE = "Mleczko (uszczelniacz)"

# Rowery, które używają nieużywanego u nich slotu komponentu do śledzenia czegoś innego
# (np. gravel bez przedniej przerzutki -> ten slot służy do logowania dolewek mleczka).
BIKE_TYPE_OVERRIDES = {
    "b17153935": {"Front Derailleur": SEALANT_TYPE},
}

# Ręczne korekty tam, gdzie automatyczna reguła (cyfra 1/2 w polu brand) nie wystarcza -
# np. łańcuch założony zanim zaczęto numerować rotację, a który fizycznie jest tym samym
# łańcuchem co późniejszy "slot 1".
CHAIN_HISTORY_FIXUPS = {
    "b17153935": [
        {"model_contains": "CN-M8100", "end_before": "2026-04-16", "target_slot": "1"},
    ],
}


def _parse_date(raw):
    raw = raw.strip()
    if not raw or raw == "Since Beginning":
        return None
    return datetime.strptime(raw, "%b %d, %Y").strftime("%Y-%m-%d")


def _parse_km(raw):
    raw = raw.strip().replace(",", "")
    raw = re.sub(r"\s*km\s*$", "", raw, flags=re.IGNORECASE).strip()
    return float(raw) if raw else 0.0


def _chain_slot(brand):
    match = re.search(r"\b([12])\b", brand)
    return match.group(1) if match else None


def _split_row(line):
    parts = line.split("\t")
    if len(parts) >= 6:
        return parts
    return re.split(r" {2,}", line.strip())


def _sort_key(item):
    return item["start_date"] or "0000-00-00"


def _apply_chain_history_fixups(gear_id, chain_history, chains):
    remaining = []
    for entry in chain_history:
        moved = False
        for rule in CHAIN_HISTORY_FIXUPS.get(gear_id, []):
            if rule["model_contains"] not in entry["model"]:
                continue
            if not entry["end_date"] or entry["end_date"] >= rule["end_before"]:
                continue
            chains.setdefault(rule["target_slot"], []).append({
                "start_date": entry["start_date"], "end_date": entry["end_date"], "km": entry["km"],
            })
            moved = True
            break
        if not moved:
            remaining.append(entry)
    return remaining


def parse_strava_components(raw_text, gear_id=None):
    components = {}
    chains = {"1": [], "2": []}
    chain_history = []
    total_km = None
    type_overrides = BIKE_TYPE_OVERRIDES.get(gear_id, {})

    for line in raw_text.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue

        parts = _split_row(line)
        if len(parts) < 6:
            continue

        type_, brand, model, added, removed, distance = (p.strip() for p in parts[:6])
        if type_ in ("Type", "Components", ""):
            continue

        try:
            start_date = _parse_date(added)
            end_date = _parse_date(removed)
            km = _parse_km(distance)
        except ValueError:
            continue

        if type_ == "Frame":
            if total_km is None or km > total_km:
                total_km = km
            continue

        if type_ == "Chain":
            slot = _chain_slot(brand)
            entry = {"start_date": start_date, "end_date": end_date, "km": km}
            if slot:
                chains[slot].append(entry)
            else:
                chain_history.append({
                    "brand": brand, "model": model,
                    "start_date": start_date, "end_date": end_date, "km": km,
                })
            continue

        pl_type = type_overrides.get(type_) or TYPE_MAP.get(type_)
        if not pl_type:
            continue

        components.setdefault(pl_type, []).append({
            "brand": brand, "model": model,
            "start_date": start_date, "end_date": end_date, "km": km,
        })

    chain_history = _apply_chain_history_fixups(gear_id, chain_history, chains)
    if chain_history:
        components[CHAIN_HISTORY_TYPE] = chain_history

    for items in components.values():
        items.sort(key=_sort_key)
    for segments in chains.values():
        segments.sort(key=_sort_key)

    return {"total_km": total_km or 0, "components": components, "chains": chains}
