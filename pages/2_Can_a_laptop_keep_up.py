"""Can a laptop keep up?

Some quantum circuits are easy for a laptop to simulate and some get out of
reach fast. This page lets people find the line themselves, with real runs
on the Quantum Rings simulator.
"""
import json
import math
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import benchmark  # noqa: E402  (our helper that runs circuits with a time limit)
import community  # noqa: E402  (SSOJet sign-in)

LIVE_LIMIT = 30      # seconds a live run may take before we give up on it
FAST_SECONDS = 1.0   # "fast" means the simulation itself finished in under this

import ui  # noqa: E402
ui.hero("Laptop vs. quantum", "Can a laptop keep up?",
        "How Quantum Rings simulates hundreds of qubits on an ordinary laptop, "
        "and where that trick has limits.")
st.write("On the game page, a laptop ran a 200-qubit quantum game in a fraction of a second "
         "per round. That sounds impossible, so what is going on? This page lets you "
         "find out which quantum circuits are easy for a laptop and which ones are not.")
st.caption("Every run on this page is real: it happens live on the Quantum Rings "
           "simulator on this laptop. Times include only the simulation itself.")

tab_idea, tab_guess, tab_dial, tab_measured = st.tabs(
    ["The idea", "Game: fast or slow?", "Game: the accuracy dial", "Measured on this laptop"])


def human_bytes(count):
    """Binary units (1 GB = 1024^3 bytes), the way computers report memory."""
    for unit in ("bytes", "KB", "MB", "GB", "TB", "PB", "EB"):
        if count < 1024:
            whole = count >= 10 or unit == "bytes" or count == int(count)
            return f"{count:,.0f} {unit}" if whole else f"{count:.1f} {unit}"
        count /= 1024
    return f"{count:,.0f} ZB"


def describe(row):
    """Turn one benchmark result into a short line of plain English."""
    if row["status"] != "ok":
        return f"The laptop could not keep up: {row['status']}."
    return f"Finished in {row['seconds']:.3f} seconds."


# ---------- The idea ----------
with tab_idea:
    st.subheader("The slow way: write everything down")
    st.write("The obvious way to simulate qubits is to keep a list with one number for "
             "every possible combination of 0s and 1s. Each extra qubit doubles the list. "
             "Slide to see how fast that gets out of hand.")
    q = st.slider("Number of qubits", 1, 60, 20, key="idea_qubits")
    size = 16 * 2 ** q          # 16 bytes per number
    if ui.viewer_is_local():
        ram = community.total_ram_bytes()     # measured on this computer, not guessed
        name, whose = "Memory in this computer", "this computer's"
    else:
        # The app is running on our machine, not the visitor's, and a web page
        # is not allowed to read how much memory a visitor's computer has.
        choice = st.select_slider(
            "How much memory does your computer have?", options=[4, 8, 16, 32, 64, 128],
            value=16, format_func=lambda gb: f"{gb} GB", key="idea_ram")
        st.caption("Pick your own: a website can't read how much memory your computer has. "
                   "(On Windows it's in Settings, System, About. On a Mac it's in "
                   "Apple menu, About This Mac.)")
        ram = choice * 2 ** 30
        name, whose = "Memory in your computer", "your computer's"
    left, right = st.columns(2)
    left.metric("Memory the full list needs", human_bytes(size))
    if ram:
        right.metric(name, human_bytes(ram))
        limit = int(math.log2(ram / 16))          # most qubits whose list fits
        if size <= ram:
            st.success(f"{q} qubits fit in {whose} {human_bytes(ram)} of memory "
                       f"(using all of it, in theory).")
        else:
            st.error(f"{q} qubits do not fit in {whose} {human_bytes(ram)} of memory. "
                     f"The full list is {size / ram:,.0f} times too big.")
        st.write(f"With {human_bytes(ram)} the full list stops fitting after **{limit} qubits**. "
                 "Yet the game page ran 200 qubits. So the simulator must be doing "
                 "something smarter.")
    else:
        right.metric(name, "unknown")
        st.info("This computer didn't report its memory size, so we can't say where "
                "the full list stops fitting.")
        st.write("Yet the game page ran 200 qubits. So the simulator must be doing "
                 "something smarter.")

    st.subheader("The smart way: write down only the pattern")
    st.write("Quantum Rings keeps a compact description instead of the full list. "
             "How compact it can be depends on the circuit. Three examples, using 200 people:")
    st.markdown("""
1. **200 people each flipping their own coin.** Nobody depends on anybody.
   You can describe each person separately: 200 short notes. **Easy.**
2. **200 people who all copy one leader.** That is the GHZ game from the game page.
   One sentence describes everyone: "they all match". **Easy.**
3. **200 people passing whispers back and forth, over and over, each one changing
   the message a little.** Now every answer depends on everyone else's in a
   complicated way. There is no short description, and the notes grow very fast
   with every extra person. **Hard.**
""")
    st.write("Real quantum computers are built for circuits like example 3, "
             "where ordinary computers run out of room as the circuits grow.")
    st.info("Try it yourself in the next tab: guess which circuits are fast "
            "or slow, then run them for real.")

