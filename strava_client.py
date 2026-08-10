import json
import time

import requests

import config

API_BASE = "https://www.strava.com/api/v3"
TOKEN_URL = "https://www.strava.com/oauth/token"


def _load_tokens():
    with open(config.TOKENS_FILE) as f:
        return json.load(f)


def save_tokens(tokens):
    with open(config.TOKENS_FILE, "w") as f:
        json.dump(tokens, f)


def _refresh_access_token(refresh_token):
    resp = requests.post(TOKEN_URL, data={
        "client_id": config.get_client_id(),
        "client_secret": config.get_client_secret(),
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })
    resp.raise_for_status()
    return resp.json()


def get_access_token():
    tokens = _load_tokens()
    if tokens["expires_at"] > time.time() + 60:
        return tokens["access_token"]
    tokens = _refresh_access_token(tokens["refresh_token"])
    save_tokens(tokens)
    return tokens["access_token"]


def _request(method, path, **kwargs):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        resp = requests.request(method, f"{API_BASE}{path}", headers=headers, **kwargs)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 60))
            print(f"Limit zapytań API osiągnięty, czekam {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()


def get_athlete():
    return _request("GET", "/athlete")


def list_activities(after=None, page=1, per_page=200):
    params = {"page": page, "per_page": per_page}
    if after is not None:
        params["after"] = after
    return _request("GET", "/athlete/activities", params=params)


def get_activity_streams(activity_id, keys=("time", "watts")):
    params = {"keys": ",".join(keys), "key_by_type": "true"}
    return _request("GET", f"/activities/{activity_id}/streams", params=params)
