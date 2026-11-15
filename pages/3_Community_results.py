"""Community results: accuracy tests published from different laptops.

Results and replies are stored in MongoDB Atlas. Anyone can read them;
publishing or replying needs an optional sign-in through SSOJet.
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
community.sidebar_account()
st.title("Community results")
st.write("Every run here is a real accuracy test published from someone's laptop: how "
         "far the Quantum Rings compression dial could be turned down before the "
         "quantum team started losing games. Anyone can read the board; sign in "
         "only if you want to post a result or reply.")

if not community.database_ready():
    st.info("The shared results database isn't set up on this laptop yet (the MongoDB "
            "Atlas connection is missing from .streamlit/secrets.toml).")
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

# ---------- Replies ----------
st.write("---")
st.subheader("Replies")
chosen = runs[pick]["run_id"]
try:
    thread = community.replies_for(chosen)
except Exception as error:
    thread = []
    st.error(f"Couldn't load replies: {error}")
if not thread:
    st.caption("No replies yet on this run.")
for reply in thread:
    when = pd.to_datetime(reply["posted_at"]).strftime("%b %d, %H:%M")
    with st.chat_message("user"):
        st.markdown(f"**{reply['user_name']}** · {when}")
        st.text(reply["text"])

if community.sign_in_box("reply", why="reply to this run"):
    with st.form("reply_form", clear_on_submit=True):
        text = st.text_area("Your reply", max_chars=community.MAX_REPLY,
                            placeholder="Did you get the same cheapest setting on your laptop?")
        if st.form_submit_button("Post reply"):
            try:
                community.post_reply(chosen, text)
                st.rerun()
            except Exception as error:
                st.error(f"Couldn't post: {error}")
