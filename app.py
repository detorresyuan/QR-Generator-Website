import streamlit as st
import psycopg2
import bcrypt
import requests
import qrcode
import io
import base64
import re
import time
from datetime import datetime

try:
    from streamlit_lottie import st_lottie
    HAS_LOTTIE = True
except ImportError:
    HAS_LOTTIE = False

# ═══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="QR Studio",
    page_icon="🔲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
# DESIGN SYSTEM — CSS & FONTS
# Palette: GitHub-dark-inspired zinc/slate greys + warm orange accent
# Body copy: Times New Roman  |  UI chrome: Inter  |  Headings: Playfair Display
# ═══════════════════════════════════════════════════════════════
GLOBAL_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">

<style>
/* ── DESIGN TOKENS ─────────────────────────────────────────── */
:root {
  /* Surface layers — zinc-slate stack (GitHub dark-ish, warmer than pure black) */
  --bg-0:        #0d1117;   /* page canvas   */
  --bg-1:        #161b22;   /* sidebar        */
  --bg-2:        #1c2128;   /* card / input   */
  --bg-3:        #22272e;   /* hover / chip   */
  --bg-4:        #2d333b;   /* active states  */

  /* Borders */
  --border:      #30363d;
  --border-2:    #444c56;

  /* Text */
  --tx-1:        #e6edf3;   /* primary   */
  --tx-2:        #8b949e;   /* secondary */
  --tx-3:        #6e7681;   /* muted     */

  /* Accent — warm amber-orange (Claude / Cloudflare-flavoured) */
  --accent:      #f0883e;
  --accent-h:    #f5a461;
  --accent-d:    #c1610f;
  --accent-bg:   rgba(240,136,62,.10);
  --accent-ring: rgba(240,136,62,.20);

  /* Semantic */
  --red:         #f85149;
  --green:       #3fb950;
  --yellow:      #d29922;
  --blue:        #58a6ff;

  /* Shape */
  --r-xs:  6px;
  --r-sm:  8px;
  --r:     10px;
  --r-lg:  14px;
  --r-xl:  20px;

  /* Shadow */
  --shadow-sm:  0 1px 3px rgba(1,4,9,.60);
  --shadow-md:  0 4px 16px rgba(1,4,9,.55);
  --shadow-lg:  0 12px 40px rgba(1,4,9,.70);
  --shadow-xl:  0 24px 64px rgba(1,4,9,.75);

  /* Typography */
  --font-h:  'Playfair Display', Georgia, 'Times New Roman', serif; /* headings  */
  --font-b:  'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; /* UI / body */
  --font-s:  'Times New Roman', Georgia, serif;  /* description paragraphs */

  /* Motion */
  --ease:  cubic-bezier(.16,1,.3,1);
  --t:     .16s;
  --t-md:  .25s;
}

/* ── FORCE DARK THEME ──────────────────────────────────────── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background-color: var(--bg-0) !important;
  color: var(--tx-1) !important;
}

[data-testid="stHeader"] {
  background: var(--bg-0) !important;
  border-bottom: 1px solid var(--border) !important;
  backdrop-filter: blur(8px) !important;
}

[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child,
section[data-testid="stSidebar"] > div {
  background: var(--bg-1) !important;
  border-right: 1px solid var(--border) !important;
}

/* ── TYPOGRAPHY ────────────────────────────────────────────── */
body, .stApp { font-family: var(--font-b) !important; }

.stApp h1 {
  font-family: var(--font-h) !important;
  font-weight: 700 !important;
  font-size: 2rem !important;
  color: var(--tx-1) !important;
  letter-spacing: -.02em !important;
  line-height: 1.2 !important;
  margin-bottom: .35rem !important;
}
.stApp h2 {
  font-family: var(--font-h) !important;
  font-weight: 600 !important;
  color: var(--tx-1) !important;
  letter-spacing: -.015em !important;
}
.stApp h3 {
  font-family: var(--font-b) !important;
  font-weight: 600 !important;
  font-size: 1rem !important;
  color: var(--tx-1) !important;
}

/* Description / body text → Times New Roman */
.stMarkdown p,
div[data-testid="stMarkdownContainer"] p {
  font-family: var(--font-s) !important;
  color: var(--tx-2) !important;
  line-height: 1.85 !important;
  font-size: 1rem !important;
}

/* Sidebar text always Inter */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
  font-family: var(--font-b) !important;
}

/* ── INPUTS ────────────────────────────────────────────────── */
.stTextInput > label {
  font-family: var(--font-b) !important;
  font-weight: 500 !important;
  font-size: .82rem !important;
  color: var(--tx-2) !important;
  letter-spacing: .01em !important;
  margin-bottom: 5px !important;
}

.stTextInput > div > div > input {
  background: var(--bg-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--tx-1) !important;
  font-family: var(--font-b) !important;
  font-size: .925rem !important;
  padding: 10px 14px !important;
  transition: border-color var(--t) var(--ease),
              box-shadow    var(--t) var(--ease) !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-ring) !important;
  outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: var(--tx-3) !important; }

/* ── SELECTBOX ─────────────────────────────────────────────── */
.stSelectbox > div > div {
  background: var(--bg-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--tx-1) !important;
}

/* ── BUTTONS (main area) ───────────────────────────────────── */
.stButton > button {
  font-family: var(--font-b) !important;
  font-weight: 500 !important;
  font-size: .875rem !important;
  border-radius: var(--r-sm) !important;
  border: 1px solid var(--border) !important;
  background: var(--bg-3) !important;
  color: var(--tx-1) !important;
  transition: background var(--t) var(--ease),
              border-color var(--t) var(--ease),
              box-shadow   var(--t) var(--ease),
              transform    var(--t) var(--ease) !important;
  padding: 7px 16px !important;
}
.stButton > button:hover {
  background: var(--bg-4) !important;
  border-color: var(--border-2) !important;
  transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
  font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
  background: var(--accent-h) !important;
  border-color: var(--accent-h) !important;
  box-shadow: 0 4px 14px var(--accent-ring) !important;
  transform: translateY(-1px) !important;
}

