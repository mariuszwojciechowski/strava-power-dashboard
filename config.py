import json
import os

from dotenv import dotenv_values

BASE_DIR = os.path.dirname(__file__)
ENV_FILE = os.path.join(BASE_DIR, ".env")
TOKENS_FILE = os.path.join(BASE_DIR, "tokens.json")
DB_FILE = os.path.join(BASE_DIR, "strava_data.db")

PEAK_DURATIONS_MIN = [2, 3, 5, 8, 10, 15, 20, 30, 40, 50, 60]
PEAK_DURATIONS_S = [m * 60 for m in PEAK_DURATIONS_MIN]

# Ustawienia (Client ID/Secret, rowery) czytane na żywo z .env przy każdym wywołaniu,
# żeby zmiany w zakładce Ustawienia działały bez restartu aplikacji.


def _env():
    return dotenv_values(ENV_FILE) if os.path.exists(ENV_FILE) else {}


def get_client_id():
    return _env().get("STRAVA_CLIENT_ID", "") or ""


def get_client_secret():
    return _env().get("STRAVA_CLIENT_SECRET", "") or ""


def get_bikes():
    env = _env()

    raw = env.get("BIKES_JSON")
    if raw:
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            pass

    # Format sprzed obsługi dowolnej liczby rowerów (dwa stałe sloty w .env).
    bikes = {}
    for i in (1, 2):
        gear_id = env.get(f"BIKE_{i}_GEAR_ID")
        if gear_id:
            bikes[gear_id] = env.get(f"BIKE_{i}_NAME") or f"Rower {i}"
    return bikes


def set_bikes(bikes):
    set_env_values({"BIKES_JSON": json.dumps(bikes)})


def set_env_values(values):
    existing = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                existing[k] = v
    existing.update(values)
    with open(ENV_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
