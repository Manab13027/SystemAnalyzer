import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "targets.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS hits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pixel_id    TEXT NOT NULL,
                ts          TEXT NOT NULL,
                ip          TEXT,
                user_agent  TEXT,
                referrer    TEXT,
                accept_lang TEXT,
                headers_raw TEXT
            );

            CREATE TABLE IF NOT EXISTS fingerprints (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                pixel_id        TEXT NOT NULL,
                ts              TEXT NOT NULL,
                ip              TEXT,
                -- parsed OS
                os_family       TEXT,
                os_version      TEXT,
                os_raw          TEXT,
                -- parsed browser
                browser_family  TEXT,
                browser_version TEXT,
                -- device
                device_type     TEXT,
                device_brand    TEXT,
                device_model    TEXT,
                -- JS-gathered extras
                screen_res      TEXT,
                color_depth     INTEGER,
                timezone        TEXT,
                language        TEXT,
                platform        TEXT,
                cpu_cores       INTEGER,
                memory_gb       REAL,
                touch           INTEGER,
                plugins         TEXT,
                webgl_vendor    TEXT,
                webgl_renderer  TEXT,
                canvas_hash     TEXT,
                audio_hash      TEXT,
                fonts           TEXT,
                connection_type TEXT,
                -- detected installed applications (URI scheme probing + MIME types)
                detected_apps   TEXT,
                mime_types      TEXT,
                -- WebRTC-leaked local network info
                hostname        TEXT,
                local_ips       TEXT,
                -- raw user agent
                user_agent      TEXT,
                -- full js payload JSON
                js_payload      TEXT
            );

            CREATE TABLE IF NOT EXISTS cve_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                pixel_id        TEXT NOT NULL,
                ts              TEXT NOT NULL,
                component       TEXT NOT NULL,
                version         TEXT,
                cve_id          TEXT NOT NULL,
                cvss_score      REAL,
                cvss_severity   TEXT,
                description     TEXT,
                published       TEXT,
                modified        TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_hits_pixel ON hits(pixel_id);
            CREATE INDEX IF NOT EXISTS idx_fp_pixel   ON fingerprints(pixel_id);
            CREATE INDEX IF NOT EXISTS idx_cve_pixel  ON cve_results(pixel_id);

            CREATE TABLE IF NOT EXISTS ip_intel (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pixel_id     TEXT NOT NULL,
                ts           TEXT NOT NULL,
                ip           TEXT,
                country      TEXT,
                country_code TEXT,
                region       TEXT,
                city         TEXT,
                lat          REAL,
                lon          REAL,
                isp          TEXT,
                org          TEXT,
                asn          TEXT,
                is_proxy     INTEGER DEFAULT 0,
                is_hosting   INTEGER DEFAULT 0,
                is_mobile    INTEGER DEFAULT 0,
                timezone     TEXT,
                raw_json     TEXT
            );

            CREATE TABLE IF NOT EXISTS nmap_scans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pixel_id    TEXT NOT NULL,
                ts          TEXT NOT NULL,
                ip          TEXT,
                status      TEXT DEFAULT 'pending',
                raw_output  TEXT,
                open_ports  TEXT,
                os_guess    TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_ipintel_pixel ON ip_intel(pixel_id);
            CREATE INDEX IF NOT EXISTS idx_nmap_pixel    ON nmap_scans(pixel_id);

            -- ── Lab: authentication ───────────────────────────────────────
            CREATE TABLE IF NOT EXISTS lab_users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role         TEXT NOT NULL DEFAULT 'player',  -- 'admin' | 'player'
                created_at   TEXT NOT NULL
            );

            -- ── Lab: per-challenge sessions (running containers) ──────────
            CREATE TABLE IF NOT EXISTS lab_sessions (
                challenge    TEXT PRIMARY KEY,
                container_id TEXT,
                started_at   TEXT,
                pixel_id     TEXT,
                status       TEXT DEFAULT 'stopped'
            );

            -- ── Lab: flag submissions / scoreboard ────────────────────────
            CREATE TABLE IF NOT EXISTS lab_scores (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL,
                challenge  TEXT NOT NULL,
                flag_key   TEXT NOT NULL,
                solved_at  TEXT NOT NULL,
                points     INTEGER NOT NULL,
                UNIQUE(username, challenge, flag_key)
            );

            CREATE INDEX IF NOT EXISTS idx_scores_user ON lab_scores(username);
        """)
        # Migrate existing DBs — add columns if they don't exist yet
        for col, typedef in [
            ("hostname",         "TEXT"),
            ("local_ips",        "TEXT"),
            ("ua_os",            "TEXT"),
            ("ua_os_version",    "TEXT"),
            ("ua_architecture",  "TEXT"),
            ("ua_model",         "TEXT"),
            ("ntlm_computer",    "TEXT"),
            ("ntlm_domain",      "TEXT"),
            ("camera_count",     "INTEGER"),
            ("microphone_count", "INTEGER"),
            ("prefers_dark",     "INTEGER"),
            ("pointer_type",     "TEXT"),
            ("speech_voices",    "TEXT"),
            ("rdns_hostname",    "TEXT"),   # server-side reverse DNS / NetBIOS resolution
            ("rdns_method",      "TEXT"),   # which method found it: rDNS / NetBIOS / mDNS
            ("geo_lat",          "REAL"),   # GPS latitude (browser Geolocation API)
            ("geo_lon",          "REAL"),   # GPS longitude
            ("geo_accuracy",     "REAL"),   # accuracy in metres
            ("geo_altitude",     "REAL"),
            ("geo_speed",        "REAL"),
            ("geo_heading",      "REAL"),
        ]:
            try:
                conn.execute(f"ALTER TABLE fingerprints ADD COLUMN {col} {typedef}")
            except Exception:
                pass  # column already exists


def insert_hit(pixel_id, ip, user_agent, referrer, accept_lang, headers_raw):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO hits (pixel_id,ts,ip,user_agent,referrer,accept_lang,headers_raw) "
            "VALUES (?,?,?,?,?,?,?)",
            (pixel_id, datetime.utcnow().isoformat(), ip, user_agent,
             referrer, accept_lang, json.dumps(headers_raw))
        )


def insert_fingerprint(pixel_id, ip, parsed, js_payload):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO fingerprints
            (pixel_id,ts,ip,os_family,os_version,os_raw,
             browser_family,browser_version,
             device_type,device_brand,device_model,
             screen_res,color_depth,timezone,language,platform,
             cpu_cores,memory_gb,touch,plugins,
             webgl_vendor,webgl_renderer,canvas_hash,audio_hash,fonts,
             connection_type,detected_apps,mime_types,
             hostname,local_ips,
             ua_os,ua_os_version,ua_architecture,ua_model,
             user_agent,js_payload)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pixel_id,
            datetime.utcnow().isoformat(),
            ip,
            parsed.get("os_family"),
            parsed.get("os_version"),
            parsed.get("os_raw"),
            parsed.get("browser_family"),
            parsed.get("browser_version"),
            parsed.get("device_type"),
            parsed.get("device_brand"),
            parsed.get("device_model"),
            js_payload.get("screen_res"),
            js_payload.get("color_depth"),
            js_payload.get("timezone"),
            js_payload.get("language"),
            js_payload.get("platform"),
            js_payload.get("cpu_cores"),
            js_payload.get("memory_gb"),
            js_payload.get("touch"),
            json.dumps(js_payload.get("plugins", [])),
            js_payload.get("webgl_vendor"),
            js_payload.get("webgl_renderer"),
            js_payload.get("canvas_hash"),
            js_payload.get("audio_hash"),
            json.dumps(js_payload.get("fonts", [])),
            js_payload.get("connection_type"),
            json.dumps(js_payload.get("detected_apps", [])),
            json.dumps(js_payload.get("mime_types", [])),
            js_payload.get("hostname"),
            json.dumps(js_payload.get("local_ips", [])),
            js_payload.get("ua_os"),
            js_payload.get("ua_os_version"),
            js_payload.get("ua_architecture"),
            js_payload.get("ua_model"),
            parsed.get("user_agent"),
            json.dumps(js_payload)
        ))


def update_gps(pixel_id: str, lat, lon, accuracy, altitude=None, speed=None, heading=None):
    """Store GPS coordinates from browser Geolocation API."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE fingerprints
            SET geo_lat=?, geo_lon=?, geo_accuracy=?, geo_altitude=?, geo_speed=?, geo_heading=?
            WHERE pixel_id=? AND id=(
                SELECT id FROM fingerprints WHERE pixel_id=? ORDER BY ts DESC LIMIT 1
            )
        """, (lat, lon, accuracy, altitude, speed, heading, pixel_id, pixel_id))


def update_resolved_hostname(pixel_id: str, hostname: str, method: str = ""):
    """Store server-side resolved hostname (rDNS / NetBIOS / mDNS) on the latest fingerprint."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE fingerprints
            SET rdns_hostname=?, rdns_method=?
            WHERE pixel_id=? AND id=(
                SELECT id FROM fingerprints WHERE pixel_id=? ORDER BY ts DESC LIMIT 1
            )
        """, (hostname, method, pixel_id, pixel_id))


def update_ntlm(pixel_id, computer, domain):
    """Store NTLM-leaked computer name and domain against the latest fingerprint."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE fingerprints SET ntlm_computer=?, ntlm_domain=?
            WHERE pixel_id=? AND id=(
                SELECT id FROM fingerprints WHERE pixel_id=? ORDER BY ts DESC LIMIT 1
            )
        """, (computer, domain, pixel_id, pixel_id))


def insert_cves(pixel_id, component, version, cves):
    ts = datetime.utcnow().isoformat()
    with get_conn() as conn:
        for cve in cves:
            conn.execute("""
                INSERT INTO cve_results
                (pixel_id,ts,component,version,cve_id,cvss_score,cvss_severity,description,published,modified)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                pixel_id, ts, component, version,
                cve["cve_id"], cve.get("cvss_score"), cve.get("cvss_severity"),
                cve.get("description"), cve.get("published"), cve.get("modified")
            ))


