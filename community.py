"""Sign-in (SSOJet) and the shared results database (Tiger Data).

Both are optional: if they are not set up in .streamlit/secrets.toml, the
rest of the app still works and these features explain what is missing.

.streamlit/secrets.toml (never commit this file):

    [auth]
    redirect_uri = "http://localhost:8501/oauth2callback"
    cookie_secret = "any long random string"

    [auth.ssojet]
    client_id = "..."
    client_secret = "..."
    server_metadata_url = "https://.../.well-known/openid-configuration"

    [tigerdata]
    url = "postgres://user:password@host:port/tsdb?sslmode=require"
"""
import importlib.metadata
import json
import os
import platform
import uuid
from datetime import datetime, timezone

import streamlit as st

PROVIDER = "ssojet"


# ---------- Settings ----------

def _secrets_section(name):
    try:
        return st.secrets[name]
    except Exception:            # no secrets file, or no such section
        return None


def login_ready():
    auth = _secrets_section("auth")
    return bool(auth) and PROVIDER in auth


def database_ready():
    section = _secrets_section("tigerdata")
    return bool(section) and bool(section.get("url"))


def signed_in():
    try:
        return login_ready() and bool(st.user.is_logged_in)
    except Exception:
        return False


def user_label():
    try:
        return st.user.get("name") or st.user.get("email") or "signed-in user"
    except Exception:
        return "signed-in user"


def user_email():
    try:
        return st.user.get("email")
    except Exception:
        return None


def sign_in_box(key):
    """Shows the sign-in state with a sign-in or sign-out button."""
    if not login_ready():
        st.info("Sign-in isn't set up on this laptop yet (SSOJet details are missing "
                "from .streamlit/secrets.toml).")
        return False
    if signed_in():
        left, right = st.columns([3, 1])
        left.write(f"Signed in as **{user_label()}** (via SSOJet).")
        if right.button("Sign out", key=f"{key}_signout"):
            st.logout()
        return True
    if st.button("Sign in with SSOJet", key=f"{key}_signin"):
        st.login(PROVIDER)
    return False


# ---------- Receipts ----------

def machine_info():
    try:
        ram = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30)
    except (ValueError, OSError, AttributeError):
        ram = None
    mac = platform.mac_ver()[0]
    try:
        sdk = importlib.metadata.version("QuantumRingsLib")
    except importlib.metadata.PackageNotFoundError:
        sdk = "unknown"
    return {"os": f"macOS {mac}" if mac else platform.system(),
            "chip": platform.machine(), "ram_gib": ram, "sdk_version": sdk}


def build_receipt(rows, players, total, layers, seed, shots):
    """rows: finished accuracy-test rows for one circuit size."""
    machine = machine_info()
    results = [{"dial": str(r["dial"]), "win_rate": r["win_rate"],
                "seconds": r["seconds"], "peak_bytes": r["peak_bytes"]}
               for r in rows]
    perfect = [r for r in rows if r["win_rate"] >= 100]
    cheapest = min(perfect, key=lambda r: r["dial_value"])["dial"] if perfect else None
    return {
        "test": "accuracy_test",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": {k: machine[k] for k in ("os", "chip", "ram_gib")},
        "sdk": {"name": "QuantumRingsLib", "version": machine["sdk_version"],
                "backend": "scarlet_quantum_rings"},
        "circuit": {"players": players, "total_qubits": total, "layers": layers,
                    "seed": seed, "rounds_per_setting": shots * 4},
        "results": results,
        "cheapest_perfect_dial": None if cheapest is None else str(cheapest),
    }


# ---------- Tiger Data ----------

SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
    published_at   timestamptz NOT NULL DEFAULT now(),
    run_id         uuid        NOT NULL,
    user_name      text,
    user_email     text,
    os             text,
    chip           text,
    ram_gib        integer,
    sdk_version    text,
    players        integer,
    total_qubits   integer,
    layers         integer,
    dial           text,
    win_rate       real,
    seconds        real,
    peak_bytes     bigint,
    cheapest_perfect_dial text,
    receipt        jsonb
)
"""


def _connect():
    import psycopg
    return psycopg.connect(_secrets_section("tigerdata")["url"], connect_timeout=10)


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
        try:
            # Tiger Data (TimescaleDB): store the rows as a time-series hypertable.
            cur.execute("SELECT create_hypertable('receipts', by_range('published_at'), "
                        "if_not_exists => TRUE)")
        except Exception:
            conn.rollback()       # plain PostgreSQL: keep it as a normal table
            cur.execute(SCHEMA)
    conn.commit()


def publish(receipt):
    """Saves one receipt: one row per dial setting, grouped by run_id."""
    run_id = uuid.uuid4()
    machine, circuit = receipt["machine"], receipt["circuit"]
    with _connect() as conn:
        ensure_table(conn)
        with conn.cursor() as cur:
            for result in receipt["results"]:
                cur.execute(
                    "INSERT INTO receipts (run_id, user_name, user_email, os, chip, "
                    "ram_gib, sdk_version, players, total_qubits, layers, dial, "
                    "win_rate, seconds, peak_bytes, cheapest_perfect_dial, receipt) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (run_id, user_label(), user_email(), machine["os"], machine["chip"],
                     machine["ram_gib"], receipt["sdk"]["version"], circuit["players"],
                     circuit["total_qubits"], circuit["layers"], result["dial"],
                     result["win_rate"], result["seconds"], result["peak_bytes"],
                     receipt["cheapest_perfect_dial"], json.dumps(receipt)))
        conn.commit()
    return run_id


def recent_runs(limit=50):
    """One row per published run, newest first."""
    with _connect() as conn:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT run_id, max(published_at) AS published_at,
                       max(user_name), max(os), max(chip), max(ram_gib),
                       max(total_qubits), max(layers), max(cheapest_perfect_dial),
                       count(*) AS settings
                FROM receipts
                GROUP BY run_id
                ORDER BY published_at DESC
                LIMIT %s""", (limit,))
            columns = ["run_id", "Published", "By", "OS", "Chip", "RAM (GiB)",
                       "Qubits", "Layers", "Cheapest perfect dial", "Settings tested"]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def run_points(run_id):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT dial, win_rate, seconds, peak_bytes FROM receipts "
                        "WHERE run_id = %s", (run_id,))
            return [{"Dial": d, "Win rate (%)": w, "Seconds": s, "Peak bytes": p}
                    for d, w, s, p in cur.fetchall()]


def summary():
    """Totals for the page header."""
    with _connect() as conn:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT count(DISTINCT run_id), count(DISTINCT user_email), "
                        "count(DISTINCT chip) FROM receipts")
            runs, people, chips = cur.fetchone()
            return {"runs": runs, "people": people, "chips": chips}
