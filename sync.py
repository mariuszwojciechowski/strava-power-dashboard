import time
from datetime import datetime

import config
import db
import strava_client as sc
from power_curve import peak_powers

RIDE_TYPES = {"Ride", "VirtualRide", "GravelRide", "MountainBikeRide", "EBikeRide"}


def _to_epoch(iso_date):
    return int(datetime.fromisoformat(iso_date.replace("Z", "+00:00")).timestamp())


def sync():
    bikes = config.get_bikes()
    if not bikes:
        raise SystemExit("Brak skonfigurowanych rowerów - ustaw je w zakładce Ustawienia albo w .env")

    conn = db.get_conn()
    after = db.get_last_sync_epoch(conn)
    newest_epoch = after or 0
    total_new = 0
    page = 1

    while True:
        activities = sc.list_activities(after=after, page=page, per_page=200)
        if not activities:
            break

        for act in activities:
            gear_id = act.get("gear_id")
            if act.get("type") not in RIDE_TYPES or gear_id not in bikes:
                continue

            is_new = not db.activity_exists(conn, act["id"])
            newest_epoch = max(newest_epoch, _to_epoch(act["start_date"]))
            has_power = bool(act.get("device_watts"))

            db.upsert_activity(conn, {
                "id": act["id"],
                "name": act["name"],
                "start_date": act["start_date"],
                "gear_id": gear_id,
                "type": act.get("type"),
                "trainer": int(bool(act.get("trainer"))),
                "distance_m": act.get("distance"),
                "moving_time_s": act.get("moving_time"),
                "max_speed_kmh": (act.get("max_speed") or 0) * 3.6,
                "avg_watts": act.get("average_watts"),
                "has_power": int(has_power),
            })
            conn.commit()

            if has_power and not db.peaks_exist(conn, act["id"]):
                streams = sc.get_activity_streams(act["id"], keys=("time", "watts"))
                if "time" in streams and "watts" in streams:
                    peaks = peak_powers(streams["time"]["data"], streams["watts"]["data"], config.PEAK_DURATIONS_S)
                    db.upsert_peaks(conn, act["id"], peaks)
                    conn.commit()
                time.sleep(1.2)

            if is_new:
                total_new += 1
                print(f"Zsynchronizowano: {act['start_date']}  {bikes[gear_id]}  {act['name']}")

        page += 1

    if newest_epoch:
        db.set_last_sync_epoch(conn, newest_epoch)
    conn.commit()
    conn.close()
    print(f"Gotowe. Nowych przejazdów: {total_new}")


if __name__ == "__main__":
    sync()