def get_all_targets():
    with get_conn() as conn:
        # Subquery picks the single latest fingerprint row per pixel_id,
        # then joins CVE counts — prevents GROUP BY picking stale/wrong rows.
        rows = conn.execute("""
            SELECT
                f.pixel_id,
                f.ip,
                f.os_family,
                f.os_version,
                f.browser_family,
                f.browser_version,
                f.device_type,
                f.device_brand,
                f.device_model,
                f.hostname,
                f.local_ips,
                f.platform,
                f.ua_os,
                f.ua_os_version,
                f.ts,
                COALESCE(cv.cve_count, 0)  as cve_count,
                cv.max_cvss                as max_cvss
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY pixel_id ORDER BY ts DESC
                ) AS rn
                FROM fingerprints
            ) f
            LEFT JOIN (
                SELECT pixel_id,
                       COUNT(DISTINCT cve_id) as cve_count,
                       MAX(cvss_score)        as max_cvss
                FROM cve_results
                GROUP BY pixel_id
            ) cv ON cv.pixel_id = f.pixel_id
            WHERE f.rn = 1
            ORDER BY f.ts DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_target(pixel_id):
    with get_conn() as conn:
        fp = conn.execute(
            "SELECT * FROM fingerprints WHERE pixel_id=? ORDER BY ts DESC LIMIT 1",
            (pixel_id,)
        ).fetchone()
        hits = conn.execute(
            "SELECT * FROM hits WHERE pixel_id=? ORDER BY ts DESC",
            (pixel_id,)
        ).fetchall()
        cves = conn.execute(
            "SELECT * FROM cve_results WHERE pixel_id=? ORDER BY cvss_score DESC",
            (pixel_id,)
        ).fetchall()
    return {
        "fingerprint": dict(fp) if fp else {},
        "hits": [dict(h) for h in hits],
        "cves": [dict(c) for c in cves],
    }


# ── IP Intelligence ───────────────────────────────────────────────────────────

def upsert_ip_intel(pixel_id: str, ip: str, data: dict):
    """Insert or replace IP intelligence data for a pixel."""
    with get_conn() as conn:
        # Delete old record for this pixel first (keep only latest)
        conn.execute("DELETE FROM ip_intel WHERE pixel_id=?", (pixel_id,))
        conn.execute("""
            INSERT INTO ip_intel
            (pixel_id, ts, ip, country, country_code, region, city,
             lat, lon, isp, org, asn, is_proxy, is_hosting, is_mobile,
             timezone, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pixel_id,
            datetime.utcnow().isoformat(),
            ip,
            data.get("country"),
            data.get("countryCode"),
            data.get("regionName"),
            data.get("city"),
            data.get("lat"),
            data.get("lon"),
            data.get("isp"),
            data.get("org"),
            data.get("as"),
            1 if data.get("proxy") else 0,
            1 if data.get("hosting") else 0,
            1 if data.get("mobile") else 0,
            data.get("timezone"),
            json.dumps(data),
        ))


