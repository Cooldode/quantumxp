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


def _claim(*names):
    """First sign-in detail that the provider actually sent, or None."""
    for name in names:
        try:
            value = st.user.get(name)
        except Exception:
            value = None
        if value:
            return str(value)
    return None


def user_label():
    """A display name. Providers differ in what they send, so try several."""
    name = _claim("name", "preferred_username", "nickname", "username", "given_name", "email")
    if name:
        return name
    account = _claim("sub")              # always sent: a stable account id
    return f"user-{account[-6:]}" if account else "signed-in user"


def user_email():
    return _claim("email")


def user_id():
    """Stable id for counting people: the email if we have it, else the account id."""
    return user_email() or _claim("sub")


def sign_in_box(key, why="publish your results"):
    """Optional sign-in, shown only where someone chooses to post something.

    Returns True when the person is signed in. Everything else in the app
    works without an account.
    """
    if not login_ready():
        st.info("Sign-in isn't set up on this laptop yet (SSOJet details are missing "
                "from .streamlit/secrets.toml).")
        return False
    if signed_in():
        left, right = st.columns([3, 1])
        left.caption(f"Posting as **{user_label()}** (signed in with SSOJet).")
        if right.button("Sign out", key=f"{key}_signout"):
            st.logout()
        return True
    st.caption(f"Optional: sign in to {why}. You don't need an account for "
               "anything else in the app. On the sign-in page, choose "
               "**Continue with GitHub**.")
    if st.button("Sign in with SSOJet", key=f"{key}_signin"):
        st.login(PROVIDER)
    return False


# ---------- Receipts ----------

def total_ram_bytes():
    """This computer's real memory in bytes, or None if it can't be read."""
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        pass
    try:                                   # macOS fallback
        import subprocess
        out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True,
                             text=True, timeout=2).stdout.strip()
        return int(out) if out else None
    except Exception:
        return None


def machine_info():
    ram_bytes = total_ram_bytes()
    ram = round(ram_bytes / 2**30) if ram_bytes else None
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
        "user_id": user_id(),
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


# ---------- Replies (the forum part) ----------
#
# One document per reply, linked to a published run by run_id.

MAX_REPLY = 1000


def _replies():
    _runs()                                   # opens the shared client
    replies = _client[DATABASE]["replies"]
    replies.create_index([("run_id", 1), ("posted_at", 1)])
    return replies


def post_reply(run_id, text):
    text = text.strip()[:MAX_REPLY]
    if not text:
        raise ValueError("The reply is empty.")
    _replies().insert_one({
        "run_id": run_id,
        "posted_at": datetime.now(timezone.utc),
        "user_name": user_label(),
        "user_email": user_email(),
        "user_id": user_id(),
        "text": text,
    })


def replies_for(run_id):
    """Replies to one run, oldest first. Emails are not returned."""
    return list(_replies().find({"run_id": run_id},
                                {"_id": 0, "user_name": 1, "text": 1, "posted_at": 1})
                .sort("posted_at", 1))


def dial_averages(total_qubits, layers):
    """The same test across every laptop: win rate at each dial setting.

    One aggregation pipeline, run inside MongoDB: keep the runs that used
    this circuit size, unpack each run's nested list of results, then group
    the points by dial setting.
    """
    pipeline = [
        {"$match": {"circuit.total_qubits": total_qubits, "circuit.layers": layers}},
        {"$unwind": "$results"},
        {"$group": {"_id": "$results.dial",
                    "average": {"$avg": "$results.win_rate"},
                    "lowest": {"$min": "$results.win_rate"},
                    "runs": {"$sum": 1}}},
    ]
    rows = [{"Dial": g["_id"], "Average win rate (%)": round(g["average"], 1),
             "Lowest win rate (%)": g["lowest"], "Runs": g["runs"]}
            for g in _runs().aggregate(pipeline)]
    return sorted(rows, key=lambda r: int(r["Dial"]) if str(r["Dial"]).isdigit() else 10**9)


def summary():
    """Totals for the page header."""
    runs = _runs()
    return {"runs": runs.count_documents({}),
            "people": len({e for e in runs.distinct("user_email") + runs.distinct("user_id") if e}),
            "chips": len(runs.distinct("machine.chip"))}