/* ── DOWNLOAD BUTTON ───────────────────────────────────────── */
.stDownloadButton > button {
  font-family: var(--font-b) !important;
  font-weight: 500 !important;
  font-size: .875rem !important;
  border-radius: var(--r-sm) !important;
  background: var(--bg-3) !important;
  border: 1px solid var(--border) !important;
  color: var(--tx-1) !important;
  transition: all var(--t) var(--ease) !important;
}
.stDownloadButton > button:hover {
  background: var(--bg-4) !important;
  border-color: var(--accent) !important;
  color: var(--accent) !important;
  transform: translateY(-1px) !important;
}

/* ── AUTH FORM CARD ────────────────────────────────────────── */
[data-testid="stForm"] {
  background: var(--bg-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  padding: 32px 36px !important;
  box-shadow: var(--shadow-xl) !important;
}

/* ── BORDERED CONTAINERS ───────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
  background: var(--bg-2) !important;
  border-radius: var(--r-lg) !important;
  border: 1px solid var(--border) !important;
  padding: 24px 28px !important;
}

/* ── EXPANDERS ─────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--bg-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  margin-bottom: 4px !important;
  transition: border-color var(--t) !important;
}
[data-testid="stExpander"]:hover { border-color: var(--border-2) !important; }
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
  font-family: var(--font-b) !important;
  font-weight: 500 !important;
  color: var(--tx-1) !important;
}

/* ── SIDEBAR EXPANDERS ─────────────────────────────────────
   The font-size:0 trick on <summary> kills raw text nodes
   (Streamlit injects "arrow_down" as a bare text node).
   We then restore font-size only on real child elements.
   ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stExpander"] {
  background: transparent !important;
  border: none !important;
  border-top: 1px solid var(--border) !important;
  border-radius: 0 !important;
  margin-bottom: 0 !important;
}
/* font-size:0 kills "arrow_down" bare text node */
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  font-size: 0 !important;          /* hides text nodes        */
  display: flex !important;
  align-items: center !important;
  padding: 10px 2px !important;
  min-height: 36px !important;
  cursor: pointer !important;
  user-select: none !important;
}
/* Restore real SVG arrow */
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
  font-size: 14px !important;
  width: 14px !important;
  height: 14px !important;
  min-width: 14px !important;
  flex-shrink: 0 !important;
  color: var(--tx-3) !important;
  fill: var(--tx-3) !important;
  margin-right: 6px !important;
}
/* Restore font-size for the actual label <p> */
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary > div > p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary span.st-emotion-cache-ue6h4q,
[data-testid="stSidebar"] [data-testid="stExpander"] summary div[data-testid] p {
  font-family: var(--font-b) !important;
  font-size: .7rem !important;
  font-weight: 700 !important;
  letter-spacing: .09em !important;
  text-transform: uppercase !important;
  color: var(--tx-3) !important;
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  flex: 1 !important;
  min-width: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover > div > p {
  color: var(--tx-1) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover svg {
  color: var(--tx-1) !important;
  fill: var(--tx-1) !important;
}

/* ── SIDEBAR NAV BUTTONS with Bootstrap Icon pseudo-elements ── */
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: none !important;
  color: var(--tx-2) !important;
  text-align: left !important;
  font-size: .875rem !important;
  padding: 6px 10px 6px 32px !important;   /* left padding for icon */
  border-radius: var(--r-sm) !important;
  font-weight: 400 !important;
  width: 100% !important;
  position: relative !important;
  transition: background var(--t), color var(--t) !important;
}
/* Bootstrap Icon glyphs as ::before — target by button text via data trick.
   We inject the icon into a span inside the button using a wrapper div approach.
   Since we can't set data attrs, we target nth-of-type inside nav expander. */
[data-testid="stSidebar"] .stButton > button::before {
  font-family: "bootstrap-icons" !important;
  font-size: .88rem !important;
  position: absolute !important;
  left: 10px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  color: var(--tx-3) !important;
  transition: color var(--t) !important;
}
/* We target the nav block's buttons in order via the expander wrapper */
/* 1st expander (Navigation) buttons: house, grid, clock-history, camera */
[data-testid="stSidebar"] [data-testid="stExpander"]:nth-of-type(1) .stButton:nth-child(1) button::before { content: "\\F424"; }
[data-testid="stSidebar"] [data-testid="stExpander"]:nth-of-type(1) .stButton:nth-child(2) button::before { content: "\\F4AE"; }
[data-testid="stSidebar"] [data-testid="stExpander"]:nth-of-type(1) .stButton:nth-child(3) button::before { content: "\\F267"; }
[data-testid="stSidebar"] [data-testid="stExpander"]:nth-of-type(1) .stButton:nth-child(4) button::before { content: "\\F228"; }
/* Account expander Sign Out button */
[data-testid="stSidebar"] [data-testid="stExpander"]:nth-of-type(3) .stButton button::before { content: "\\F52B"; }

[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--bg-3) !important;
  color: var(--tx-1) !important;
  transform: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover::before {
  color: var(--accent) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: var(--accent-bg) !important;
  color: var(--accent) !important;
  font-weight: 600 !important;
  border: none !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]::before {
  color: var(--accent) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  background: rgba(240,136,62,.16) !important;
  transform: none !important;
  box-shadow: none !important;
}

/* ── ALERTS ────────────────────────────────────────────────── */
.stAlert {
  border-radius: var(--r) !important;
  font-family: var(--font-b) !important;
  font-size: .875rem !important;
  background: var(--bg-2) !important;
  border: 1px solid var(--border) !important;
}

/* ── DIVIDER ───────────────────────────────────────────────── */
hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 24px 0 !important;
}