def get_ip_intel(pixel_id: str) -> dict:
    """Return IP intel dict for a pixel, or empty dict."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM ip_intel WHERE pixel_id=? ORDER BY ts DESC LIMIT 1",
            (pixel_id,)
        ).fetchone()
    return dict(row) if row else {}


# ── Nmap Scans ────────────────────────────────────────────────────────────────

def upsert_nmap(pixel_id: str, ip: str, status: str,
                raw_output: str = None, open_ports: list = None, os_guess: str = None):
    """Insert or update a nmap scan record for a pixel."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM nmap_scans WHERE pixel_id=? LIMIT 1", (pixel_id,)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE nmap_scans SET ts=?, ip=?, status=?, raw_output=?,
                                      open_ports=?, os_guess=?
                WHERE pixel_id=?
            """, (
                datetime.utcnow().isoformat(), ip, status,
                raw_output, json.dumps(open_ports or []), os_guess,
                pixel_id,
            ))
        else:
            conn.execute("""
                INSERT INTO nmap_scans
                (pixel_id, ts, ip, status, raw_output, open_ports, os_guess)
                VALUES (?,?,?,?,?,?,?)
            """, (
                pixel_id, datetime.utcnow().isoformat(), ip, status,
                raw_output, json.dumps(open_ports or []), os_guess,
            ))


def get_nmap(pixel_id: str) -> dict:
    """Return nmap scan dict for a pixel, or empty dict."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM nmap_scans WHERE pixel_id=? ORDER BY ts DESC LIMIT 1",
            (pixel_id,)
        ).fetchone()
    return dict(row) if row else {}


