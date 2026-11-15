"""The accuracy test: the game as a check on the simulator.

The three players' linked qubits go on a round trip through a heavy circuit
and exactly back. A perfect simulation returns them untouched, so the quantum
team keeps winning every round. Turn up the compression and the quantum team
starts losing: the game itself shows how accurate the simulation was.
"""
import importlib.metadata
import json
import os
import platform
import sys

import altair as alt
import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import benchmark  # noqa: E402  (runs circuits in a separate process, with a time limit)
import community  # noqa: E402  (SSOJet sign-in and the MongoDB Atlas results database)
import game       # noqa: E402  (the classical limit)

LIVE_LIMIT = 20          # seconds one dial setting may take before we stop it
PLAYERS = 3
SHOTS = 25               # rounds per deal; 3 players have 4 deals, so 100 rounds

st.set_page_config(page_title="The accuracy test")
community.sidebar_account()
st.title("The accuracy test")
st.subheader("Can the simulator keep the quantum team perfect?")

st.markdown("""
**How the simulator fits big circuits on a laptop.** Quantum Rings saves memory by
compressing. Its engine is MPS-based, and a dial controls how hard it compresses.
Turn the dial down and it runs faster and lighter, but less accurately, like saving
a photo at lower quality.

**Our test.** Three players link their qubits, as in the game. Then we send those
qubits on a round trip: through a big tangled circuit that mixes them with helper
qubits, and then exactly backwards. A perfect simulator brings them back untouched,
so the quantum team still wins every round. If it compresses too hard, small errors
creep in, and the quantum team starts losing.

**The red line** is the best a normal team can ever do: 75% for three players.
Below it, the simulated quantum team is doing worse than a team with no quantum at all.
""")
classical = 100 * game.best_classical_plan(PLAYERS)[2]


def dial_label(setting):
    return "Full accuracy" if setting == "full" else str(setting)


def verdict(rate):
    if rate >= 100:
        return "success", "Perfect: the round trip came back untouched."
    if rate >= classical:
        return "warning", "Some rounds lost: compression errors are creeping in."
    return "error", ("Below the classical line: at this setting the simulated quantum "
                     "team does worse than a team with no quantum at all.")


def receipt(total, layers, setting):
    try:
        sdk = importlib.metadata.version("QuantumRingsLib")
    except importlib.metadata.PackageNotFoundError:
        sdk = "unknown"
    try:
        ram = f"{os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30:.0f} GiB RAM"
    except (ValueError, OSError, AttributeError):
        ram = "RAM unknown"
    mac = platform.mac_ver()[0]
    machine = f"macOS {mac}" if mac else platform.system()
    dial = ("HIGHESTACCURACY" if setting == "full"
            else f"performance CUSTOM, threshold {setting}")
    return (f"{machine} ({platform.machine()}), {ram} · QuantumRingsLib {sdk} · "
            f"CPU backend (scarlet_quantum_rings), SDK default precision · {dial} · "
            f"{PLAYERS} players + {total - PLAYERS} helpers, {layers} scrambling layers, "
            f"seed 7 · {SHOTS} rounds on each of 4 deals")


def run_one(total, layers, setting):
    spec = {"part": "C", "players": PLAYERS, "total": total, "layers": layers,
            "threshold": setting, "seed": 7, "shots": SHOTS}
    result = benchmark.run_with_limit(spec, LIVE_LIMIT)
    row = {"Qubits": total, "Layers": layers, "Dial": dial_label(setting),
           "dial_value": 512 if setting == "full" else setting}
    if result["status"] == "ok":
        row.update({"Win rate (%)": round(100 * result["wins"] / result["rounds"], 1),
                    "Seconds": result["seconds"],
                    "Peak memory (MiB)": round(result["peak_bytes"] / 2**20, 1),
                    "peak_bytes": result["peak_bytes"],
                    "Status": "finished"})
    else:
        row.update({"Win rate (%)": None, "Seconds": None,
                    "Peak memory (MiB)": None, "peak_bytes": None,
                    "Status": result["status"]})
    return row


# ---------- Controls ----------
left, right = st.columns(2)
total = left.slider("Size of the round trip (qubits, including helpers)", 6, 30, 20,
                    key="acc_total")
layers = right.slider("How tangled the round trip is (layers)", 2, 24, 12, key="acc_layers")
setting = st.select_slider("Compression dial (lower = more compression)",
                           options=benchmark.DIAL, value=64, format_func=dial_label,
                           key="acc_setting")
st.caption("The dial is the simulator's `threshold` setting; the default is 64. "
           "\"Full accuracy\" uses the HIGHESTACCURACY mode.")

