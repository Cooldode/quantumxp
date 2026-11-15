"""Sign-in (SSOJet) and the shared results database (MongoDB Atlas).

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

    [mongodb]
    url = "mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/"
"""
import importlib.metadata
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
    section = _secrets_section("mongodb")
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



def sidebar_account():
    """A small account panel in the sidebar of every page."""
    with st.sidebar:
        st.markdown("**Account**")
        if not login_ready():
            st.caption("Sign-in isn't set up on this laptop.")
            return
        if signed_in():
            st.write(f"Signed in as **{user_label()}**")
            st.caption("Secured by SSOJet")
            if st.button("Sign out", key="sidebar_signout"):
                st.logout()
        else:
            st.caption("Sign in to publish your results to the community board.")
            if st.button("Sign in with SSOJet", key="sidebar_signin", type="primary"):
                st.login(PROVIDER)


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


# ---------- MongoDB Atlas ----------
#
# One document per published run: the whole receipt, plus who published it
# and when. MongoDB stores the JSON receipt as it is, with no table to design.

DATABASE = "quantumxp"
COLLECTION = "runs"
_client = None


def _runs():
    """The 'runs' collection, connecting once per app session."""
    global _client
    if _client is None:
        import certifi
        from pymongo import MongoClient
        _client = MongoClient(_secrets_section("mongodb")["url"],
                              serverSelectionTimeoutMS=10000,
                              tlsCAFile=certifi.where())
    runs = _client[DATABASE][COLLECTION]
    runs.create_index("published_at")
    return runs


def publish(receipt):
    run_id = str(uuid.uuid4())
    _runs().insert_one({
        "run_id": run_id,
        "published_at": datetime.now(timezone.utc),
        "user_name": user_label(),
        "user_email": user_email(),
        **receipt,
    })
    return run_id


def recent_runs(limit=50):
    """One row per published run, newest first."""
    rows = []
    for doc in _runs().find({}, {"_id": 0}).sort("published_at", -1).limit(limit):
        machine, circuit = doc.get("machine", {}), doc.get("circuit", {})
        rows.append({"run_id": doc["run_id"], "Published": doc["published_at"],
                     "By": doc.get("user_name"), "OS": machine.get("os"),
                     "Chip": machine.get("chip"), "RAM (GiB)": machine.get("ram_gib"),
                     "Qubits": circuit.get("total_qubits"), "Layers": circuit.get("layers"),
                     "Cheapest perfect dial": doc.get("cheapest_perfect_dial"),
                     "Settings tested": len(doc.get("results", []))})
    return rows


def run_points(run_id):
    doc = _runs().find_one({"run_id": run_id}, {"_id": 0, "results": 1}) or {}
    return [{"Dial": r["dial"], "Win rate (%)": r["win_rate"], "Seconds": r["seconds"],
             "Peak bytes": r["peak_bytes"]} for r in doc.get("results", [])]


def summary():
    """Totals for the page header."""
    runs = _runs()
    return {"runs": runs.count_documents({}),
            "people": len([e for e in runs.distinct("user_email") if e]),
            "chips": len(runs.distinct("machine.chip"))}