/* ── IMAGE ─────────────────────────────────────────────────── */
.stImage img {
  border-radius: var(--r) !important;
  border: 1px solid var(--border) !important;
}

/* ── CAPTION ───────────────────────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {
  font-family: var(--font-b) !important;
  color: var(--tx-3) !important;
  font-size: .78rem !important;
}

/* ── SCROLLBAR ─────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-2); }

/* ── ANIMATIONS ────────────────────────────────────────────── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0);   }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes scaleIn {
  from { opacity: 0; transform: scale(.95); }
  to   { opacity: 1; transform: scale(1);   }
}
@keyframes rotateSlow {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: .55; }
}

/* ════════════════════════════════════════════════════════════
   CUSTOM COMPONENTS
   ════════════════════════════════════════════════════════════ */

/* ── Auth ─────────────────────────────────────────────────── */
.auth-wrap {
  animation: fadeUp .4s var(--ease) both;
}
.auth-logo {
  display: flex; justify-content: center;
  margin-bottom: 20px;
  animation: scaleIn .45s var(--ease) .05s both;
}
.auth-logo svg {
  filter: drop-shadow(0 8px 24px rgba(240,136,62,.35));
}
.auth-title {
  font-family: var(--font-h) !important;
  font-weight: 700 !important;
  font-size: 1.9rem !important;
  color: var(--tx-1) !important;
  text-align: center;
  margin: 0 0 4px !important;
  letter-spacing: -.02em !important;
  animation: fadeUp .4s var(--ease) .1s both;
}
.auth-tagline {
  font-family: var(--font-h) !important;
  font-style: italic !important;
  color: var(--tx-3) !important;
  text-align: center;
  font-size: .93rem !important;
  margin: 0 0 26px !important;
  animation: fadeUp .4s var(--ease) .15s both;
}
.auth-divider {
  display: flex; align-items: center; gap: 12px;
  margin: 18px 0;
}
.auth-divider hr { flex: 1; margin: 0 !important; }
.auth-divider span {
  font-family: var(--font-b);
  font-size: .78rem;
  color: var(--tx-3);
  white-space: nowrap;
}
.auth-switch {
  text-align: center;
  font-family: var(--font-b);
  font-size: .84rem;
  color: var(--tx-3);
  margin-top: 12px;
  animation: fadeIn .35s ease .25s both;
}

/* ── Sidebar brand ────────────────────────────────────────── */
.sidebar-brand {
  display: flex; align-items: center; gap: 10px;
  padding: 4px 0 18px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 14px;
}
.sidebar-brand .brand-name {
  font-family: var(--font-b);
  font-weight: 700; font-size: .95rem; color: var(--tx-1);
}
.sidebar-brand .brand-sub {
  font-family: var(--font-b);
  font-size: .68rem; color: var(--tx-3); margin-top: 1px;
}

/* ── Sidebar user chip ────────────────────────────────────── */
.user-chip {
  display: flex; align-items: center; gap: 10px;
  background: var(--bg-3);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 10px 12px;
  margin-bottom: 14px;
}
.user-chip .avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-d));
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-b); font-weight: 700;
  font-size: .85rem; color: #fff; flex-shrink: 0;
}
.user-chip .uname {
  font-family: var(--font-b) !important;
  font-weight: 600; font-size: .84rem; color: var(--tx-1);
  line-height: 1.2;
}
.user-chip .urole {
  font-family: var(--font-b) !important;
  font-size: .7rem; color: var(--tx-3);
}

/* ── Sidebar nav section label ────────────────────────────── */
.nav-section-lbl {
  font-family: var(--font-b);
  font-size: .68rem; font-weight: 700;
  letter-spacing: .09em; text-transform: uppercase;
  color: var(--tx-3); padding: 12px 2px 5px;
}

/* ── Sidebar recent QR item ───────────────────────────────── */
.rq-item {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 5px 6px; border-radius: var(--r-xs);
  transition: background var(--t);
}
.rq-item:hover { background: var(--bg-3); }
.rq-item .rq-icon { color: var(--accent); font-size: .82rem; flex-shrink: 0; margin-top: 3px; }
.rq-item .rq-name {
  font-family: var(--font-b); font-size: .8rem;
  font-weight: 500; color: var(--tx-2);
  overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; max-width: 145px;
}
.rq-item .rq-date { font-family: var(--font-b); font-size: .68rem; color: var(--tx-3); }

/* ── Hero section ─────────────────────────────────────────── */
.hero { animation: fadeUp .5s var(--ease); padding: 6px 0 20px; }
.hero-eyebrow {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--accent-bg); color: var(--accent);
  border: 1px solid rgba(240,136,62,.22);
  border-radius: 20px; padding: 3px 11px;
  font-family: var(--font-b); font-size: .73rem;
  font-weight: 600; letter-spacing: .07em;
  text-transform: uppercase; margin-bottom: 14px;
}
.hero-title {
  font-family: var(--font-h) !important;
  font-size: clamp(1.85rem, 4vw, 3.1rem) !important;
  font-weight: 700 !important;
  color: var(--tx-1) !important;
  margin: 0 0 14px !important;
  line-height: 1.13 !important;
  letter-spacing: -.025em !important;
}
.hero-title .accent { color: var(--accent); }
.hero-desc {
  font-family: var(--font-s) !important;
  font-size: 1.05rem !important;
  color: var(--tx-2) !important;
  line-height: 1.85 !important;
  max-width: 460px;
}

