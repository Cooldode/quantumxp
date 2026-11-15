"""Home: the landing page, with a big box that takes you to the game."""
import streamlit as st

import ui

ui.hero("Hack The Nest 2026 · Quantum Leap",
        "A card game a quantum team never loses",
        "Players can't talk and each sees only their own card. The best classical plan "
        "wins 3 rounds out of 4. A team sharing entangled qubits, simulated on this laptop "
        "with the Quantum Rings SDK, wins every round.")

# ---------- The big "play" box ----------
with st.container(key="home_play"):
    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
        st.markdown('<div class="qx-eyebrow">Start here</div>'
                    '<div class="qx-box-title">Play the game</div>'
                    '<p class="qx-box-text">Pick a team size, deal the cards, and watch the '
                    'quantum team and the best classical team play the same rounds side '
                    'by side. Turn on sabotage to see one wrong gate break the quantum team.</p>',
                    unsafe_allow_html=True)
        if st.button("▶  Play now", type="primary", key="home_play_btn"):
            st.switch_page("play.py")
    with right:
        st.markdown(
            '<div class="qx-deal">'
            '<div class="qx-pcard">1</div><div class="qx-pcard">1</div>'
            '<div class="qx-pcard">0</div></div>'
            '<p class="qx-deal-caption">Two 1-cards dealt, so the answers must add up to an '
            '<b>odd</b> total.</p>', unsafe_allow_html=True)

# ---------- Quick facts ----------
a, b, c = st.columns(3)
a.metric("Best classical team, 3 players", "75%")
b.metric("Quantum team (ideal simulation)", "100%")
c.metric("Largest game run on a laptop", "200 qubits")

# ---------- The other pages ----------
st.markdown('<div class="qx-section">Explore</div>', unsafe_allow_html=True)
pages = [
    ("explore_acc", "🎛️", "Accuracy test",
     "Turn the simulator's compression dial down and find where the quantum team "
     "starts losing.", "pages/1_The_accuracy_test.py"),
    ("explore_laptop", "💻", "Laptop vs. quantum",
     "Why a laptop can run 200 qubits of this game, and where that trick stops working.",
     "pages/2_Can_a_laptop_keep_up.py"),
    ("explore_com", "💬", "Community",
     "Results published from other laptops. Sign in only if you want to post or reply.",
     "pages/3_Community_results.py"),
]
for column, (key, icon, title, text, target) in zip(st.columns(3), pages):
    with column:
        with st.container(key=key):
            st.markdown(f'<div class="qx-small-icon">{icon}</div>'
                        f'<div class="qx-small-title">{title}</div>'
                        f'<p class="qx-box-text">{text}</p>', unsafe_allow_html=True)
            if st.button("Open", key=f"{key}_btn"):
                st.switch_page(target)
