import sqlite3

from config import DB_FILE


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY,
            name TEXT,
            start_date TEXT,
            gear_id TEXT,
            type TEXT,
            trainer INTEGER,
            distance_m REAL,
            moving_time_s INTEGER,
            max_speed_kmh REAL,
            avg_watts REAL,
            has_power INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS peaks (
            activity_id INTEGER,
            duration_s INTEGER,
            power_w REAL,
            PRIMARY KEY (activity_id, duration_s)
        )
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS sync_state (key TEXT PRIMARY KEY, value TEXT)")

    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(activities)")}
    if "type" not in existing_cols:
        conn.execute("ALTER TABLE activities ADD COLUMN type TEXT")
    if "trainer" not in existing_cols:
        conn.execute("ALTER TABLE activities ADD COLUMN trainer INTEGER")
    conn.commit()

    return conn


def upsert_activity(conn, activity):
    conn.execute("""
        INSERT INTO activities
            (id, name, start_date, gear_id, type, trainer, distance_m, moving_time_s, max_speed_kmh, avg_watts, has_power)
        VALUES
            (:id, :name, :start_date, :gear_id, :type, :trainer, :distance_m, :moving_time_s, :max_speed_kmh, :avg_watts, :has_power)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, start_date=excluded.start_date, gear_id=excluded.gear_id,
            type=excluded.type, trainer=excluded.trainer,
            distance_m=excluded.distance_m, moving_time_s=excluded.moving_time_s,
            max_speed_kmh=excluded.max_speed_kmh, avg_watts=excluded.avg_watts, has_power=excluded.has_power
    """, activity)


def upsert_peaks(conn, activity_id, peaks):
    for duration_s, power_w in peaks.items():
        if power_w is None:
            continue
        conn.execute("""
            INSERT INTO peaks (activity_id, duration_s, power_w) VALUES (?, ?, ?)
            ON CONFLICT(activity_id, duration_s) DO UPDATE SET power_w=excluded.power_w
        """, (activity_id, duration_s, power_w))


def activity_exists(conn, activity_id):
    return conn.execute("SELECT 1 FROM activities WHERE id = ?", (activity_id,)).fetchone() is not None


def peaks_exist(conn, activity_id):
    return conn.execute("SELECT 1 FROM peaks WHERE activity_id = ? LIMIT 1", (activity_id,)).fetchone() is not None


def get_last_sync_epoch(conn):
    row = conn.execute("SELECT value FROM sync_state WHERE key = 'last_after'").fetchone()
    return int(row[0]) if row else None


def set_last_sync_epoch(conn, epoch):
    conn.execute("""
        INSERT INTO sync_state (key, value) VALUES ('last_after', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (str(epoch),))