/* ── Stat cards ───────────────────────────────────────────── */
.stat-card {
  background: var(--bg-2); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 22px 20px;
  text-align: center;
  animation: fadeUp .4s var(--ease);
  transition: border-color var(--t-md), transform var(--t-md), box-shadow var(--t-md);
}
.stat-card:hover {
  border-color: var(--accent);
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(240,136,62,.12);
}
.stat-num {
  font-family: var(--font-h); font-size: 2.4rem;
  font-weight: 700; color: var(--accent);
  line-height: 1; margin-bottom: 7px;
}
.stat-lbl {
  font-family: var(--font-b); font-size: .76rem;
  color: var(--tx-3); font-weight: 500;
  text-transform: uppercase; letter-spacing: .07em;
}

/* ── Generator card ───────────────────────────────────────── */
.gen-card {
  background: var(--bg-2); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 26px 28px;
  animation: fadeUp .45s var(--ease);
}
.gen-card-title {
  font-family: var(--font-h) !important;
  font-size: 1.45rem !important; font-weight: 600 !important;
  color: var(--tx-1) !important; margin-bottom: 18px !important;
  display: flex; align-items: center; gap: 8px;
}

/* ── QR grid card ─────────────────────────────────────────── */
.qr-card-meta { padding: 4px 2px; }
.qr-name {
  font-family: var(--font-b); font-weight: 600;
  font-size: .9rem; color: var(--tx-1); margin-bottom: 4px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.qr-link {
  font-family: var(--font-b); font-size: .77rem; color: var(--tx-3);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.qr-date { font-family: var(--font-b); font-size: .73rem; color: var(--tx-3); margin-top: 5px; }

/* ── PhotoQR in-dev ───────────────────────────────────────── */
.in-dev-wrap {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 58vh; text-align: center;
  animation: fadeUp .5s var(--ease);
}
.in-dev-icon {
  font-size: 3.5rem; color: var(--accent);
  display: block; margin-bottom: 22px;
  animation: rotateSlow 14s linear infinite;
}
.in-dev-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--accent-bg); color: var(--accent);
  border: 1px solid rgba(240,136,62,.26);
  border-radius: 20px; padding: 4px 13px;
  font-family: var(--font-b); font-size: .72rem;
  font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; margin-bottom: 18px;
}
.in-dev-badge::before {
  content: '';
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.8s ease-in-out infinite;
}
.in-dev-title {
  font-family: var(--font-h) !important;
  font-weight: 700 !important; font-size: 2.4rem !important;
  color: var(--tx-1) !important; margin: 0 0 12px !important;
  letter-spacing: -.025em !important;
}
.in-dev-desc {
  font-family: var(--font-s);
  color: var(--tx-2); font-size: 1.05rem;
  line-height: 1.85; max-width: 400px;
}

/* ── Password strength bar ────────────────────────────────── */
.pw-wrap { margin: 5px 0 4px; }
.pw-track { height: 4px; background: var(--bg-4); border-radius: 4px; overflow: hidden; }
.pw-fill  { height: 100%; border-radius: 4px; transition: width .3s ease, background .3s ease; }
.pw-lbl   { font-family: var(--font-b); font-size: .78rem; font-weight: 600; margin-top: 5px; }

/* ── Meta blocks (preview) ────────────────────────────────── */
.meta-block { margin-bottom: 14px; }
.meta-label {
  font-family: var(--font-b); font-size: .72rem; color: var(--tx-3);
  text-transform: uppercase; letter-spacing: .07em; margin-bottom: 3px;
}
.meta-val {
  font-family: var(--font-b); font-weight: 600;
  color: var(--tx-1); font-size: .9rem;
}
.meta-val-sm {
  font-family: var(--font-b); font-size: .84rem;
  color: var(--tx-2); word-break: break-all;
}

/* ── Empty state ─────────────────────────────────────────── */
.empty-state {
  text-align: center; padding: 60px 24px;
  animation: fadeIn .4s ease;
}
.empty-icon { font-size: 2.6rem; color: var(--border-2); display: block; margin-bottom: 14px; }
.empty-text { font-family: var(--font-b); color: var(--tx-3); font-size: .88rem; margin-top: 6px; }

/* ── Section count chip ───────────────────────────────────── */
.count-chip {
  display: inline-block; background: var(--bg-3);
  border: 1px solid var(--border); border-radius: 20px;
  padding: 1px 9px; font-family: var(--font-b);
  font-size: .74rem; color: var(--tx-3); font-weight: 500;
  vertical-align: middle; margin-left: 8px;
}

/* ── Page header ─────────────────────────────────────────── */
.page-header {
  padding: 4px 0 20px;
  animation: fadeUp .35s var(--ease);
}
.page-header-title {
  font-family: var(--font-h) !important;
  font-size: 1.85rem !important; font-weight: 700 !important;
  color: var(--tx-1) !important; margin: 0 !important;
  letter-spacing: -.02em !important;
}
.page-header-sub {
  font-family: var(--font-s);
  color: var(--tx-2); font-size: .98rem;
  margin-top: 5px; line-height: 1.7;
}

