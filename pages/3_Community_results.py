"""Community results: accuracy tests published from different laptops.

Results are stored in Tiger Data (PostgreSQL with time-series hypertables).
Publishing needs a sign-in through SSOJet; reading does not.
"""
import os
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import community  # noqa: E402

CLASSICAL_LINE = 75.0   # best classical team with 3 players

st.set_page_config(page_title="Community results")
st.title("Community results")
st.write("Every run here is a real accuracy test published from someone's laptop: how "
         "far the Quantum Rings compression dial could be turned down before the "
         "quantum team started losing games.")

community.sign_in_box("community")

if not community.database_ready():
    st.info("The shared results database isn't set up on this laptop yet (the Tiger "
            "Data connection is missing from .streamlit/secrets.toml).")
    st.stop()

try:
    totals = community.summary()
    runs = community.recent_runs()
except Exception as error:
    st.error(f"Couldn't reach the results database: {error}")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Runs published", totals["runs"])
c2.metric("People", totals["people"])
c3.metric("Kinds of chip", totals["chips"])

if not runs:
    st.write("No results yet. Run the accuracy test, sign in, and publish the first one.")
    st.stop()

frame = pd.DataFrame(runs)
frame["Published"] = pd.to_datetime(frame["Published"]).dt.strftime("%b %d, %H:%M")
st.dataframe(frame.drop(columns=["run_id"]), hide_index=True, width="stretch")

labels = [f"{r['By']} · {r['Chip']} · {r['Qubits']} qubits · {r['Published']}"
          for r in frame.to_dict("records")]
pick = st.selectbox("See one run in detail", range(len(labels)),
                    format_func=lambda i: labels[i], key="community_pick")
points = pd.DataFrame(community.run_points(runs[pick]["run_id"]))
if len(points):
    points["dial_value"] = points["Dial"].map(
        lambda d: 512 if d == "Full accuracy" else int(d))
    x = alt.X("dial_value:Q", scale=alt.Scale(type="log", base=2),
              title="Compression dial (right = less compression)")
    line = alt.Chart(points).mark_line(point=True).encode(
        x=x, y=alt.Y("Win rate (%):Q", scale=alt.Scale(domain=[0, 100])),
        tooltip=["Dial", "Win rate (%)", "Seconds"])
    rule = alt.Chart(pd.DataFrame({"y": [CLASSICAL_LINE]})).mark_rule(
        color="red", strokeDash=[6, 4]).encode(y="y:Q")
    st.altair_chart(line + rule, width="stretch")
    st.caption("Dashed red line: the best a normal team can do with 3 players (75%).")