# ── Lab: Users ────────────────────────────────────────────────────────────────

def lab_create_user(username: str, password_hash: str, role: str = "player") -> bool:
    """Create a lab user. Returns False if username already exists."""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO lab_users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
                (username, password_hash, role, datetime.utcnow().isoformat())
            )
        return True
    except Exception:
        return False


def lab_get_user(username: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM lab_users WHERE username=?", (username,)
        ).fetchone()
    return dict(row) if row else {}


def lab_list_users() -> list:
    with get_conn() as conn:
        rows = conn.execute("SELECT id, username, role, created_at FROM lab_users ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]


def lab_delete_user(username: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM lab_users WHERE username=?", (username,))


# ── Lab: Sessions (containers) ────────────────────────────────────────────────

def lab_upsert_session(challenge: str, container_id: str, status: str, pixel_id: str = None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO lab_sessions (challenge, container_id, started_at, pixel_id, status)
            VALUES (?,?,?,?,?)
            ON CONFLICT(challenge) DO UPDATE SET
                container_id=excluded.container_id,
                started_at=excluded.started_at,
                pixel_id=excluded.pixel_id,
                status=excluded.status
        """, (challenge, container_id, datetime.utcnow().isoformat(), pixel_id, status))


def lab_get_session(challenge: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM lab_sessions WHERE challenge=?", (challenge,)
        ).fetchone()
    return dict(row) if row else {}


def lab_set_session_status(challenge: str, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE lab_sessions SET status=? WHERE challenge=?", (status, challenge)
        )


# ── Lab: Scores / Flags ───────────────────────────────────────────────────────

def lab_submit_flag(username: str, challenge: str, flag_key: str, points: int) -> bool:
    """Record a solved flag. Returns False if already solved (duplicate)."""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO lab_scores (username,challenge,flag_key,solved_at,points) VALUES (?,?,?,?,?)",
                (username, challenge, flag_key, datetime.utcnow().isoformat(), points)
            )
        return True
    except Exception:
        return False  # UNIQUE constraint = already solved


def lab_get_scoreboard() -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT username, SUM(points) as total_points,
                   COUNT(*) as flags_solved,
                   MAX(solved_at) as last_solve
            FROM lab_scores
            GROUP BY username
            ORDER BY total_points DESC, last_solve ASC
        """).fetchall()
    return [dict(r) for r in rows]


def lab_get_user_solves(username: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM lab_scores WHERE username=? ORDER BY solved_at DESC",
            (username,)
        ).fetchall()
    return [dict(r) for r in rows]


def lab_already_solved(username: str, challenge: str, flag_key: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM lab_scores WHERE username=? AND challenge=? AND flag_key=?",
            (username, challenge, flag_key)
        ).fetchone()
    return row is not None
