import json
import os
from datetime import date

import db
from config import BASE_DIR

DATA_FILE = os.path.join(BASE_DIR, "components_data.json")
CHAIN_ROTATION_KM = 400

# Świeżość zależy od czasu, nie od km - mleczko w oponach wysycha nawet gdy rower stoi.
# Progi to rozsądny wspólny mianownik dla różnych marek/mleczek używanych jednocześnie.
TIME_BASED_TYPES = {
    "Mleczko (uszczelniacz)": {"topup_days": 90, "replace_days": 180},
}


def _load_all():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)


def _save_all(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_bike_data(gear_id, parsed):
    all_data = _load_all()
    all_data[gear_id] = parsed
    _save_all(all_data)


def _km_in_range(conn, gear_id, start_date, end_date):
    query = "SELECT COALESCE(SUM(distance_m), 0) FROM activities WHERE gear_id = ?"
    params = [gear_id]
    if start_date:
        query += " AND start_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND start_date < ?"
        params.append(end_date)
    row = conn.execute(query, params).fetchone()
    return (row[0] or 0) / 1000


def _enrich(conn, gear_id, item):
    computed = round(_km_in_range(conn, gear_id, item.get("start_date"), item.get("end_date")), 1)
    strava_km = item["km"]
    return {
        **item,
        "km_strava": strava_km,
        "km_computed": computed,
        "diff_km": round(computed - strava_km, 1),
        "active": item["end_date"] is None,
    }


def _freshness(ctype, enriched):
    thresholds = TIME_BASED_TYPES.get(ctype)
    if not thresholds:
        return None
    current = next((it for it in enriched if it["active"]), None)
    if not current or not current.get("start_date"):
        return None
    days_since = (date.today() - date.fromisoformat(current["start_date"])).days
    return {
        "days_since": days_since,
        "topup_days": thresholds["topup_days"],
        "replace_days": thresholds["replace_days"],
        "topup_due": days_since >= thresholds["topup_days"],
        "replace_due": days_since >= thresholds["replace_days"],
        "topup_remaining_days": max(0, thresholds["topup_days"] - days_since),
        "replace_remaining_days": max(0, thresholds["replace_days"] - days_since),
    }


def _component_types(conn, gear_id, bike_data):
    result = []
    for ctype, items in bike_data.get("components", {}).items():
        enriched = [_enrich(conn, gear_id, it) for it in items]
        finished = [it["km_computed"] for it in enriched if not it["active"]]
        avg_km = round(sum(finished) / len(finished), 1) if finished else None
        result.append({
            "type": ctype,
            "items": enriched,
            "avg_lifetime_km": avg_km,
            "freshness": _freshness(ctype, enriched),
        })
    return result


def _chains(conn, gear_id, bike_data):
    result = []
    for chain_id, segments in bike_data.get("chains", {}).items():
        if not segments:
            continue
        enriched = [_enrich(conn, gear_id, s) for s in segments]
        current = next((s for s in enriched if s["active"]), None)
        result.append({
            "id": chain_id,
            "segments": enriched,
            "total_km_strava": round(sum(s["km_strava"] for s in enriched), 1),
            "total_km_computed": round(sum(s["km_computed"] for s in enriched), 1),
            "active": current is not None,
            "current_km_strava": current["km_strava"] if current else 0,
            "current_km_computed": current["km_computed"] if current else 0,
            "remaining_km": round(max(0, CHAIN_ROTATION_KM - current["km_computed"]), 1) if current else None,
            "rotation_km": CHAIN_ROTATION_KM,
        })
    result.sort(key=lambda c: c["id"])
    return result


def bike_summary(gear_id):
    bike_data = _load_all().get(gear_id, {})
    conn = db.get_conn()
    total_computed = round(_km_in_range(conn, gear_id, None, None), 1)
    summary = {
        "total_km_strava": bike_data.get("total_km") or 0,
        "total_km_computed": total_computed,
        "component_types": _component_types(conn, gear_id, bike_data),
        "chains": _chains(conn, gear_id, bike_data),
    }
    conn.close()
    return summary
