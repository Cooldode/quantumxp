"""Shared look and feel: page headers and the custom styling."""
import os

import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
FAVICON = os.path.join(ROOT, "assets", "favicon.png")
LOGO = os.path.join(ROOT, "assets", "logo.png")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@500&display=swap');

html, body, .stMarkdown, .stMarkdown p, label, input, textarea, h1, h2, h3, h4 {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* Background: deep navy with a soft violet and cyan glow at the top */
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(900px 420px at 15% -10%, rgba(167,139,250,0.20), transparent 60%),
    radial-gradient(700px 360px at 95% 0%, rgba(34,211,238,0.12), transparent 60%),
    #0E0F27;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1040px; padding-top: 2.2rem; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: #0B0C20;
  border-right: 1px solid rgba(167,139,250,0.15);
}
[data-testid="stSidebarNav"] a { border-radius: 10px; }
.qx-brand { display:flex; align-items:center; gap:.55rem; margin:.2rem 0 .8rem; }
.qx-brand b { font-size: 1.15rem; letter-spacing: -.01em; }
.qx-brand span { color:#8C88B8; font-size:.78rem; display:block; margin-top:-.15rem; }

/* Account control, pinned to the top-right corner */
.st-key-qx_account {
  position: fixed; top: 4rem; right: 1.4rem; z-index: 999991; width: auto !important;
}
.st-key-qx_account button { padding: .35rem .95rem; border-radius: 999px; }

/* Page header */
.qx-hero { padding: .4rem 0 1.4rem; margin-bottom: 1.2rem;
           border-bottom: 1px solid rgba(167,139,250,0.14); }
.qx-kicker { display:inline-block; font-size:.75rem; font-weight:600; letter-spacing:.08em;
             text-transform:uppercase; color:#C4B5FD; background:rgba(167,139,250,0.12);
             border:1px solid rgba(167,139,250,0.30); padding:.28rem .7rem; border-radius:999px; }
.qx-title { font-size: clamp(2rem, 4.2vw, 3.1rem); font-weight: 800; line-height: 1.08;
            letter-spacing: -.025em; margin: .8rem 0 .6rem;
            background: linear-gradient(90deg, #FFFFFF 0%, #C4B5FD 55%, #67E8F9 100%);
            -webkit-background-clip: text; background-clip: text; color: transparent; }
.qx-sub { color:#A9A6CF; font-size:1.08rem; max-width: 720px; line-height:1.55; margin:0; }

/* Rule cards */
.qx-cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap:.8rem; margin: .2rem 0 1rem; }
.qx-card { background: rgba(23,24,58,0.75); border:1px solid rgba(167,139,250,0.18);
           border-radius:16px; padding:1rem 1.1rem; }
.qx-card .n { font-family:'JetBrains Mono', monospace; color:#67E8F9; font-size:.8rem; }
.qx-card h4 { margin:.3rem 0 .35rem; font-size:1.02rem; font-weight:600; color:#F3F1FF; }
.qx-card p { margin:0; color:#A9A6CF; font-size:.92rem; line-height:1.5; }

/* Home page boxes */
.st-key-home_play {
  background: linear-gradient(135deg, rgba(139,92,246,0.28), rgba(34,211,238,0.10));
  border: 1px solid rgba(167,139,250,0.45); border-radius: 22px;
  padding: 1.6rem 1.8rem; margin-bottom: 1.2rem;
}
.st-key-explore_acc, .st-key-explore_laptop, .st-key-explore_com {
  background: rgba(23,24,58,0.75); border: 1px solid rgba(167,139,250,0.18);
  border-radius: 18px; padding: 1.1rem 1.2rem; min-height: 230px;
  transition: border-color .15s ease, transform .15s ease;
}
.st-key-explore_acc:hover, .st-key-explore_laptop:hover, .st-key-explore_com:hover {
  border-color: #A78BFA; transform: translateY(-2px);
}
.qx-eyebrow { font-family:'JetBrains Mono', monospace; color:#67E8F9; font-size:.78rem;
              letter-spacing:.08em; text-transform:uppercase; }
.qx-box-title { font-size:1.9rem; font-weight:800; letter-spacing:-.02em; margin:.25rem 0 .4rem; }
.qx-box-text { color:#B9B6DD; line-height:1.55; margin:0 0 .6rem; }
.qx-small-icon { font-size:1.6rem; }
.qx-small-title { font-size:1.15rem; font-weight:700; margin:.3rem 0 .35rem; }
.qx-section { font-size:1.25rem; font-weight:700; margin:1.4rem 0 .6rem; }
.qx-deal { display:flex; gap:.7rem; justify-content:center; }
.qx-pcard { width:72px; height:100px; border-radius:12px; display:flex; align-items:center;
            justify-content:center; font-size:2.2rem; font-weight:800; color:#0E0F27;
            background: linear-gradient(160deg, #F5F3FF, #C4B5FD);
            box-shadow: 0 10px 28px rgba(139,92,246,0.35); }
.qx-pcard:nth-child(2) { transform: translateY(-8px) rotate(2deg); }
.qx-pcard:nth-child(1) { transform: rotate(-4deg); }
.qx-pcard:nth-child(3) { transform: rotate(5deg); }
.qx-deal-caption { text-align:center; color:#B9B6DD; font-size:.9rem; margin-top:.9rem; }

/* Metrics as cards */
[data-testid="stMetric"] {
  background: rgba(23,24,58,0.75); border:1px solid rgba(167,139,250,0.20);
  border-radius:16px; padding: .9rem 1.1rem;
}
[data-testid="stMetricValue"] { font-weight:800; letter-spacing:-.02em; }
[data-testid="stMetricLabel"] p { color:#A9A6CF; font-weight:500; }

/* Buttons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 12px; font-weight: 600; padding: .55rem 1.15rem;
  border: 1px solid rgba(167,139,250,0.35); background: rgba(167,139,250,0.08);
  transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  transform: translateY(-1px); background: rgba(167,139,250,0.18);
  box-shadow: 0 6px 22px rgba(167,139,250,0.25); border-color:#A78BFA;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(90deg, #8B5CF6, #22D3EE); border: none; color: #0B0C20;
}

/* Tabs as pills */
.stTabs [role="tablist"] { gap:.45rem; border-bottom:none; flex-wrap: wrap; }
.stTabs button[role="tab"] {
  background: rgba(23,24,58,0.7); border:1px solid rgba(167,139,250,0.18);
  border-radius:999px; padding:.35rem 1rem; height:auto;
}
.stTabs button[role="tab"][aria-selected="true"] {
  background: rgba(167,139,250,0.22); border-color:#A78BFA;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

/* Expanders, alerts, tables, inputs */
[data-testid="stExpander"] details, [data-testid="stAlert"], [data-testid="stTable"],
[data-testid="stDataFrame"], [data-testid="stForm"] { border-radius: 14px; }
[data-testid="stForm"] { border:1px solid rgba(167,139,250,0.20); background: rgba(23,24,58,0.5); }
h2, h3 { letter-spacing: -.015em; }
hr { border-color: rgba(167,139,250,0.14) !important; }
footer { visibility: hidden; }
</style>
"""


def apply_style():
    """Call once per run, from the app's entry point."""
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        st.logo(LOGO, icon_image=FAVICON, size="large")
    except TypeError:                 # older Streamlit without size=
        st.logo(LOGO, icon_image=FAVICON)
    with st.sidebar:
        st.caption("[About the project](https://quantumxp.us/) · "
                   "[Code](https://github.com/Cooldode/quantumxp)")
        if not viewer_is_local():
            st.caption("You're using the app over the web. The quantum simulations run "
                       "on the team's computer, not yours.")


def hero(kicker, title, subtitle=""):
    """The header block at the top of each page."""
    sub = f'<p class="qx-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<div class="qx-hero"><span class="qx-kicker">{kicker}</span>'
                f'<div class="qx-title">{title}</div>{sub}</div>', unsafe_allow_html=True)


def cards(items):
    """A row of small cards: items is a list of (label, heading, text)."""
    html = "".join(f'<div class="qx-card"><div class="n">{n}</div><h4>{h}</h4><p>{t}</p></div>'
                   for n, h, t in items)
    st.markdown(f'<div class="qx-cards">{html}</div>', unsafe_allow_html=True)


def account_corner():
    """Sign in / sign out, pinned to the top-right corner of every page."""
    import community
    if not community.login_ready():
        return
    try:
        box = st.container(key="qx_account")
    except TypeError:                 # older Streamlit: falls back to the top of the page
        box = st.container()
    with box:
        if community.signed_in():
            with st.popover(f"👤 {community.user_label()}"):
                st.caption("Signed in with SSOJet")
                if st.button("Sign out", key="corner_signout"):
                    st.logout()
        elif st.button("Sign in", key="corner_signin", type="primary",
                       help="Opens the SSOJet sign-in page. Use your email or Continue with GitHub."):
            st.login(community.PROVIDER)


def viewer_is_local():
    """True when the browser is on the same computer that is running the app.

    Someone using the app through the website is on a different computer, so
    anything we measure here (memory, chip) is ours, not theirs.
    """
    try:
        host = (st.context.headers.get("host") or "").split(":")[0].lower()
    except Exception:
        return True
    return host in ("", "localhost", "127.0.0.1", "[")