history = st.session_state.setdefault("acc_history", [])
b1, b2 = st.columns(2)
if b1.button("Play 100 rounds at this setting", key="acc_one"):
    with st.spinner("Linking, scrambling, unscrambling, playing..."):
        history.append(run_one(total, layers, setting))
if b2.button("Sweep the whole dial", key="acc_sweep"):
    progress = st.progress(0.0)
    for i, rung in enumerate(benchmark.DIAL):
        row = run_one(total, layers, rung)
        history.append(row)
        progress.progress((i + 1) / len(benchmark.DIAL))
        if row["Status"] != "finished":
            st.info(f"Stopped the sweep at {dial_label(rung)}: higher settings only get slower.")
            break

# ---------- Results ----------
if history:
    latest = history[-1]
    if latest["Win rate (%)"] is None:
        st.error(f"The laptop could not finish this setting: {latest['Status']}.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Quantum team", f"{latest['Win rate (%)']}%")
        c2.metric("Best normal team", f"{classical:.0f}%")
        c3.metric("Time", f"{latest['Seconds']} s")
        kind, line = verdict(latest["Win rate (%)"])
        getattr(st, kind)(line)
        st.caption("Receipt: " + receipt(latest["Qubits"], latest["Layers"],
                                         "full" if latest["Dial"] == "Full accuracy"
                                         else int(latest["Dial"])))

    frame = pd.DataFrame(history)
    same = frame[(frame["Qubits"] == latest["Qubits"]) & (frame["Layers"] == latest["Layers"])]
    same = same.dropna(subset=["Win rate (%)"]).drop_duplicates("Dial", keep="last")
    if len(same) > 1:
        st.write(f"**Win rate across the dial** ({latest['Qubits']} qubits, "
                 f"{latest['Layers']} layers)")
        x = alt.X("dial_value:Q", scale=alt.Scale(type="log", base=2),
                  title="Compression dial (right = less compression; far right = full accuracy)")
        points = alt.Chart(same).mark_line(point=True).encode(
            x=x, y=alt.Y("Win rate (%):Q", scale=alt.Scale(domain=[0, 100])),
            tooltip=["Dial", "Win rate (%)", "Seconds", "Peak memory (MiB)"])
        line = alt.Chart(pd.DataFrame({"y": [classical]})).mark_rule(
            color="red", strokeDash=[6, 4]).encode(y="y:Q")
        st.altair_chart(points + line, width="stretch")
        passing = same[same["Win rate (%)"] >= 100]
        if len(passing):
            cheapest = passing.sort_values("dial_value").iloc[0]
            st.success(f"Cheapest setting that kept the quantum team perfect: "
                       f"{cheapest['Dial']} ({cheapest['Seconds']} s).")
    st.table(frame.drop(columns=["dial_value", "peak_bytes"]))

    # ---------- Share this result ----------
    if len(same):
        st.write("---")
        st.subheader("Share your result")
        receipt = community.build_receipt(
            [{"dial": r["Dial"], "dial_value": r["dial_value"], "win_rate": r["Win rate (%)"],
              "seconds": r["Seconds"], "peak_bytes": r["peak_bytes"]}
             for _, r in same.sort_values("dial_value").iterrows()],
            PLAYERS, int(latest["Qubits"]), int(latest["Layers"]), 7, SHOTS)
        st.download_button("Download receipt (JSON)", json.dumps(receipt, indent=2),
                           file_name="quantumxp_receipt.json", mime="application/json",
                           key="acc_download")
        st.caption("Publishing adds this run to the Community results page, so you can "
                   "compare how different laptops handle the same test.")
        if community.sign_in_box("acc"):
            if not community.database_ready():
                st.info("Publishing isn't set up on this laptop yet (the MongoDB Atlas "
                        "connection is missing from .streamlit/secrets.toml).")
            elif st.button("Publish to Community results", key="acc_publish"):
                try:
                    community.publish(receipt)
                    st.success("Published. See it on the Community results page.")
                except Exception as error:
                    st.error(f"Couldn't publish: {error}")

st.write("**Challenge:** find the cheapest dial setting that keeps the quantum team "
         "at 100%. Quantum Rings set a very similar challenge at MIT's iQuHACK 2026: "
         "find the lowest setting that keeps a round trip at least 99% accurate.")

# ---------- Saved sweep from the command line ----------
saved_path = os.path.join(ROOT, "accuracy_test_results.json")
if os.path.exists(saved_path):
    with st.expander("Saved sweep (from `python benchmark.py --accuracy-test`)"):
        with open(saved_path) as handle:
            saved = pd.DataFrame(json.load(handle)["rows"])
        keep = [c for c in ("total", "layers", "threshold", "status", "win_rate",
                            "seconds", "peak_bytes") if c in saved]
        st.table(saved[keep])