/* ── HIDE STREAMLIT CHROME ───────────────────────────────── */
#MainMenu { display: none !important; }
footer    { display: none !important; }
[data-testid="stDecoration"]              { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* Fix: sidebar collapse toggle button leaking icon name text */
[data-testid="stSidebar"] button[kind="header"] { display: none !important; }

/* Fix: expander summary overflow so raw icon-name text doesn't bleed
   into the label. Streamlit injects a <span> with the Material icon
   string ("keyboard_double_arrow_right") — we clip it. */
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  overflow: hidden !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary > div > p {
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

/* ── MOBILE ──────────────────────────────────────────────── */
@media (max-width: 768px) {
  [data-testid="stForm"] { padding: 22px 16px !important; }
  .hero-title { font-size: 1.75rem !important; }
  .stat-num   { font-size: 2rem !important; }
  .in-dev-title { font-size: 1.85rem !important; }
  .gen-card { padding: 18px 16px; }
  .auth-title { font-size: 1.6rem !important; }
  .in-dev-wrap { min-height: 48vh; padding: 0 16px; }
  div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 18px 16px !important; }
  .page-header-title { font-size: 1.5rem !important; }
}
</style>
"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── SVG assets ──────────────────────────────────────────────────────────────────
QR_LOGO_SVG = """
<svg width="64" height="64" viewBox="0 0 68 68" xmlns="http://www.w3.org/2000/svg">
  <rect width="68" height="68" rx="16" fill="#f0883e"/>
  <rect x="8"  y="8"  width="22" height="22" rx="4.5" fill="white"/>
  <rect x="12" y="12" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="38" y="8"  width="22" height="22" rx="4.5" fill="white"/>
  <rect x="42" y="12" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="8"  y="38" width="22" height="22" rx="4.5" fill="white"/>
  <rect x="12" y="42" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="38" y="38" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="46" y="38" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="54" y="38" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="38" y="46" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="50" y="46" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="54" y="54" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="38" y="54" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="46" y="54" width="6" height="6" rx="1.5" fill="white"/>
</svg>"""

QR_LOGO_SM = """
<svg width="26" height="26" viewBox="0 0 68 68" xmlns="http://www.w3.org/2000/svg">
  <rect width="68" height="68" rx="16" fill="#f0883e"/>
  <rect x="8"  y="8"  width="22" height="22" rx="4.5" fill="white"/>
  <rect x="12" y="12" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="38" y="8"  width="22" height="22" rx="4.5" fill="white"/>
  <rect x="42" y="12" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="8"  y="38" width="22" height="22" rx="4.5" fill="white"/>
  <rect x="12" y="42" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="38" y="38" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="46" y="38" width="6" height="6" rx="1.5" fill="white"/>
</svg>"""


# ═══════════════════════════════════════════════════════════════
# DATABASE LAYER
# ═══════════════════════════════════════════════════════════════
def get_connection():
    return psycopg2.connect(
        dbname="postgres", user="postgres",
        password="group2", host="localhost", port="5432",
    )

@st.cache_resource(show_spinner=False)
def init_db():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         SERIAL PRIMARY KEY,
            username   VARCHAR(100) UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name       VARCHAR(200) NOT NULL,
            qr_data    TEXT NOT NULL,
            qr_image   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit(); cur.close(); conn.close()
    return True

init_db()

# ── QR list with 30-second TTL cache ───────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _fetch_qr_codes(username: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT qc.id, qc.name, qc.qr_data, qc.qr_image, qc.created_at
        FROM qr_codes qc
        JOIN users u ON qc.user_id = u.id
        WHERE u.username = %s
        ORDER BY qc.created_at DESC
    """, (username,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows

def get_user_qr_codes(username: str):
    return _fetch_qr_codes(username)

def _bust_cache():
    _fetch_qr_codes.clear()

def save_qr_to_db(username, name, qr_data, qr_image_b64):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    if user:
        cur.execute(
            "INSERT INTO qr_codes (user_id, name, qr_data, qr_image) VALUES (%s,%s,%s,%s)",
            (user[0], name, qr_data, qr_image_b64),
        )
        conn.commit()
    cur.close(); conn.close()
    _bust_cache()

def delete_qr_from_db(qr_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM qr_codes WHERE id = %s", (qr_id,))
    conn.commit(); cur.close(); conn.close()
    _bust_cache()

# ── Auth helpers ────────────────────────────────────────────────────────────────
def hash_password(pw):    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def verify_password(pw, h): return bcrypt.checkpw(pw.encode(), h.encode())

# ── QR generation (content-addressed cache — same URL → same PNG) ───────────────
@st.cache_data(show_spinner=False)
def generate_qr_bytes(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ── Lottie loader ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# PASSWORD STRENGTH  (debounced via session-state timestamps)
# ═══════════════════════════════════════════════════════════════
def check_password_strength(password: str):
    checks = [
        (len(password) >= 8,                                                  "At least 8 characters"),
        (bool(re.search(r'[A-Z]', password)),                                 "At least one uppercase letter (A–Z)"),
        (bool(re.search(r'[a-z]', password)),                                 "At least one lowercase letter (a–z)"),
        (bool(re.search(r'\d', password)),                                    "At least one number (0–9)"),
        (bool(re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\\/_\-+=~`]', password)), "At least one special character"),
    ]
    score   = sum(1 for ok, _ in checks if ok)
    missing = [msg for ok, msg in checks if not ok]
    return score, missing

_STRENGTH = {
    0: ("No input",    "#444c56",  0),
    1: ("Very Weak",   "#f85149", 20),
    2: ("Weak",        "#f0883e", 40),
    3: ("Moderate",    "#d29922", 60),
    4: ("Strong",      "#3fb950", 80),
    5: ("Very Strong", "#2ea043",100),
}

def render_strength_bar(password: str, db_key: str = "pw"):
    if not password:
        return
    cache_key = f"_pw_cache_{db_key}"
    cached    = st.session_state.get(cache_key)
    if cached is None or cached["pw"] != password:
        score, missing = check_password_strength(password)
        st.session_state[cache_key] = {"pw": password, "score": score, "missing": missing}
    else:
        score, missing = cached["score"], cached["missing"]

    label, color, pct = _STRENGTH.get(score, _STRENGTH[0])
    st.markdown(f"""
    <div class="pw-wrap">
        <div class="pw-track">
            <div class="pw-fill" style="width:{pct}%;background:{color};"></div>
        </div>
        <p class="pw-lbl" style="color:{color};">Strength: {label}</p>
    </div>
    """, unsafe_allow_html=True)

    if missing:
        with st.expander("Requirements not yet met", expanded=(score < 3)):
            for m in missing:
                st.markdown(
                    f'<i class="bi bi-x-circle-fill" style="color:#f85149;margin-right:6px;"></i>{m}',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            '<i class="bi bi-check-circle-fill" style="color:#3fb950;margin-right:6px;"></i>'
            '**All requirements met!**',
            unsafe_allow_html=True,
        )


# ── Input debounce helper ───────────────────────────────────────────────────────
def _debounce_input(key: str, value: str, delay: float = 0.45) -> bool:
    """Returns True once `value` has been stable for `delay` seconds."""
    now          = time.time()
    val_key      = f"_dbi_v_{key}"
    time_key     = f"_dbi_t_{key}"
    last_val     = st.session_state.get(val_key, "")
    last_changed = st.session_state.get(time_key, 0)
    if value != last_val:
        st.session_state[val_key]  = value
        st.session_state[time_key] = now
        return False
    return (now - last_changed) >= delay


# ═══════════════════════════════════════════════════════════════
# SESSION STATE DEFAULTS
# ═══════════════════════════════════════════════════════════════
_DEFAULTS = {
    "logged_in":    False,
    "username":     "",
    "active_tab":   "Home",
    "auth_mode":    "Login",
    "qr_bytes":     None,
    "qr_data_val":  "",
    "qr_name_val":  "",
    "show_save_ui": False,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

def _clear_preview():
    st.session_state["show_save_ui"] = False
    st.session_state["qr_bytes"]     = None
    st.session_state["qr_data_val"]  = ""
    st.session_state["qr_name_val"]  = ""


# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # ── Brand ──────────────────────────────────────────────────────────────
        st.markdown(f"""
        <div class="sidebar-brand">
            {QR_LOGO_SM}
            <div>
                <div class="brand-name">QR Studio</div>
                <div class="brand-sub">Group 2 · 2025</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state["logged_in"]:
            return

        # ── User chip ──────────────────────────────────────────────────────────
        initial = st.session_state["username"][0].upper()
        st.markdown(f"""
        <div class="user-chip">
            <div class="avatar">{initial}</div>
            <div>
                <div class="uname">{st.session_state["username"]}</div>
                <div class="urole">Member</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Navigation dropdown ────────────────────────────────────────────────
        with st.expander("Navigation", expanded=True):
            nav_items = [
                ("Home",        "Home"),
                ("My QR Codes", "MyQR"),
                ("History",     "History"),
                ("PhotoQR",     "PhotoQR"),
            ]
            for label, key in nav_items:
                active = st.session_state["active_tab"] == key
                if st.button(
                    label,
                    key=f"nav_{key}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                ):
                    if st.session_state["active_tab"] != key:
                        st.session_state["active_tab"] = key
                        _clear_preview()
                        st.rerun()

        # ── Recent QR codes dropdown ───────────────────────────────────────────
        with st.expander("Recent QR Codes"):
            recent = get_user_qr_codes(st.session_state["username"])[:5]
            if recent:
                for _, name, _, _, ts in recent:
                    safe = (name[:21] + "…") if len(name) > 21 else name
                    st.markdown(f"""
                    <div class="rq-item">
                        <i class="bi bi-qr-code rq-icon"></i>
                        <div>
                            <div class="rq-name">{safe}</div>
                            <div class="rq-date">{ts.strftime("%b %d, %Y")}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("Nothing saved yet.")

        # ── Account dropdown ───────────────────────────────────────────────────
        with st.expander("Account"):
            st.caption(f"Signed in as **{st.session_state['username']}**")
            st.write("")
            if st.button(
                "Sign Out",
                use_container_width=True,
            ):
                for k, v in _DEFAULTS.items():
                    st.session_state[k] = v
                st.rerun()

render_sidebar()


# ═══════════════════════════════════════════════════════════════
# AUTH PAGES
# ═══════════════════════════════════════════════════════════════
_HIDE_SIDEBAR_CSS = """
<style>
[data-testid="stSidebar"]                { display: none !important; }
[data-testid="stSidebarCollapsedControl"]{ display: none !important; }
</style>
"""

def render_login():
    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)

        # Logo
        st.markdown(f'<div class="auth-logo">{QR_LOGO_SVG}</div>', unsafe_allow_html=True)
        # Title + tagline
        st.markdown('<div class="auth-title">QR Studio</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-tagline">A QR code, anytime, anywhere.</div>',
            unsafe_allow_html=True,
        )

        # Form card
        with st.form("login_form", clear_on_submit=False):
            username  = st.text_input("Username", placeholder="Enter your username")
            password  = st.text_input("Password", type="password", placeholder="••••••••")
            st.write("")
            submitted = st.form_submit_button(
                "Sign In",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not username.strip() or not password:
                st.error("Please enter your username and password.")
            else:
                conn = get_connection(); cur = conn.cursor()
                cur.execute("SELECT password FROM users WHERE username = %s", (username.strip(),))
                result = cur.fetchone()
                cur.close(); conn.close()
                if result and verify_password(password, result[0]):
                    st.session_state["logged_in"] = True
                    st.session_state["username"]   = username.strip()
                    st.session_state["active_tab"] = "Home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        # Switch to signup
        st.markdown(
            '<div class="auth-switch">Don\'t have an account?</div>',
            unsafe_allow_html=True,
        )
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Create an account →", use_container_width=True, key="go_signup"):
                st.session_state["auth_mode"] = "Signup"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def render_signup():
    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)

        st.markdown(f'<div class="auth-logo">{QR_LOGO_SVG}</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">Create Account</div>',  unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-tagline">Join QR Studio today.</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            new_user = st.text_input("Username",         placeholder="Choose a username",  key="su_user")
            new_pass = st.text_input("Password",         type="password",
                                     placeholder="••••••••", key="su_pass")
            render_strength_bar(new_pass or "", db_key="signup")
            confirm  = st.text_input("Confirm Password", type="password",
                                     placeholder="••••••••", key="su_confirm")
            st.write("")
            reg_btn = st.button(
                "Create Account",
                type="primary",
                use_container_width=True,
            )

        if reg_btn:
            score, _ = check_password_strength(new_pass or "")
            if not new_user.strip():
                st.error("Please enter a username.")
            elif not new_pass:
                st.error("Please enter a password.")
            elif score < 3:
                st.error(
                    "Password is too weak — please meet at least 3 of the 5 requirements.",
                )
            elif new_pass != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    conn = get_connection(); cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users(username, password) VALUES (%s,%s)",
                        (new_user.strip(), hash_password(new_pass)),
                    )
                    conn.commit(); cur.close(); conn.close()
                    st.success(
                        "Account created! Redirecting to sign in…",
                    )
                    time.sleep(1.2)
                    st.session_state["auth_mode"] = "Login"
                    st.rerun()
                except Exception as e:
                    st.error(f"Database error: {e}")

        st.markdown(
            '<div class="auth-switch">Already have an account?</div>',
            unsafe_allow_html=True,
        )
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Sign in instead →", use_container_width=True, key="go_login"):
                st.session_state["auth_mode"] = "Login"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# MAIN TABS
# ═══════════════════════════════════════════════════════════════

def render_home():
    lottie_anim = load_lottieurl(
        "https://lottie.host/6a3ab8e3-b3c8-4e40-ad93-b7adfdc4a3eb/Ql1QsdyMTr.json"
    )
    qr_count = len(get_user_qr_codes(st.session_state["username"]))

    # ── Hero ──────────────────────────────────────────────────────────────────
    left_h, right_h = st.columns([3, 2], gap="large")
    with left_h:
        st.markdown(f"""
        <div class="hero">
            <div class="hero-eyebrow">
                <i class="bi bi-lightning-charge-fill"></i>&nbsp;QR Studio
            </div>
            <div class="hero-title">
                Generate QR codes<br>
                <span class="accent">in seconds.</span>
            </div>
            <p class="hero-desc">
                A fast, elegant QR code generator built for the modern web.
                Create, save, and manage your QR codes — for links, contacts,
                or anything in between. Built with Python &amp; Streamlit.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with right_h:
        if HAS_LOTTIE and lottie_anim:
            st_lottie(lottie_anim, height=220, key="hero_lottie")
        else:
            st.markdown(
                f'<div style="display:flex;justify-content:center;'
                f'align-items:center;height:220px;">{QR_LOGO_SVG}</div>',
                unsafe_allow_html=True,
            )

    # ── Stats row ─────────────────────────────────────────────────────────────
    st.markdown("---")
    s1, s2, s3 = st.columns(3)
    tiles = [
        (str(qr_count), "QR Codes Saved"),
        ("∞",           "Links Supported"),
        ("PNG",         "Export Format"),
    ]
    for col, (num, lbl) in zip([s1, s2, s3], tiles):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-num">{num}</div>
                <div class="stat-lbl">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    # ── Generator card ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="gen-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="gen-card-title">'
        '<i class="bi bi-qr-code-scan" style="color:var(--accent);"></i>'
        ' Generate a QR Code'
        '</div>',
        unsafe_allow_html=True,
    )

    inp1, inp2 = st.columns(2)
    with inp1:
        qr_name = st.text_input(
            "Name", placeholder="e.g. My GitHub Profile", key="home_qr_name"
        )
    with inp2:
        qr_link = st.text_input(
            "Link / Text", placeholder="https://example.com", key="home_qr_link"
        )

    g_col, _ = st.columns([1, 3])
    with g_col:
        gen_btn = st.button(
            "Generate",
            type="primary",
            use_container_width=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Debounced validation feedback
    if qr_link and not _debounce_input("home_link", qr_link, delay=0.5):
        pass  # still typing

    if gen_btn:
        if not qr_name.strip():
            st.warning("Please enter a name for your QR code.")
        elif not qr_link.strip():
            st.warning("Please enter a link or text.")
        else:
            st.session_state["qr_bytes"]     = generate_qr_bytes(qr_link.strip())
            st.session_state["qr_data_val"]  = qr_link.strip()
            st.session_state["qr_name_val"]  = qr_name.strip()
            st.session_state["show_save_ui"] = True

    # ── Preview & save ────────────────────────────────────────────────────────
    if st.session_state["show_save_ui"] and st.session_state["qr_bytes"]:
        st.markdown("---")
        with st.container(border=True):
            prev_col, act_col = st.columns([1, 2], gap="large")

            with prev_col:
                st.image(
                    st.session_state["qr_bytes"],
                    caption=st.session_state["qr_name_val"],
                    width=200,
                )

            with act_col:
                st.markdown(f"""
                <div class="meta-block">
                    <div class="meta-label">Name</div>
                    <div class="meta-val">{st.session_state["qr_name_val"]}</div>
                </div>
                <div class="meta-block">
                    <div class="meta-label">Link / Text</div>
                    <div class="meta-val-sm">{st.session_state["qr_data_val"]}</div>
                </div>
                """, unsafe_allow_html=True)

                save_col, cancel_col = st.columns(2)
                with save_col:
                    if st.button(
                        "Save QR Code",
                        type="primary",
                        use_container_width=True,
                    ):
                        b64 = base64.b64encode(st.session_state["qr_bytes"]).decode()
                        save_qr_to_db(
                            st.session_state["username"],
                            st.session_state["qr_name_val"],
                            st.session_state["qr_data_val"],
                            b64,
                        )
                        st.success(
                            f'Saved **{st.session_state["qr_name_val"]}**!',
                        )
                        _clear_preview()
                        st.rerun()
                with cancel_col:
                    if st.button("Discard", use_container_width=True):
                        _clear_preview()
                        st.rerun()


def render_my_qr():
    qr_list  = get_user_qr_codes(st.session_state["username"])
    count    = len(qr_list)

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">
            My QR Codes
            <span class="count-chip">{count}</span>
        </div>
        <div class="page-header-sub">
            Your saved QR codes — download or remove them at any time.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    if not qr_list:
        st.markdown("""
        <div class="empty-state">
            <i class="bi bi-inbox empty-icon"></i>
            <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">
                Nothing here yet
            </h3>
            <p class="empty-text">
                Head over to <strong>Home</strong> to generate your first QR code.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    cols = st.columns(3)
    for idx, (qr_id, name, qr_data, qr_img_b64, created_at) in enumerate(qr_list):
        qr_bytes   = base64.b64decode(qr_img_b64)
        short_link = qr_data if len(qr_data) <= 40 else qr_data[:37] + "…"

        with cols[idx % 3]:
            with st.container(border=True):
                st.image(qr_bytes, use_container_width=True)
                st.markdown(f"""
                <div class="qr-card-meta">
                    <div class="qr-name">{name}</div>
                    <div class="qr-link">
                        <i class="bi bi-link-45deg"></i> {short_link}
                    </div>
                    <div class="qr-date">
                        <i class="bi bi-calendar3"></i>
                        {created_at.strftime("%b %d, %Y  %H:%M")}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.write("")
                dl_c, del_c = st.columns(2)
                with dl_c:
                    st.download_button(
                        "Download",
                        data=qr_bytes,
                        file_name=f"{name}.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"myqr_dl_{qr_id}",
                    )
                with del_c:
                    if st.button(
                        "Delete",
                        key=f"myqr_del_{qr_id}",
                        use_container_width=True,
                    ):
                        delete_qr_from_db(qr_id)
                        st.rerun()


def render_history():
    qr_list = get_user_qr_codes(st.session_state["username"])
    count   = len(qr_list)

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">
            History
            <span class="count-chip">{count}</span>
        </div>
        <div class="page-header-sub">
            A full log of every QR code you've saved — newest first.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    if not qr_list:
        st.markdown("""
        <div class="empty-state">
            <i class="bi bi-clock-history empty-icon"></i>
            <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">
                No history yet
            </h3>
            <p class="empty-text">
                Generate your first QR code from <strong>Home</strong>.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    for qr_id, name, qr_data, qr_img_b64, created_at in qr_list:
        qr_bytes = base64.b64decode(qr_img_b64)
        with st.expander(
            f"{name}  ·  {created_at.strftime('%b %d, %Y  %H:%M')}",
            expanded=False,
        ):
            l_col, r_col = st.columns([1, 2], gap="large")
            with l_col:
                st.image(qr_bytes, width=148)
            with r_col:
                st.markdown(f"""
                <div class="meta-block">
                    <div class="meta-label">Name</div>
                    <div class="meta-val">{name}</div>
                </div>
                <div class="meta-block">
                    <div class="meta-label">Link / Text</div>
                    <div class="meta-val-sm">{qr_data}</div>
                </div>
                <div class="meta-block">
                    <div class="meta-label">Created</div>
                    <div class="meta-val-sm">{created_at.strftime("%B %d, %Y at %H:%M")}</div>
                </div>
                """, unsafe_allow_html=True)

                dl2, del2 = st.columns(2)
                with dl2:
                    st.download_button(
                        "Download",
                        data=qr_bytes,
                        file_name=f"{name}.png",
                        mime="image/png",
                        key=f"hist_dl_{qr_id}",
                    )
                with del2:
                    if st.button(
                        "Delete",
                        key=f"hist_del_{qr_id}",
                    ):
                        delete_qr_from_db(qr_id)
                        st.rerun()


def render_photo_qr():
    st.markdown("""
    <div class="page-header" style="padding-bottom:8px;">
        <div class="page-header-title">PhotoQR</div>
        <div class="page-header-sub">
            Embed QR codes directly into your photos and images.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("""
    <div class="in-dev-wrap">
        <i class="bi bi-camera in-dev-icon"></i>
        <div class="in-dev-badge">In Development</div>
        <div class="in-dev-title">PhotoQR</div>
        <p class="in-dev-desc">
            PhotoQR will let you embed QR codes directly into photos and images —
            beautiful, scannable, and seamlessly integrated into any picture.
            Something great is coming. Stay tuned.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════
if not st.session_state["logged_in"]:
    if st.session_state["auth_mode"] == "Signup":
        render_signup()
    else:
        render_login()
else:
    _tab = st.session_state["active_tab"]
    if   _tab == "Home":    render_home()
    elif _tab == "MyQR":    render_my_qr()
    elif _tab == "History": render_history()
    elif _tab == "PhotoQR": render_photo_qr()