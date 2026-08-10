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


def parse_strava_components(raw_text):
    components = {}
    chains = {"1": [], "2": []}
    chain_history = []
    total_km = None

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

        pl_type = TYPE_MAP.get(type_)
        if not pl_type:
            continue

        components.setdefault(pl_type, []).append({
            "brand": brand, "model": model,
            "start_date": start_date, "end_date": end_date, "km": km,
        })

    if chain_history:
        components[CHAIN_HISTORY_TYPE] = chain_history

    for items in components.values():
        items.sort(key=_sort_key)
    for segments in chains.values():
        segments.sort(key=_sort_key)

    return {"total_km": total_km or 0, "components": components, "chains": chains}