# ---------- Game: fast or slow? ----------
EXAMPLES = {
    "200 coins, each spinning on its own":
        {"family": "recipe", "n": 200, "spins": "random", "links": "none", "layers": 12,
         "story": "200 people each flipping their own coin. Nobody affects anybody."},
    "The GHZ game, 200 players":
        {"family": "game", "n": 200,
         "story": "200 people who all copy one leader, then twist and look."},
    "A scrambled group of 16":
        {"family": "recipe", "n": 16, "spins": "random", "links": "layers", "layers": 12,
         "story": "16 people passing whispers back and forth 12 times."},
    "A scrambled group of 24":
        {"family": "recipe", "n": 24, "spins": "random", "links": "layers", "layers": 12,
         "story": "24 people passing whispers back and forth 12 times."},
    "Build your own": None,
}

with tab_guess:
    st.write(f"Pick a circuit, guess whether the laptop will be **fast** "
             f"(under {FAST_SECONDS:g} second) or **slow**, then run it for real. "
             f"Runs that take more than {LIVE_LIMIT} seconds are stopped.")
    choice = st.selectbox("Pick a circuit", list(EXAMPLES), key="guess_choice")
    preset = EXAMPLES[choice]

    if preset is None:
        n = st.slider("Qubits", 2, 200, 20, key="own_n")
        spins = st.radio("Spins", ["none", "quarter", "random"], horizontal=True,
                         format_func={"none": "No spins", "quarter": "Quarter turns only",
                                      "random": "Random spins"}.get, key="own_spins")
        links = st.radio("Links between qubits", ["none", "chain", "layers"], horizontal=True,
                         format_func={"none": "No links", "chain": "One chain of links",
                                      "layers": "Links in every layer"}.get, key="own_links")
        layers = st.slider("Layers", 1, 20, 12, key="own_layers")
        spec = {"family": "recipe", "n": n, "spins": spins, "links": links, "layers": layers}
        st.caption("Tip: try changing one thing at a time to find what makes it slow.")
    else:
        spec = {key: value for key, value in preset.items() if key != "story"}
        st.write(f"**In everyday terms:** {preset['story']}")

    guess = st.radio("Your guess", ["Fast", "Slow"], horizontal=True, key="guess_pick")
    if st.button("Run it", key="guess_run"):
        with st.spinner("Simulating on this laptop..."):
            result = benchmark.run_with_limit({"part": "A", "seed": 7, **spec}, LIVE_LIMIT)
        fast = result["status"] == "ok" and result["seconds"] < FAST_SECONDS
        actual = "Fast" if fast else "Slow"
        history = st.session_state.setdefault("guess_history", [])
        history.append({"Circuit": choice if preset else "Your own",
                        "Qubits": spec["n"], "Your guess": guess, "Actual": actual,
                        "Seconds": result.get("seconds", "stopped"),
                        "Peak size (SDK units)": result.get("peak_size", "")})
        st.session_state["guess_last"] = (guess == actual, describe(result))

    last = st.session_state.get("guess_last")
    if last:
        correct, line = last
        (st.success if correct else st.warning)(
            ("You were right. " if correct else "Not this time. ") + line)
    history = st.session_state.get("guess_history", [])
    if history:
        right = sum(row["Your guess"] == row["Actual"] for row in history)
        st.metric("Your score", f"{right} of {len(history)} right")
        st.table(pd.DataFrame(history))

