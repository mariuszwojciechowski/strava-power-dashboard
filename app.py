import os
from urllib.parse import urlencode

import requests as http_requests
from flask import Flask, jsonify, redirect, render_template, request

import components as components_module
import components_parser
import config
import db
import lab_tests as lab_tests_module
import strava_client
import sync as sync_module

app = Flask(__name__)

STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
OAUTH_SCOPE = "activity:read_all,profile:read_all"


def _load_peaks_df():
    import pandas as pd
    conn = db.get_conn()
    df = pd.read_sql_query("""
        SELECT p.activity_id, p.duration_s, p.power_w, a.start_date, a.gear_id, a.name
        FROM peaks p JOIN activities a ON a.id = p.activity_id
    """, conn)
    conn.close()
    if not df.empty:
        df["start_date"] = pd.to_datetime(df["start_date"])
    return df


def _load_activities_df():
    import pandas as pd
    conn = db.get_conn()
    df = pd.read_sql_query("SELECT * FROM activities", conn)
    conn.close()
    if not df.empty:
        df["start_date"] = pd.to_datetime(df["start_date"])
    return df


def _series_response(df, value_col):
    if df.empty:
        return {"raw": [], "monthly_best": [], "rolling_avg": []}

    df = df.sort_values("start_date")
    raw = [
        {"date": d.strftime("%Y-%m-%d"), "value": v, "name": n}
        for d, v, n in zip(df["start_date"], df[value_col], df["name"])
    ]

    monthly = df.set_index("start_date")[value_col].resample("MS").max().dropna()
    rolling = monthly.rolling(3, min_periods=1).mean()

    mid_month = lambda d: d.replace(day=15).strftime("%Y-%m-%d")
    monthly_best = [{"date": mid_month(d), "value": v} for d, v in monthly.items()]
    rolling_avg = [{"date": mid_month(d), "value": v} for d, v in rolling.items()]

    return {"raw": raw, "monthly_best": monthly_best, "rolling_avg": rolling_avg}


@app.route("/")
def index():
    return render_template("index.html", bikes=config.get_bikes(), durations=config.PEAK_DURATIONS_MIN)


@app.route("/api/sync", methods=["POST"])
def api_sync():
    sync_module.sync()
    return jsonify({"status": "ok"})


@app.route("/api/power")
def api_power():
    bike = request.args.get("bike", "all")
    duration = int(request.args.get("duration"))

    df = _load_peaks_df()
    if not df.empty:
        df = df[df["duration_s"] == duration]
        if bike != "all":
            df = df[df["gear_id"] == bike]

    return jsonify(_series_response(df, "power_w"))


@app.route("/api/speed")
def api_speed():
    bike = request.args.get("bike", "all")

    df = _load_activities_df()
    if not df.empty:
        df = df[(df["max_speed_kmh"] > 0) & (df["type"] != "VirtualRide") & (df["trainer"] != 1)]
        if bike != "all":
            df = df[df["gear_id"] == bike]

    return jsonify(_series_response(df, "max_speed_kmh"))


FTP_SHORT_S = 180
FTP_LONG_S = 1200


def _ftp_dataframe(method, bike):
    df = _load_peaks_df()
    if df.empty:
        return df
    if bike != "all":
        df = df[df["gear_id"] == bike]

    if method == "sixty_min":
        sub = df[df["duration_s"] == 3600].copy()
        sub["value"] = sub["power_w"]
    elif method == "twenty_min_095":
        sub = df[df["duration_s"] == 1200].copy()
        sub["value"] = sub["power_w"] * 0.95
    else:
        pivot = df[df["duration_s"].isin([FTP_SHORT_S, FTP_LONG_S])].pivot_table(
            index=["activity_id", "start_date", "gear_id", "name"],
            columns="duration_s", values="power_w",
        ).reset_index()
        pivot = pivot.dropna(subset=[FTP_SHORT_S, FTP_LONG_S])
        pivot["value"] = (
            (pivot[FTP_SHORT_S] * FTP_SHORT_S - pivot[FTP_LONG_S] * FTP_LONG_S)
            / (FTP_SHORT_S - FTP_LONG_S)
        )
        sub = pivot

    return sub[["start_date", "gear_id", "name", "value"]]


