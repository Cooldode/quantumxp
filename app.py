"""QuantumXP. Run with:  streamlit run app.py"""
import streamlit as st

import ui

st.set_page_config(page_title="QuantumXP", page_icon=ui.FAVICON, layout="centered")
ui.apply_style()
ui.account_corner()

pages = [
    st.Page("play.py", title="Play the game", icon="🎮",
            default=True),
    st.Page("pages/1_The_accuracy_test.py", title="Accuracy test",
            icon="🎛️", url_path="accuracy-test"),
    st.Page("pages/2_Can_a_laptop_keep_up.py", title="Laptop vs. quantum",
            icon="💻", url_path="laptop"),
    st.Page("pages/3_Community_results.py", title="Community",
            icon="💬", url_path="community"),
]
st.navigation(pages).run()