# ---------- Game: the accuracy dial ----------
with tab_dial:
    st.write("""
Quantum Rings has an accuracy dial. Turn it down and the simulator keeps a rougher
description, like saving a photo at lower quality: faster and smaller, but a bit blurry.

**How we check accuracy: the round trip.** We run a scrambled circuit forward and then
exactly backward. A perfect simulation ends up right back where it started, scoring
100%. A rough one ends up close, but not exactly there.
""")
    n = st.slider("Qubits", 6, 30, 20, key="dial_n")
    layers = st.slider("Layers of scrambling", 2, 20, 12, key="dial_layers")
    setting = st.select_slider("Accuracy dial", options=[2, 4, 8, 16, 32, 64, 128, 256],
                               value=64, key="dial_setting")
    st.caption("This is the simulator's `threshold` setting. Higher means more accurate. "
               "The default is 64.")

    if st.button("Run the round trip", key="dial_run"):
        spec = {"part": "B", "family": "scrambled", "n": n, "layers": layers,
                "seed": 7, "threshold": setting}
        with st.spinner("Running forward and back..."):
            result = benchmark.run_with_limit(spec, LIVE_LIMIT)
        row = {"Qubits": n, "Layers": layers, "Dial": setting}
        if result["status"] == "ok":
            row.update({"Round-trip score (%)": round(100 * float(result["fidelity"]), 2),
                        "Seconds": result["seconds"],
                        "Peak size (SDK units)": result["peak_size"]})
        else:
            row.update({"Round-trip score (%)": None, "Seconds": None,
                        "Peak size (SDK units)": result["status"]})
        st.session_state.setdefault("dial_history", []).append(row)

    dial_rows = st.session_state.get("dial_history", [])
    if dial_rows:
        latest = dial_rows[-1]
        if latest["Round-trip score (%)"] is None:
            st.error(f"The laptop could not finish: {latest['Peak size (SDK units)']}.")
        else:
            left, right = st.columns(2)
            left.metric("Round-trip score", f"{latest['Round-trip score (%)']}%")
            right.metric("Time", f"{latest['Seconds']} s")
            if latest["Round-trip score (%)"] >= 99:
                st.success("At least 99%. Can you go lower and still pass?")
            else:
                st.warning("Below 99%. Turn the dial up a step.")
        frame = pd.DataFrame(dial_rows)
        st.table(frame)
        same = frame[(frame["Qubits"] == latest["Qubits"])
                     & (frame["Layers"] == latest["Layers"])].dropna()
        if len(same) > 1:
            st.write("Your tries at this size, by dial setting:")
            st.line_chart(same.sort_values("Dial"), x="Dial",
                          y=["Round-trip score (%)", "Seconds"])

# ---------- Measured on this laptop ----------
with tab_measured:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "benchmark_results.json")
    if not os.path.exists(path):
        st.write("No saved measurements yet. In the Terminal, in the project folder, run:")
        st.code("python benchmark.py --quick", language="bash")
        st.write("Then reload this page to see the results here.")
    else:
        with open(path) as handle:
            saved = json.load(handle)
        rows = pd.DataFrame(saved["rows"])
        part_a = rows[rows["part"] == "A"].copy()
        part_a["Seconds"] = pd.to_numeric(part_a.get("seconds"), errors="coerce")
        st.subheader("Time per circuit as the qubits grow")
        for family, label in (("game", "GHZ game"), ("scrambled", "Scrambled circuit")):
            subset = part_a[part_a["family"] == family]
            if len(subset):
                st.write(f"**{label}**")
                st.table(subset[["n", "status", "Seconds"]].rename(columns={"n": "Qubits"}))
        part_b = rows[rows["part"] == "B"]
        if len(part_b):
            st.subheader("The accuracy dial on a scrambled round trip")
            st.table(part_b[["n", "threshold", "status"] +
                            [c for c in ("seconds", "fidelity", "peak_size") if c in part_b]]
                     .rename(columns={"n": "Qubits", "threshold": "Dial"}))
        st.caption(f"Each run was stopped after {saved['time_limit_s']} seconds. "
                   f"Scrambled circuits used {saved['scrambled_depth']} layers.")
