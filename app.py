"""QuantumXP. Run with:  streamlit run app.py"""
import os

import streamlit as st

import ui

# The Quantum Rings key can come from the shell (export QR_TOKEN=...) or from
# the top of .streamlit/secrets.toml. Either way it ends up in the environment,
# where the game and the test runs (separate processes) read it.
for _name in ("QR_TOKEN", "QR_ACCOUNT"):
    try:
        if _name not in os.environ and _name in st.secrets:
            os.environ[_name] = str(st.secrets[_name])
    except Exception:
        pass                                  # no secrets file: fine

st.set_page_config(page_title="QuantumXP", page_icon=ui.FAVICON, layout="centered")
ui.apply_style()
ui.account_corner()
if "QR_TOKEN" not in os.environ or "QR_ACCOUNT" not in os.environ:
    st.warning("**The Quantum Rings key isn't set, so nothing can run yet.** Stop the app "
               "(Ctrl+C), then in the same Terminal window run `export QR_TOKEN=\"your key\"` "
               "and `export QR_ACCOUNT=\"your account email\"`, and start the app again. "
               "Or add those two lines, without the word export, to the very top of "
               "`.streamlit/secrets.toml`.")

pages = [
    st.Page("home.py", title="Home", icon="🏠", default=True),
    st.Page("play.py", title="Play the game", icon="🎮", url_path="play"),
    st.Page("pages/1_The_accuracy_test.py", title="Accuracy test",
            icon="🎛️", url_path="accuracy-test"),
    st.Page("pages/2_Can_a_laptop_keep_up.py", title="Laptop vs. quantum",
            icon="💻", url_path="laptop"),
    st.Page("pages/3_Community_results.py", title="Community",
            icon="💬", url_path="community"),
]
st.navigation(pages).run()