@app.route("/api/ftp")
def api_ftp():
    bike = request.args.get("bike", "all")
    method = request.args.get("method", "critical_power")
    df = _ftp_dataframe(method, bike)
    return jsonify(_series_response(df, "value"))


@app.route("/api/gear-summary")
def api_gear_summary():
    return jsonify({gear_id: components_module.bike_summary(gear_id) for gear_id in config.get_bikes()})


@app.route("/api/lab-tests")
def api_lab_tests():
    return jsonify(lab_tests_module.get_tests())


def _oauth_redirect_uri():
    return request.url_root.rstrip("/") + "/oauth/callback"


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        action = request.form.get("action")
        message = ""

        if action == "save_credentials":
            config.set_env_values({
                "STRAVA_CLIENT_ID": request.form.get("client_id", "").strip(),
                "STRAVA_CLIENT_SECRET": request.form.get("client_secret", "").strip(),
            })
            message = "Zapisano Client ID i Client Secret."

        elif action == "save_bikes":
            selected = request.form.getlist("bike_selected")
            bikes = {}
            for gear_id in selected:
                name = request.form.get(f"name_{gear_id}", "").strip() or gear_id
                bikes[gear_id] = name
            config.set_bikes(bikes)
            message = f"Zapisano {len(bikes)} rower(y)." if bikes else "Nie wybrano żadnego roweru."

        elif action == "add_bike_manual":
            gear_id = request.form.get("gear_id", "").strip()
            if gear_id:
                bikes = config.get_bikes()
                bikes[gear_id] = request.form.get("bike_name", "").strip() or gear_id
                config.set_bikes(bikes)
                message = "Dodano rower."

        elif action == "remove_bike":
            bikes = config.get_bikes()
            bikes.pop(request.form.get("gear_id", ""), None)
            config.set_bikes(bikes)
            message = "Usunięto rower."

        elif action == "parse_components":
            gear_id = request.form.get("components_bike", "").strip()
            raw_text = request.form.get("components_raw", "")
            if not gear_id:
                message = "Wybierz rower, którego dotyczą wklejone dane."
            elif not raw_text.strip():
                message = "Wklej najpierw dane z zakładki Sprzęt w Strava."
            else:
                parsed = components_parser.parse_strava_components(raw_text)
                components_module.save_bike_data(gear_id, parsed)
                n_types = len(parsed["components"])
                n_chains = sum(1 for segs in parsed["chains"].values() if segs)
                message = f"Zapisano dane eksploatacji: {n_types} typów komponentów, {n_chains} śledzonych łańcuchów."

        return redirect(f"/settings?{urlencode({'msg': message})}")

    has_credentials = bool(config.get_client_id() and config.get_client_secret())
    has_tokens = os.path.exists(config.TOKENS_FILE)

    athlete = None
    available_bikes = []
    auth_error = None
    if has_tokens:
        try:
            athlete = strava_client.get_athlete()
            available_bikes = athlete.get("bikes", [])
        except Exception as exc:
            auth_error = str(exc)

    return render_template(
        "settings.html",
        client_id=config.get_client_id(),
        has_credentials=has_credentials,
        has_tokens=has_tokens,
        athlete=athlete,
        auth_error=auth_error,
        available_bikes=available_bikes,
        bikes=config.get_bikes(),
        redirect_uri=_oauth_redirect_uri(),
        message=request.args.get("msg"),
    )


@app.route("/oauth/authorize")
def oauth_authorize():
    params = {
        "client_id": config.get_client_id(),
        "redirect_uri": _oauth_redirect_uri(),
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": OAUTH_SCOPE,
    }
    return redirect(f"{STRAVA_AUTHORIZE_URL}?{urlencode(params)}")


@app.route("/oauth/callback")
def oauth_callback():
    error = request.args.get("error")
    code = request.args.get("code")
    if error or not code:
        return redirect(f"/settings?error={error or 'brak kodu autoryzacji'}")

    resp = http_requests.post(STRAVA_TOKEN_URL, data={
        "client_id": config.get_client_id(),
        "client_secret": config.get_client_secret(),
        "code": code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    strava_client.save_tokens(resp.json())
    return redirect("/settings")


if __name__ == "__main__":
    app.run(port=5050)
