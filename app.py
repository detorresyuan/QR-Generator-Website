import streamlit as st
import streamlit.components.v1 as _st_components
import psycopg2
import bcrypt
import requests
import qrcode
import io
import base64
import re
import time
import html
import os
from datetime import datetime

try:
    from streamlit_lottie import st_lottie
    HAS_LOTTIE = True
except ImportError:
    HAS_LOTTIE = False

st.set_page_config(
    page_title="QR Studio",
    page_icon="🔲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# LOGO LOADING  (PNG → base64, used everywhere in place of SVG fallback)
# ══════════════════════════════════════════════════════════════════════════════
_LOGO_B64  = ""
_LOGO_MIME = "image/png"
_logo_paths = [
    os.path.join(os.path.dirname(__file__), "Logo website.png"),
    os.path.join(os.path.dirname(__file__), "Logo_website.png"),
    "/mnt/user-data/uploads/Logo_website.png",
]
for _path in _logo_paths:
    try:
        if not os.path.isfile(_path):
            continue
        with open(_path, "rb") as _lf:
            _raw = _lf.read()
            _LOGO_B64 = base64.b64encode(_raw).decode()
            _LOGO_MIME = "image/jpeg" if _raw[:3] == b"\xff\xd8\xff" else "image/png"
        break
    except OSError:
        continue

def _logo_tag(size: int = 32, extra_style: str = "") -> str:
    """Return <img> logo tag; falls back to inline SVG if PNG unavailable."""
    if _LOGO_B64:
        r = max(4, size // 6)
        return (
            f'<img src="data:{_LOGO_MIME};base64,{_LOGO_B64}" '
            f'width="{size}" height="{size}" '
            f'style="border-radius:{r}px;object-fit:contain;vertical-align:middle;{extra_style}" '
            f'alt="QR Studio">'
        )
    # SVG fallback
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 68 68" xmlns="http://www.w3.org/2000/svg">
  <rect width="68" height="68" rx="16" fill="#f0883e"/>
  <rect x="8" y="8" width="22" height="22" rx="4.5" fill="white"/>
  <rect x="12" y="12" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="38" y="8" width="22" height="22" rx="4.5" fill="white"/>
  <rect x="42" y="12" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="8" y="38" width="22" height="22" rx="4.5" fill="white"/>
  <rect x="12" y="42" width="14" height="14" rx="2.5" fill="#f0883e"/>
  <rect x="38" y="38" width="6" height="6" rx="1.5" fill="white"/>
  <rect x="46" y="38" width="6" height="6" rx="1.5" fill="white"/>
</svg>"""

# ══════════════════════════════════════════════════════════════════════════════
# FONTS + ICON LINKS
# ══════════════════════════════════════════════════════════════════════════════
GLOBAL_CSS_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
"""

def _load_css() -> str:
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    try:
        with open(css_path, encoding="utf-8-sig") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""

st.markdown(GLOBAL_CSS_LINKS, unsafe_allow_html=True)
st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SVG FALLBACKS (kept for loading overlay only)
# ══════════════════════════════════════════════════════════════════════════════
_LOADER_SVG = """<svg width="64" height="64" viewBox="0 0 68 68" xmlns="http://www.w3.org/2000/svg">
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

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL STYLE + LOADING OVERLAY
# ══════════════════════════════════════════════════════════════════════════════
GLOBAL_STYLE = """
<style>
[data-testid="stSidebarCollapsedControl"]  { display: flex !important; }
[data-testid="stSidebarCollapseButton"]    { display: flex !important; }
[data-testid="stSidebar"] button[kind="header"]                        { display: flex !important; }
[data-testid="stSidebar"] [data-testid="stBaseButton-headerNoPadding"] { display: flex !important; }
[data-testid="stSidebar"] > div > div > div:first-child > button       { display: flex !important; }
[data-testid="stSidebarCollapseButton"] p,
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stSidebar"] button[kind="header"] p,
[data-testid="stSidebar"] button[kind="header"] span,
[data-testid="stBaseButton-headerNoPadding"] p,
[data-testid="stBaseButton-headerNoPadding"] span { display: none !important; }

button[kind="primary"],
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span,
[data-testid="stFormSubmitButton"] > button,
[data-testid="stFormSubmitButton"] > button p,
[data-testid="stFormSubmitButton"] > button span {
    color: #ffffff !important;
    font-weight: 600 !important;
}
button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    color: #ffffff !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary > div > p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary div[data-testid] p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary span {
    color: #f0883e !important;
    font-size: .7rem !important;
    font-weight: 700 !important;
    letter-spacing: .09em !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
    color: #f0883e !important; fill: #f0883e !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover > div > p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover span {
    color: #f5a461 !important;
}

.qrs-footer {
    background: #0d1117;
    border-top: 1px solid rgba(255,255,255,0.08);
    font-family: 'Inter', sans-serif;
    padding: 36px 48px 20px;
    margin-top: 48px;
}
.qrs-footer-top {
    display: flex; justify-content: space-between;
    align-items: flex-start; gap: 32px; flex-wrap: wrap;
    padding-bottom: 24px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 16px;
}
.qrs-footer-brand { max-width: 240px; }
.qrs-footer-brand-name {
    font-size: 1.1rem; font-weight: 700;
    color: #e6edf3; margin-bottom: 8px; letter-spacing: -.01em;
}
.qrs-footer-brand-name span { color: #f0883e; }
.qrs-footer-brand-desc { font-size: .78rem; color: #6e7681; line-height: 1.65; }
.qrs-footer-cols { display: flex; gap: 52px; flex-wrap: wrap; }
.qrs-footer-col-title {
    font-size: .68rem; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: #f0883e; margin-bottom: 12px;
}
.qrs-footer-col a {
    display: block; font-size: .79rem; color: #6e7681;
    text-decoration: none; margin-bottom: 7px; transition: color .15s;
}
.qrs-footer-col a:hover { color: #f0883e; }
.qrs-footer-bottom {
    display: flex; justify-content: space-between;
    align-items: center; flex-wrap: wrap; gap: 8px;
}
.qrs-footer-copy { font-size: .73rem; color: #444c56; }
.qrs-footer-version { font-size: .73rem; color: #444c56; }

#qrs-loading-overlay {
    display: none; position: fixed; inset: 0;
    background: rgba(13,17,23,0.92); backdrop-filter: blur(8px);
    z-index: 99999; flex-direction: column;
    align-items: center; justify-content: center; gap: 20px;
}
#qrs-loading-overlay.active { display: flex; }
.qrs-loader-logo { animation: loader-pulse 1.4s ease-in-out infinite; }
.qrs-loader-dots { display: flex; gap: 8px; }
.qrs-loader-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #f0883e;
    animation: loader-bounce 1.2s ease-in-out infinite;
}
.qrs-loader-dot:nth-child(2) { animation-delay: .15s; }
.qrs-loader-dot:nth-child(3) { animation-delay: .3s; }
@keyframes loader-pulse {
    0%,100%{ opacity:1; transform:scale(1); }
    50%{ opacity:.6; transform:scale(.92); }
}
@keyframes loader-bounce {
    0%,80%,100%{ transform:translateY(0); opacity:.5; }
    40%{ transform:translateY(-10px); opacity:1; }
}

/* password strength bar */
.pw-wrap { margin: 4px 0 8px; }
.pw-track {
    height: 5px; border-radius: 3px;
    background: rgba(255,255,255,0.08); overflow: hidden; margin-bottom: 4px;
}
.pw-fill { height: 100%; border-radius: 3px; transition: width .35s, background .35s; }
.pw-lbl { font-family:'Inter',sans-serif; font-size:.74rem; margin:0; }

@media (max-width: 900px) {
    .qrs-footer { padding: 28px 20px 16px; }
    .qrs-footer-cols { gap: 28px; }
    .qrs-footer-top { flex-direction: column; }
}
</style>

<div id="qrs-loading-overlay">
    <div class="qrs-loader-logo">""" + _LOADER_SVG + """</div>
    <div class="qrs-loader-dots">
        <div class="qrs-loader-dot"></div>
        <div class="qrs-loader-dot"></div>
        <div class="qrs-loader-dot"></div>
    </div>
</div>
<script>
(function(){
    function showLoader(){
        var ov=document.getElementById('qrs-loading-overlay');
        if(ov){ov.classList.add('active');}
    }
    function attachListeners(){
        document.querySelectorAll('button[kind="primary"],[data-testid="stFormSubmitButton"] button').forEach(function(btn){
            if(!btn.dataset.loaderAttached){
                btn.dataset.loaderAttached='1';
                btn.addEventListener('click',showLoader);
            }
        });
    }
    attachListeners();
    var obs=new MutationObserver(function(){attachListeners();});
    obs.observe(document.body,{childList:true,subtree:true});
    var mainObs=new MutationObserver(function(){
        var ov=document.getElementById('qrs-loading-overlay');
        if(ov){ov.classList.remove('active');}
    });
    mainObs.observe(document.body,{childList:true,subtree:false});
})();
</script>
"""

FOOTER_HTML = """<div class="qrs-footer">
    <div class="qrs-footer-top">
        <div class="qrs-footer-brand">
            <div class="qrs-footer-brand-name"><span>QR</span> Studio</div>
            <div class="qrs-footer-brand-desc">
                A fast, elegant QR code generator built for the modern web.
                Create, save, and share QR codes for links, photos, and more.
            </div>
        </div>
        <div class="qrs-footer-cols">
            <div class="qrs-footer-col">
                <div class="qrs-footer-col-title">Features</div>
                <a href="#" onclick="return false;">QR Generator</a>
                <a href="#" onclick="return false;">PhotoQR</a>
                <a href="#" onclick="return false;">QcaRd</a>
                <a href="#" onclick="return false;">QR History</a>
            </div>
            <div class="qrs-footer-col">
                <div class="qrs-footer-col-title">How It Works</div>
                <a href="#" onclick="return false;">Create Account</a>
                <a href="#" onclick="return false;">Generate a QR</a>
                <a href="#" onclick="return false;">Share &amp; Scan</a>
                <a href="#" onclick="return false;">Private PhotoQR</a>
            </div>
            <div class="qrs-footer-col">
                <div class="qrs-footer-col-title">Project</div>
                <a href="#" onclick="return false;">Group 2 &middot; 2026</a>
                <a href="https://streamlit.io" target="_blank" rel="noopener">Built with Streamlit</a>
                <a href="https://www.postgresql.org" target="_blank" rel="noopener">PostgreSQL Backend</a>
                <a href="https://ubuntu.com" target="_blank" rel="noopener">Ubuntu Server</a>
            </div>
        </div>
    </div>
    <div class="qrs-footer-bottom">
        <div class="qrs-footer-copy">
            &copy; 2026 QR Studio &nbsp;&middot;&nbsp; Group 2 &nbsp;&middot;&nbsp; All rights reserved.
        </div>
        <div class="qrs-footer-version">v3.0</div>
    </div>
</div>"""

def inject_global():
    st.markdown(GLOBAL_STYLE, unsafe_allow_html=True)

def render_footer():
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════
def get_connection():
    return psycopg2.connect(
        dbname="postgres", user="postgres",
        password="group2", host="localhost", port="5432",
    )

@st.cache_resource(show_spinner=False)
def init_db():
    conn = get_connection(); cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS qr_codes (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(200) NOT NULL,
        qr_data TEXT NOT NULL,
        qr_image TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS photo_qr (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        photo_data TEXT NOT NULL,
        caption VARCHAR(300) DEFAULT '',
        visibility VARCHAR(10) DEFAULT 'public'
            CHECK (visibility IN ('public','private')),
        pin_hash TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── New: QcaRd (business card) ─────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS qcards (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
        full_name  VARCHAR(200) DEFAULT '',
        job_title  VARCHAR(200) DEFAULT '',
        company    VARCHAR(200) DEFAULT '',
        bio        TEXT        DEFAULT '',
        email      VARCHAR(200) DEFAULT '',
        phone      VARCHAR(100) DEFAULT '',
        address    TEXT        DEFAULT '',
        website    VARCHAR(500) DEFAULT '',
        linkedin   VARCHAR(500) DEFAULT '',
        github     VARCHAR(500) DEFAULT '',
        twitter    VARCHAR(500) DEFAULT '',
        custom_link_label VARCHAR(200) DEFAULT '',
        custom_link_url   VARCHAR(500) DEFAULT '',
        profile_photo TEXT DEFAULT NULL,
        bg_photo      TEXT DEFAULT NULL,
        accent_color  VARCHAR(100) DEFAULT '#f0883e',
        scan_count    INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── Migration: safely add any columns missing from a pre-existing qcards table
    _qcard_cols_to_add = [
        ("job_title",         "VARCHAR(200) DEFAULT ''"),
        ("company",           "VARCHAR(200) DEFAULT ''"),
        ("bio",               "TEXT DEFAULT ''"),
        ("email",             "VARCHAR(200) DEFAULT ''"),
        ("phone",             "VARCHAR(100) DEFAULT ''"),
        ("address",           "TEXT DEFAULT ''"),
        ("website",           "VARCHAR(500) DEFAULT ''"),
        ("linkedin",          "VARCHAR(500) DEFAULT ''"),
        ("github",            "VARCHAR(500) DEFAULT ''"),
        ("twitter",           "VARCHAR(500) DEFAULT ''"),
        ("custom_link_label", "VARCHAR(200) DEFAULT ''"),
        ("custom_link_url",   "VARCHAR(500) DEFAULT ''"),
        ("profile_photo",     "TEXT"),
        ("bg_photo",          "TEXT"),
        ("accent_color",      "VARCHAR(100) DEFAULT '#f0883e'"),
        ("scan_count",        "INTEGER DEFAULT 0"),
        ("updated_at",        "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]
    for _col_name, _col_def in _qcard_cols_to_add:
        cur.execute(f"""
        DO $$ BEGIN
            ALTER TABLE qcards ADD COLUMN {_col_name} {_col_def};
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
        """)

    _qcard_cols_to_alter = [
        ("full_name", "VARCHAR(200)"),
        ("job_title", "VARCHAR(200)"),
        ("company", "VARCHAR(200)"),
        ("email", "VARCHAR(200)"),
        ("phone", "VARCHAR(100)"),
        ("website", "VARCHAR(500)"),
        ("linkedin", "VARCHAR(500)"),
        ("github", "VARCHAR(500)"),
        ("twitter", "VARCHAR(500)"),
        ("custom_link_label", "VARCHAR(200)"),
        ("custom_link_url", "VARCHAR(500)"),
        ("accent_color", "VARCHAR(100)"),
    ]
    for _col_name, _col_type in _qcard_cols_to_alter:
        cur.execute(f"""
        DO $$ BEGIN
            ALTER TABLE qcards ALTER COLUMN {_col_name} TYPE {_col_type};
        EXCEPTION WHEN undefined_column THEN NULL;
        END $$;
        """)

    cur.execute("ALTER TABLE qr_codes ENABLE ROW LEVEL SECURITY;")
    cur.execute("""DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_policies
                       WHERE tablename='qr_codes'
                       AND policyname='user_isolation') THEN
            CREATE POLICY user_isolation ON qr_codes
                USING (user_id=(current_setting('app.current_user_id',true)::INTEGER));
        END IF;
    END $$;""")

    conn.commit(); cur.close(); conn.close()
    return True

init_db()

def get_authed_connection(user_id: int):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SET LOCAL app.current_user_id = %s;", (user_id,))
    cur.close()
    return conn

# ── QR codes ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _fetch_qr_codes(user_id: int):
    conn = get_authed_connection(user_id); cur = conn.cursor()
    cur.execute(
        "SELECT id, name, qr_data, qr_image, created_at "
        "FROM qr_codes WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cur.fetchall(); cur.close(); conn.close(); return rows

def get_user_qr_codes(user_id: int): return _fetch_qr_codes(user_id)
def _bust_cache(): _fetch_qr_codes.clear()

def save_qr_to_db(user_id, name, qr_data, qr_image_b64):
    conn = get_authed_connection(user_id); cur = conn.cursor()
    cur.execute(
        "INSERT INTO qr_codes (user_id, name, qr_data, qr_image) VALUES (%s,%s,%s,%s)",
        (user_id, name, qr_data, qr_image_b64),
    )
    conn.commit(); cur.close(); conn.close(); _bust_cache()

def delete_qr_from_db(qr_id, user_id):
    conn = get_authed_connection(user_id); cur = conn.cursor()
    cur.execute("DELETE FROM qr_codes WHERE id=%s AND user_id=%s", (qr_id, user_id))
    conn.commit(); cur.close(); conn.close(); _bust_cache()

# ── Photo QR ──────────────────────────────────────────────────────────────────
def save_photo_qr_to_db(user_id, photo_b64, caption, visibility, pin=""):
    pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode() if pin else None
    conn = get_connection(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO photo_qr (user_id,photo_data,caption,visibility,pin_hash) "
        "VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (user_id, photo_b64, caption.strip(), visibility, pin_hash),
    )
    new_id = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close(); return new_id

def get_photo_qr(photo_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute(
        "SELECT p.id,p.user_id,p.photo_data,p.caption,p.visibility,p.pin_hash,"
        "p.created_at,u.username "
        "FROM photo_qr p JOIN users u ON u.id=p.user_id WHERE p.id=%s",
        (photo_id,),
    )
    row = cur.fetchone(); cur.close(); conn.close(); return row

def get_user_photo_qrs(user_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute(
        "SELECT id,caption,visibility,created_at FROM photo_qr "
        "WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cur.fetchall(); cur.close(); conn.close(); return rows

def delete_photo_qr_from_db(photo_id, user_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM photo_qr WHERE id=%s AND user_id=%s", (photo_id, user_id))
    conn.commit(); cur.close(); conn.close()

def verify_photo_pin(pin, pin_hash):
    try: return bcrypt.checkpw(pin.encode(), pin_hash.encode())
    except Exception: return False

# ── QcaRd ─────────────────────────────────────────────────────────────────────
_QCARD_COLS = [
    "id","user_id","full_name","job_title","company","bio",
    "email","phone","address","website","linkedin","github","twitter",
    "custom_link_label","custom_link_url","profile_photo","bg_photo",
    "accent_color","scan_count","created_at","updated_at",
]

def _row_to_dict(cur, row):
    if row is None:
        return None
    colnames = [desc[0] for desc in cur.description]
    row_dict = dict(zip(colnames, row))
    # Normalize legacy qcards schema fields to current names.
    if not row_dict.get("profile_photo") and row_dict.get("photo_b64"):
        row_dict["profile_photo"] = row_dict["photo_b64"]
    if not row_dict.get("bg_photo") and row_dict.get("bg_b64"):
        row_dict["bg_photo"] = row_dict["bg_b64"]
    if not row_dict.get("job_title") and row_dict.get("title"):
        row_dict["job_title"] = row_dict["title"]
    if row_dict.get("scan_count") is None and row_dict.get("visits_count") is not None:
        row_dict["scan_count"] = row_dict["visits_count"]
    return row_dict


def get_user_qcard(user_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM qcards WHERE user_id=%s", (user_id,))
    row = cur.fetchone(); card = _row_to_dict(cur, row)
    cur.close(); conn.close();
    return card

def get_qcard_by_id(qcard_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute(
        "SELECT q.*,u.username FROM qcards q "
        "JOIN users u ON u.id=q.user_id WHERE q.id=%s",
        (qcard_id,),
    )
    row = cur.fetchone(); card = _row_to_dict(cur, row)
    cur.close(); conn.close();
    return card

def upsert_qcard(user_id, data: dict) -> int:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id FROM qcards WHERE user_id=%s", (user_id,))
    existing = cur.fetchone()
    fields = ["full_name","job_title","company","bio","email","phone","address",
              "website","linkedin","github","twitter","custom_link_label",
              "custom_link_url","profile_photo","bg_photo","accent_color"]
    # Field max lengths to prevent truncation errors
    field_limits = {"full_name":200, "job_title":200, "company":200, "email":200,
                    "phone":100, "address":500, "website":500, "linkedin":500,
                    "github":500, "twitter":500, "custom_link_label":200,
                    "custom_link_url":500, "accent_color":100}
    vals = [(data.get(f, "") or "")[:field_limits.get(f, 65535)] for f in fields]
    if existing:
        set_clause = ", ".join(f"{f}=%s" for f in fields) + ", updated_at=CURRENT_TIMESTAMP"
        cur.execute(f"UPDATE qcards SET {set_clause} WHERE user_id=%s", vals + [user_id])
        card_id = existing[0]
    else:
        cols_str = ", ".join(["user_id"] + fields)
        phs = ", ".join(["%s"] * (len(fields) + 1))
        cur.execute(
            f"INSERT INTO qcards ({cols_str}) VALUES ({phs}) RETURNING id",
            [user_id] + vals,
        )
        card_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close(); return card_id

def increment_qcard_scan(qcard_id: int):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE qcards SET scan_count=scan_count+1 WHERE id=%s", (qcard_id,))
    conn.commit(); cur.close(); conn.close()

# ── Auth ──────────────────────────────────────────────────────────────────────
def hash_password(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def verify_password(pw, hashed): return bcrypt.checkpw(pw.encode(), hashed.encode())

def lookup_user(username):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id,password FROM users WHERE username=%s", (username.strip(),))
    row = cur.fetchone(); cur.close(); conn.close(); return row

# ── Misc helpers ──────────────────────────────────────────────────────────────
def get_base_url() -> str:
    try:
        r = requests.get("http://localhost:4040/api/tunnels", timeout=2)
        tunnels = r.json().get("tunnels", [])
        for t in tunnels:
            if t.get("proto") == "https": return t["public_url"].rstrip("/")
        if tunnels: return tunnels[0]["public_url"].rstrip("/")
    except Exception:
        pass
    return "http://localhost:8501"

@st.cache_data(show_spinner=False)
def generate_qr_bytes(data):
    img = qrcode.make(data); buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

@st.cache_data(show_spinner=False)
def load_lottieurl(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception: return None

def _image_src_from_b64(b64_data: str, default_mime: str = "jpeg") -> str:
    if not b64_data:
        return ""
    if b64_data.startswith("data:image/"):
        return b64_data
    # Some stored values may already include a data URI prefix.
    if "," in b64_data and b64_data.startswith("data:"):
        b64_data = b64_data.split(",", 1)[1]
    try:
        raw = base64.b64decode(b64_data, validate=True)
    except Exception:
        return f"data:image/{default_mime};base64,{b64_data}"
    if raw.startswith(b"\x89PNG"):
        mime = "png"
    elif raw[:3] == b"\xff\xd8\xff":
        mime = "jpeg"
    elif raw[:6] in (b"GIF87a", b"GIF89a"):
        mime = "gif"
    else:
        mime = default_mime
    return f"data:image/{mime};base64,{b64_data}"

def e(value): return html.escape(str(value), quote=True)


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING
# ══════════════════════════════════════════════════════════════════════════════
_RATE_CFG      = {"login":{"max":5,"window":60},"signup":{"max":3,"window":300},"generate":{"max":20,"window":60}}
_LOCKOUT_SCHED = [60,120,300,900,1800,3600]

def format_wait_time(secs):
    if secs < 60: return "less than 1 minute"
    m = round(secs / 60)
    if m < 60: return f"{m} minute{'s' if m!=1 else ''}"
    h, rm = m//60, m%60
    hs = f"{h} hour{'s' if h!=1 else ''}"
    return f"{hs} and {rm} minute{'s' if rm!=1 else ''}" if rm else hs

def _rate_key(a): return f"_rl_{a}"
def _lk_count_key(a): return f"_rl_lkcount_{a}"

def get_next_lockout(action):
    idx = min(st.session_state.get(_lk_count_key(action), 0), len(_LOCKOUT_SCHED)-1)
    return _LOCKOUT_SCHED[idx]

def is_rate_limited(action):
    cfg = _RATE_CFG[action]; key = _rate_key(action); now = time.time()
    if key not in st.session_state:
        st.session_state[key] = {"attempts":[],"locked_until":0}
    rl = st.session_state[key]
    if now < rl["locked_until"]: return True, int(rl["locked_until"]-now)
    rl["attempts"] = [t for t in rl["attempts"] if now-t < cfg["window"]]
    if len(rl["attempts"]) >= cfg["max"]:
        dur = get_next_lockout(action); rl["locked_until"] = now+dur
        st.session_state[_lk_count_key(action)] = st.session_state.get(_lk_count_key(action),0)+1
        return True, dur
    return False, 0

def record_attempt(action):
    key = _rate_key(action)
    if key not in st.session_state: st.session_state[key] = {"attempts":[],"locked_until":0}
    st.session_state[key]["attempts"].append(time.time())

def clear_attempts(action):
    st.session_state[_rate_key(action)] = {"attempts":[],"locked_until":0}
    st.session_state[_lk_count_key(action)] = 0


# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD STRENGTH
# ══════════════════════════════════════════════════════════════════════════════
def check_password_strength(password):
    checks = [
        (len(password)>=8,            "At least 8 characters"),
        (bool(re.search(r'[A-Z]',password)), "At least one uppercase letter (A-Z)"),
        (bool(re.search(r'[a-z]',password)), "At least one lowercase letter (a-z)"),
        (bool(re.search(r'\d',password)),    "At least one number (0-9)"),
        (bool(re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\\/_ \-+=~`]',password)),
         "At least one special character"),
    ]
    score   = sum(1 for ok,_ in checks if ok)
    missing = [msg for ok,msg in checks if not ok]
    return score, missing

_STRENGTH = {
    0:("No input","#444c56",0),  1:("Very Weak","#f85149",20),
    2:("Weak","#f0883e",40),     3:("Moderate","#d29922",60),
    4:("Strong","#3fb950",80),   5:("Very Strong","#2ea043",100),
}

def render_strength_bar(password, db_key="pw"):
    if not password: return
    ck = f"_pw_cache_{db_key}"
    cached = st.session_state.get(ck)
    if cached is None or cached["pw"] != password:
        score, missing = check_password_strength(password)
        st.session_state[ck] = {"pw":password,"score":score,"missing":missing}
    else:
        score, missing = cached["score"], cached["missing"]
    label, color, pct = _STRENGTH.get(score, _STRENGTH[0])
    st.markdown(f"""
    <div class="pw-wrap">
        <div class="pw-track">
            <div class="pw-fill" style="width:{pct}%;background:{color};"></div>
        </div>
        <p class="pw-lbl" style="color:{color};">Strength: {label}</p>
    </div>""", unsafe_allow_html=True)
    if missing:
        with st.expander("Requirements not yet met", expanded=(score<3)):
            for m in missing:
                st.markdown(
                    f'<i class="bi bi-x-circle-fill" style="color:#f85149;margin-right:6px;"></i>{e(m)}',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            '<i class="bi bi-check-circle-fill" style="color:#3fb950;margin-right:6px;"></i>**All requirements met!**',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULTS = {
    "logged_in": False, "username": "", "user_id": None,
    "active_tab": "Home", "auth_mode": "Login",
    "qr_bytes": None, "qr_data_val": "", "qr_name_val": "",
    "show_save_ui": False,
    "_qcard_ready": False,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state: st.session_state[_k] = _v

def _clear_preview():
    st.session_state.update({
        "show_save_ui": False, "qr_bytes": None,
        "qr_data_val": "", "qr_name_val": "",
        "_qcard_ready": False,
    })
    # Flush qcard editor keys so next open reloads from DB
    for k in list(st.session_state.keys()):
        if k.startswith("qcard_"):
            del st.session_state[k]

inject_global()


# ══════════════════════════════════════════════════════════════════════════════
# QCARD HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _init_qcard_session(user_id: int):
    """Populate qcard_* keys in session state from DB (once per tab visit)."""
    card = get_user_qcard(user_id)
    defaults = {
        "qcard_full_name": "", "qcard_job_title": "", "qcard_company": "",
        "qcard_bio": "", "qcard_email": "", "qcard_phone": "",
        "qcard_address": "", "qcard_website": "", "qcard_linkedin": "",
        "qcard_github": "", "qcard_twitter": "",
        "qcard_custom_link_label": "", "qcard_custom_link_url": "",
        "qcard_accent_color": "#f0883e",
        "qcard_profile_b64": "", "qcard_bg_b64": "",
        "qcard_db_id": None, "qcard_scan_count": 0,
    }
    if card:
        str_fields = ["full_name","job_title","company","bio","email","phone",
                      "address","website","linkedin","github","twitter",
                      "custom_link_label","custom_link_url","accent_color"]
        for f in str_fields:
            value = card.get(f)
            if value is None and f == "job_title":
                value = card.get("title")
            elif value is None and f == "accent_color":
                value = card.get("accent_color")
            defaults[f"qcard_{f}"] = str(value or "")
        defaults["qcard_profile_b64"]  = str(card.get("profile_photo") or card.get("photo_b64") or "")
        defaults["qcard_bg_b64"]       = str(card.get("bg_photo") or card.get("bg_b64") or "")
        defaults["qcard_db_id"]        = card.get("id")
        scan_value = card.get("scan_count") if card.get("scan_count") is not None else card.get("visits_count")
        try:
            defaults["qcard_scan_count"] = int(scan_value or 0)
        except (TypeError, ValueError):
            defaults["qcard_scan_count"] = 0
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    st.session_state["_qcard_ready"] = True


def _build_qcard_html(card: dict, uid: str = "main", large: bool = False) -> str:
    """
    Returns a *complete* standalone HTML document suitable for
    st.components.v1.html().  The card flips on click and lifts on hover.
    """
    accent    = (card.get("accent_color") or "#f0883e").strip()
    name      = e(card.get("full_name",  "") or "")
    title     = e(card.get("job_title", card.get("title", "")) or "")
    company   = e(card.get("company",    "") or "")
    bio       = e(card.get("bio",        "") or "")
    email_v   = e(card.get("email",      "") or "")
    phone_v   = e(card.get("phone",      "") or "")
    website_v = e(card.get("website",    "") or "")
    address_v = e(card.get("address",    "") or "")
    linkedin_v= e(card.get("linkedin",   "") or "")
    github_v  = e(card.get("github",     "") or "")
    twitter_v = e(card.get("twitter",    "") or "")
    cl_label  = e(card.get("custom_link_label","") or "")
    cl_url    = e(card.get("custom_link_url",  "") or "")

    prof_b64 = card.get("profile_photo", card.get("photo_b64", card.get("qcard_profile_b64", ""))) or ""
    bg_b64   = card.get("bg_photo",      card.get("bg_b64", card.get("qcard_bg_b64", ""))) or ""

    # Dimensions
    w, h  = (480, 274) if large else (400, 228)
    av_sz = 82 if large else 72
    nm_fs = "1.22rem" if large else "1.1rem"
    ti_fs = "0.78rem" if large else "0.72rem"
    in_fs = "2rem"    if large else "1.8rem"

    # Avatar HTML
    if prof_b64:
        avatar_html = (
            f'<img src="{_image_src_from_b64(prof_b64)}" '
            f'class="qcrd-avatar" alt="Profile">'
        )
    else:
        init = (html.unescape(name) or "?")[0].upper()
        avatar_html = f'<div class="qcrd-avatar qcrd-init">{e(init)}</div>'

    # Front background CSS value
    if bg_b64:
        bg_src = _image_src_from_b64(bg_b64)
        front_bg_css = (
            f'background-color:#1c2130; '
            f'background-image:url("{bg_src}"); '
            f'background-position:center; background-size:cover; background-repeat:no-repeat;'
        )
        overlay_html = '<div class="qcrd-overlay"></div>'
    else:
        front_bg_css = (
            f'background:linear-gradient(135deg,#1c2130 0%,#0d1117 68%,{accent}18 100%);'
        )
        overlay_html = ""

    title_company = html.escape(
        " · ".join(filter(None, [html.unescape(title), html.unescape(company)])),
        quote=True,
    )

    # Contact rows (back face)
    def crow(icon_cls: str, val: str, limit: int = 40) -> str:
        if not val: return ""
        trimmed = val[:limit] + ("…" if len(val) > limit else "")
        return (
            f'<div class="qcrd-row">'
            f'<div class="qcrd-ico"><i class="bi {icon_cls}"></i></div>'
            f'<div class="qcrd-txt">{trimmed}</div>'
            f'</div>'
        )

    contact_rows = "".join(filter(None, [
        crow("bi-envelope-fill",  email_v),
        crow("bi-telephone-fill", phone_v),
        crow("bi-globe2",         website_v),
        crow("bi-geo-alt-fill",   address_v),
        crow("bi-linkedin",       linkedin_v),
        crow("bi-github",         github_v),
        crow("bi-twitter-x",      twitter_v),
        crow("bi-link-45deg",     cl_label or cl_url),
    ]))
    if not contact_rows:
        contact_rows = (
            '<div style="font-family:Inter,sans-serif;font-size:.7rem;'
            'color:rgba(255,255,255,.3);">No contact info added yet</div>'
        )

    # ── Build the complete standalone HTML document ──────────────────────────
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
*,*::before,*::after {{ box-sizing:border-box; }}
html,body {{
    margin:0; padding:0;
    background:transparent;
    overflow:hidden;
    font-family:'Inter',sans-serif;
}}
/* ── Scene & flip mechanics ─────────── */
.qcrd-scene {{
    perspective:1400px;
    width:{w}px; min-width:{w}px; min-height:{h}px; height:{h}px;
    margin:32px auto 12px;
}}
.qcrd-card {{
    width:100%; height:100%; min-width:100%; min-height:100%;
    width:100%; height:100%;
    position:relative;
    transform-style:preserve-3d;
    transition:transform .72s cubic-bezier(.4,.2,.2,1);
    cursor:pointer;
}}
.qcrd-card:hover:not(.flipped) {{
    transform:translateY(-12px) rotateX(4deg) rotateY(2deg);
}}
.qcrd-card.flipped {{
    transform:rotateY(180deg);
}}
.qcrd-card.flipped:hover {{
    transform:rotateY(180deg) translateY(-12px) rotateX(4deg);
}}
.qcrd-face {{
    position:absolute; inset:0;
    backface-visibility:hidden;
    -webkit-backface-visibility:hidden;
    transform-style:preserve-3d;
    border-radius:18px; overflow:hidden;
    border:1px solid rgba(255,255,255,.07);
    box-shadow:0 18px 40px rgba(0,0,0,.28);
    transition:box-shadow .3s ease;
}}
.qcrd-card:hover .qcrd-face {{
    box-shadow:0 30px 60px rgba(0,0,0,.32);
}}
/* ── FRONT ──────────────────────────── */
.qcrd-front {{ transform:rotateY(0deg); {front_bg_css} position:relative; }}
.qcrd-overlay {{
    position:absolute; inset:0;
    background:linear-gradient(135deg,rgba(0,0,0,.48),rgba(0,0,0,.12));
    z-index:0;
}}
.qcrd-front-body {{
    position:absolute; inset:0; z-index:1;
    padding:22px 26px;
    display:flex; align-items:center; gap:20px;
}}
.qcrd-avatar {{
    width:{av_sz}px; height:{av_sz}px;
    border-radius:50%; object-fit:cover; flex-shrink:0;
    border:3px solid {accent};
    box-shadow:0 0 24px {accent}60;
}}
.qcrd-init {{
    display:flex; align-items:center; justify-content:center;
    font-family:'Playfair Display',serif;
    font-size:{in_fs}; font-weight:700; color:#fff;
    background:{accent};
}}
.qcrd-info {{ flex:1; min-width:0; }}
.qcrd-name {{
    font-family:'Playfair Display',serif;
    font-size:{nm_fs}; font-weight:700; color:#fff;
    margin-bottom:5px;
    text-shadow:0 1px 8px rgba(0,0,0,.65);
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}}
.qcrd-title {{
    font-family:'Inter',sans-serif;
    font-size:{ti_fs}; font-weight:500; color:{accent};
    margin-bottom:3px;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}}
.qcrd-company {{
    font-family:'Inter',sans-serif;
    font-size:.69rem; color:rgba(255,255,255,.6);
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}}
.qcrd-bio {{
    font-family:'Inter',sans-serif;
    font-size:.63rem; color:rgba(255,255,255,.45);
    margin-top:8px; line-height:1.5;
    overflow:hidden; display:-webkit-box;
    -webkit-line-clamp:2; -webkit-box-orient:vertical;
}}
.qcrd-front-hint {{
    position:absolute; bottom:13px; right:18px; z-index:1;
    font-family:'Inter',sans-serif; font-size:.6rem;
    color:rgba(255,255,255,.28);
    display:flex; align-items:center; gap:4px;
}}
/* ── BACK ───────────────────────────── */
.qcrd-back {{
    transform:rotateY(180deg);
    background:#0d1117;
    border:1px solid {accent}28 !important;
}}
.qcrd-stripe {{
    position:absolute; left:0; top:0; bottom:0; width:5px;
    background:linear-gradient(180deg,{accent},{accent}44);
}}
.qcrd-back-body {{
    position:absolute; inset:0;
    padding:14px 18px 14px 24px;
    display:flex; flex-direction:column;
}}
.qcrd-back-hdr {{
    padding-bottom:9px;
    border-bottom:1px solid rgba(255,255,255,.06);
    margin-bottom:10px; flex-shrink:0;
}}
.qcrd-back-name {{
    font-family:'Playfair Display',serif;
    font-size:.94rem; font-weight:700; color:#fff;
}}
.qcrd-back-sub {{
    font-family:'Inter',sans-serif;
    font-size:.64rem; color:{accent};
}}
.qcrd-rows {{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:5px 10px; overflow:hidden; align-content:start;
}}
.qcrd-row {{
    display:flex; align-items:center; gap:6px; min-width:0;
}}
.qcrd-ico {{
    width:20px; height:20px; border-radius:5px; flex-shrink:0;
    background:{accent}1e;
    display:flex; align-items:center; justify-content:center;
    font-size:.65rem; color:{accent};
}}
.qcrd-txt {{
    font-family:'Inter',sans-serif; font-size:.65rem;
    color:rgba(255,255,255,.72);
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1;
}}
.qcrd-back-foot {{
    font-family:'Inter',sans-serif; font-size:.58rem;
    color:rgba(255,255,255,.2); text-align:right; margin-top:auto; padding-top:4px;
}}
/* ── Hint below card ────────────────── */
.qcrd-ui-hint {{
    text-align:center; margin-top:8px;
    font-family:'Inter',sans-serif; font-size:.72rem;
    color:rgba(255,255,255,.28);
    display:flex; align-items:center; justify-content:center; gap:6px;
}}
</style>
</head>
<body>

<div class="qcrd-scene">
  <div class="qcrd-card" id="qcrd-main"
       onclick="this.classList.toggle('flipped')">

    <!-- FRONT -->
    <div class="qcrd-face qcrd-front">
      {overlay_html}
      <div class="qcrd-front-body">
        {avatar_html}
        <div class="qcrd-info">
          <div class="qcrd-name">{name or "Your Name"}</div>
          {f'<div class="qcrd-title">{title}</div>' if title else ""}
          {f'<div class="qcrd-company">{company}</div>' if company else ""}
          {f'<div class="qcrd-bio">{bio}</div>' if bio else ""}
        </div>
      </div>
      <div class="qcrd-front-hint">
        <i class="bi bi-arrow-repeat"></i> flip
      </div>
    </div>

    <!-- BACK -->
    <div class="qcrd-face qcrd-back">
      <div class="qcrd-stripe"></div>
      <div class="qcrd-back-body">
        <div class="qcrd-back-hdr">
          <div class="qcrd-back-name">{name or "Your Name"}</div>
          {f'<div class="qcrd-back-sub">{title_company}</div>' if title_company else ""}
        </div>
        <div class="qcrd-rows">
          {contact_rows}
        </div>
        <div class="qcrd-back-foot">
          <i class="bi bi-arrow-repeat"></i> flip back
        </div>
      </div>
    </div>

  </div>
</div>

<div class="qcrd-ui-hint">
  <i class="bi bi-hand-index-fill"></i>
  Click the card to flip
</div>

</body>
</html>"""


def generate_vcard(card: dict) -> bytes:
    lines = ["BEGIN:VCARD", "VERSION:3.0"]
    name = card.get("full_name", "") or ""
    if name:
        parts = name.strip().rsplit(" ", 1)
        first = parts[0]; last = parts[1] if len(parts) > 1 else ""
        lines += [f"N:{last};{first};;;", f"FN:{name}"]
    for field, vcard_key in [
        ("job_title", "TITLE"), ("title", "TITLE"), ("company", "ORG"),
    ]:
        if card.get(field): lines.append(f"{vcard_key}:{card[field]}")
    if card.get("email"):   lines.append(f"EMAIL;TYPE=INTERNET:{card['email']}")
    if card.get("phone"):   lines.append(f"TEL;TYPE=CELL:{card['phone']}")
    if card.get("website"): lines.append(f"URL:{card['website']}")
    if card.get("address"): lines.append(f"ADR;TYPE=WORK:;;{card['address']};;;;")
    if card.get("linkedin"):lines.append(f"URL;TYPE=LinkedIn:{card['linkedin']}")
    if card.get("github"):  lines.append(f"URL;TYPE=GitHub:{card['github']}")
    if card.get("twitter"): lines.append(f"URL;TYPE=Twitter:{card['twitter']}")
    if card.get("bio"):     lines.append(f"NOTE:{card['bio']}")
    photo_data = card.get("profile_photo") or card.get("photo_b64")
    if photo_data:
        lines.append(f"PHOTO;ENCODING=b;TYPE=JPEG:{photo_data}")
    lines.append("END:VCARD")
    return "\n".join(lines).encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# PHOTO VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_photo_viewer(photo_id):
    row = get_photo_qr(photo_id)
    if not row:
        st.markdown("""
        <div class="empty-state">
            <i class="bi bi-exclamation-triangle empty-icon" style="color:var(--red);"></i>
            <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">Photo Not Found</h3>
            <p class="empty-text">This QR code may have been deleted or the link is invalid.</p>
        </div>""", unsafe_allow_html=True)
        return

    _id, owner_id, photo_b64, caption, visibility, pin_hash, created_at, username = row
    vis_icon  = "bi-globe2"    if visibility == "public" else "bi-lock-fill"
    vis_color = "var(--green)" if visibility == "public" else "var(--accent)"

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">PhotoQR Viewer</div>
        <div class="page-header-sub">
            <i class="bi {vis_icon}" style="color:{vis_color};margin-right:4px;"></i>
            {"Public" if visibility=="public" else "Private"} photo shared by
            <strong>{e(username)}</strong>
            &nbsp;·&nbsp; {e(created_at.strftime("%b %d, %Y"))}
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    if visibility == "private":
        unlock_key = f"_pqr_unlocked_{_id}"
        if not st.session_state.get(unlock_key, False):
            st.markdown("""
            <div style="max-width:360px;margin:0 auto;text-align:center;padding:40px 0;">
                <i class="bi bi-lock-fill" style="font-size:2.8rem;color:var(--accent);display:block;margin-bottom:18px;"></i>
                <div style="font-family:var(--font-h);font-size:1.5rem;font-weight:700;color:var(--tx-1);margin-bottom:8px;">Private Photo</div>
                <p style="font-family:var(--font-b);color:var(--tx-2);font-size:.9rem;margin-bottom:24px;">Enter the PIN provided by the owner to view this photo.</p>
            </div>""", unsafe_allow_html=True)
            _, pin_col, _ = st.columns([1, 2, 1])
            with pin_col:
                with st.container(border=True):
                    entered_pin = st.text_input("PIN", type="password", placeholder="Enter PIN...", key=f"pin_input_{_id}")
                    if st.button("Unlock Photo", type="primary", width='stretch', key=f"pin_btn_{_id}"):
                        if verify_photo_pin(entered_pin, pin_hash):
                            st.session_state[unlock_key] = True; st.rerun()
                        else:
                            st.error("Incorrect PIN. Please try again.")
            return

    try:
        img_bytes = base64.b64decode(photo_b64)
    except Exception:
        st.error("Could not decode the photo."); return

    _, img_col, _ = st.columns([1, 2, 1])
    with img_col:
        with st.container(border=True):
            st.markdown(f"""
            <div class="user-chip" style="margin-bottom:14px;">
                <div class="avatar">{e(username[0].upper())}</div>
                <div>
                    <div class="uname">{e(username)}</div>
                    <div class="urole">Photo shared on {e(created_at.strftime("%B %d, %Y"))}</div>
                </div>
            </div>""", unsafe_allow_html=True)
            st.image(img_bytes, width='stretch')
            if caption:
                st.markdown(f"""
                <div class="meta-block" style="margin-top:12px;">
                    <div class="meta-label">Caption</div>
                    <div class="meta-val">{e(caption)}</div>
                </div>""", unsafe_allow_html=True)
            st.download_button(
                "Download Photo", data=img_bytes,
                file_name=f"photoqr_{_id}.jpg", mime="image/jpeg",
                width='stretch', key=f"viewer_dl_{_id}",
            )

    st.markdown("---")
    _, back_col, _ = st.columns([1, 2, 1])
    with back_col:
        if st.button("Back to QR Studio", width='stretch', key="viewer_back"):
            st.query_params.clear()
            if st.session_state.get("logged_in"): st.session_state["active_tab"] = "PhotoQR"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# QCARD VIEWER  (public page when QR is scanned)
# ══════════════════════════════════════════════════════════════════════════════
def render_qcard_viewer(qcard_id: int):
    # Count scan once per session
    scan_key = f"_qcrd_counted_{qcard_id}"
    if not st.session_state.get(scan_key):
        increment_qcard_scan(qcard_id)
        st.session_state[scan_key] = True

    card = get_qcard_by_id(qcard_id)
    if not card:
        st.markdown("""
        <div class="empty-state">
            <i class="bi bi-person-x empty-icon" style="color:var(--accent);"></i>
            <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">Card Not Found</h3>
            <p class="empty-text">This business card may have been removed or the link is invalid.</p>
        </div>""", unsafe_allow_html=True)
        return

    owner = e(card.get("username", ""))
    display_name = e(card.get("full_name", "") or card.get("username", "Unknown"))

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">
            <i class="bi bi-person-vcard-fill" style="color:var(--accent);margin-right:10px;"></i>
            {display_name}'s Business Card
        </div>
        <div class="page-header-sub">
            Shared by <strong>{owner}</strong> via QcaRd &nbsp;·&nbsp;
            <i class="bi bi-qr-code" style="color:var(--accent);"></i> QR Studio
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    # Card display (large, centered)
    _, card_col, _ = st.columns([1, 3, 1])
    with card_col:
        _st_components.html(
            _build_qcard_html(card, large=True),
            height=380, scrolling=False,
        )

    st.markdown("---")

    # Action buttons
    vcf_data = generate_vcard(card)
    safe_name = re.sub(r'[^\w\-]', '_', card.get("full_name","contact") or "contact")

    action_cols = st.columns(3)
    with action_cols[0]:
        st.download_button(
            "Save Contact (.vcf)",
            data=vcf_data,
            file_name=f"{safe_name}.vcf",
            mime="text/vcard",
            width='stretch',
            type="primary",
            key=f"vcf_dl_{qcard_id}",
        )
    with action_cols[1]:
        if card.get("email"):
            st.link_button(
                f"✉  {e(card['email'])}",
                url=f"mailto:{card['email']}",
                width='stretch',
            )
    with action_cols[2]:
        if card.get("website"):
            url = card["website"]
            if not url.startswith(("http://","https://")):
                url = "https://" + url
            st.link_button("🌐  Visit Website", url=url, width='stretch')

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    _, back_col, _ = st.columns([1, 2, 1])
    with back_col:
        if st.button("Back to QR Studio", width='stretch', key="qcard_viewer_back"):
            st.query_params.clear()
            if st.session_state.get("logged_in"):
                st.session_state["active_tab"] = "QcaRd"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar(is_viewer=False):
    with st.sidebar:
        # Brand
        logo_html = _logo_tag(30, "margin-right:2px;")
        st.markdown(f"""
        <div class="sidebar-brand">
            {logo_html}
            <div>
                <div class="brand-name">QR Studio</div>
                <div class="brand-sub">Group 2 · 2026</div>
            </div>
        </div>""", unsafe_allow_html=True)

        if is_viewer and not st.session_state["logged_in"]:
            st.markdown("""
            <div style="padding:6px 2px 8px;">
                <p style="font-family:var(--font-b);font-size:.82rem;color:var(--tx-3);
                           margin:0 0 8px;text-align:center;line-height:1.5;">
                    Don't have an account yet?
                </p>
            </div>""", unsafe_allow_html=True)
            if st.button("Create a free account", width='stretch',
                         key="sidebar_guest_signup", type="primary"):
                st.query_params.clear()
                st.session_state["auth_mode"] = "Signup"; st.rerun()
            st.markdown("""
            <p style="font-family:var(--font-b);font-size:.72rem;color:var(--tx-3);
                       margin:6px 0 0;text-align:center;">
                Save &amp; share your own photos &amp; cards as QR codes.
            </p>""", unsafe_allow_html=True)
            return

        if not st.session_state["logged_in"]: return

        st.markdown(f"""
        <div class="user-chip">
            <div class="avatar">{e(st.session_state["username"][0].upper())}</div>
            <div>
                <div class="uname">{e(st.session_state["username"])}</div>
                <div class="urole">Member</div>
            </div>
        </div>""", unsafe_allow_html=True)

        nav_items = [
            ("Home","Home"),
            ("My QR Codes","MyQR"),
            ("History","History"),
            ("PhotoQR","PhotoQR"),
            ("QcaRd","QcaRd"),
        ]
        with st.expander("Navigation", expanded=True):
            for label, key in nav_items:
                active = st.session_state["active_tab"] == key
                if st.button(label, key=f"nav_{key}", width='stretch',
                             type="primary" if active else "secondary"):
                    if st.session_state["active_tab"] != key:
                        st.session_state["active_tab"] = key
                        _clear_preview(); st.rerun()

        with st.expander("Recent QR Codes"):
            recent = get_user_qr_codes(st.session_state["user_id"])[:5]
            if recent:
                for _, name, _, _, ts in recent:
                    sn = e(name); trunc = (sn[:21]+"…") if len(sn)>21 else sn
                    st.markdown(f"""
                    <div class="rq-item">
                        <i class="bi bi-qr-code rq-icon"></i>
                        <div>
                            <div class="rq-name">{trunc}</div>
                            <div class="rq-date">{e(ts.strftime("%b %d, %Y"))}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.caption("Nothing saved yet.")

        with st.expander("Account"):
            st.caption(f"Signed in as **{e(st.session_state['username'])}**")
            st.write("")
            if st.button("Sign Out", width='stretch'):
                for k, v in _DEFAULTS.items(): st.session_state[k] = v
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGES
# ══════════════════════════════════════════════════════════════════════════════
_HIDE_SIDEBAR_CSS = """
<style>
[data-testid="stSidebar"]                { display: none !important; }
[data-testid="stSidebarCollapsedControl"]{ display: none !important; }
</style>"""

_BTN_WHITE = """
<style>
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] > button { color:#ffffff !important; font-weight:600 !important; }
</style>"""

def render_login():
    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)
    st.markdown(_BTN_WHITE, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
        logo_lg = _logo_tag(90, "display:block;margin:0 auto 4px;")
        st.markdown(f'<div class="auth-logo">{logo_lg}</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">QR Studio</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-tagline">A QR code, anytime, anywhere.</div>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="e.g. MyPass@123")
            st.write("")
            submitted = st.form_submit_button("Log In", type="primary", width='stretch')

        if submitted:
            blocked, secs = is_rate_limited("login")
            if blocked:
                st.error(f"Too many failed attempts. Please wait {format_wait_time(secs)}.")
            elif not username.strip() or not password:
                st.error("Please enter your username and password.")
            else:
                record_attempt("login")
                result = lookup_user(username)
                if result and verify_password(password, result[1]):
                    clear_attempts("login")
                    st.session_state.update({
                        "logged_in": True, "username": username.strip(),
                        "user_id": result[0], "active_tab": "Home",
                    }); st.rerun()
                else:
                    st.error("Invalid username or password.")

        st.markdown('<div class="auth-switch">New here? Create a free account — it only takes a minute.</div>',
                    unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Create Free Account", width='stretch', key="go_signup", type="primary"):
                st.session_state["auth_mode"] = "Signup"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def render_signup():
    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)
    st.markdown(_BTN_WHITE, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
        logo_lg = _logo_tag(90, "display:block;margin:0 auto 4px;")
        st.markdown(f'<div class="auth-logo">{logo_lg}</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">Create Account</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-tagline">Join QR Studio today.</div>', unsafe_allow_html=True)

        with st.container(border=True):
            new_user = st.text_input("Username", placeholder="Choose a username", key="su_user")
            new_pass = st.text_input("Password", type="password", placeholder="e.g. MyPass@123", key="su_pass")
            render_strength_bar(new_pass or "", db_key="signup")

            with st.expander("Password requirements & examples", expanded=False):
                st.markdown("""
                <div style="padding:4px 0;">
                    <ul style="font-family:var(--font-b);font-size:.78rem;color:var(--tx-2);margin:0 0 10px;padding-left:18px;">
                        <li>At least 8 characters</li>
                        <li>One uppercase letter (A-Z)</li>
                        <li>One lowercase letter (a-z)</li>
                        <li>One number (0-9)</li>
                        <li>One special character (!@#$%^&amp;*...)</li>
                    </ul>
                    <p style="font-family:var(--font-b);font-size:.78rem;font-weight:700;color:var(--accent);margin:0;">
                        Examples: MyPass@123 · Hello$456 · Secure#99 · QrCode!7
                    </p>
                </div>""", unsafe_allow_html=True)

            confirm = st.text_input("Confirm Password", type="password",
                                    placeholder="Re-enter password", key="su_confirm")
            st.write("")
            reg_btn = st.button("Create Account", type="primary", width='stretch')

        if reg_btn:
            blocked, secs = is_rate_limited("signup")
            if blocked:
                st.error(f"Too many registration attempts. Please wait {format_wait_time(secs)}.")
            else:
                score, _ = check_password_strength(new_pass or "")
                if not new_user.strip():  st.error("Please enter a username.")
                elif not new_pass:        st.error("Please enter a password.")
                elif score < 3:           st.error("Password is too weak — please meet at least 3 of the 5 requirements.")
                elif new_pass != confirm: st.error("Passwords do not match.")
                else:
                    record_attempt("signup")
                    try:
                        conn = get_connection(); cur = conn.cursor()
                        cur.execute("INSERT INTO users(username,password) VALUES (%s,%s)",
                                    (new_user.strip(), hash_password(new_pass)))
                        conn.commit(); cur.close(); conn.close()
                        clear_attempts("signup")
                        st.success("Account created! Redirecting to sign in…")
                        time.sleep(1.2); st.session_state["auth_mode"]="Login"; st.rerun()
                    except Exception as ex:
                        if "unique" in str(ex).lower(): st.error("That username is already taken.")
                        else: st.error("Registration failed. Please try again.")

        st.markdown('<div class="auth-switch">Already have an account?</div>', unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Sign in instead →", width='stretch', key="go_login", type="primary"):
                st.session_state["auth_mode"]="Login"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
def render_home():
    lottie_anim = load_lottieurl(
        "https://lottie.host/6a3ab8e3-b3c8-4e40-ad93-b7adfdc4a3eb/Ql1QsdyMTr.json"
    )
    qr_count = len(get_user_qr_codes(st.session_state["user_id"]))
    left_h, right_h = st.columns([3, 2], gap="large")
    with left_h:
        st.markdown(f"""
        <div class="hero">
            <div class="hero-eyebrow">
                <i class="bi bi-lightning-charge-fill"></i>&nbsp;QR Studio
            </div>
            <div class="hero-title">Generate QR codes<br><span class="accent">in seconds.</span></div>
            <p class="hero-desc">A fast, elegant QR code generator built for the modern web.
            Create, save, and manage your QR codes for links, contacts, or anything in between.
            Built with Python &amp; Streamlit.</p>
        </div>""", unsafe_allow_html=True)
    with right_h:
        if HAS_LOTTIE and lottie_anim:
            st_lottie(lottie_anim, height=220, key="hero_lottie")
        else:
            st.markdown(f'<div style="display:flex;justify-content:center;align-items:center;height:220px;">'
                        f'{_logo_tag(64)}</div>', unsafe_allow_html=True)

    st.markdown("---")
    s1, s2, s3 = st.columns(3)
    for col, (num, lbl) in zip([s1,s2,s3], [
        (str(qr_count),"QR Codes Saved"), ("∞","Links Supported"), ("PNG","Export Format"),
    ]):
        with col:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{e(num)}</div>'
                        f'<div class="stat-lbl">{e(lbl)}</div></div>', unsafe_allow_html=True)

    # Promo banners
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)

    with b1:
        with st.container(border=True):
            st.markdown("""
            <div style="background:linear-gradient(135deg,rgba(240,136,62,.10),rgba(88,166,255,.07));
                        border-radius:10px;padding:14px 16px 10px;display:flex;align-items:center;gap:12px;">
                <span style="font-size:1.9rem;flex-shrink:0;">📷</span>
                <div>
                    <div style="font-family:var(--font-h);font-size:.98rem;font-weight:700;color:var(--tx-1);margin-bottom:2px;">
                        PhotoQR
                    </div>
                    <div style="font-family:var(--font-b);font-size:.78rem;color:var(--tx-2);">
                        Turn any photo into a shareable QR — public or private with a PIN.
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
            if st.button("✨ Try PhotoQR", key="banner_photoqr", type="primary", width='stretch'):
                st.session_state["active_tab"]="PhotoQR"; _clear_preview(); st.rerun()

    with b2:
        with st.container(border=True):
            st.markdown("""
            <div style="background:linear-gradient(135deg,rgba(240,136,62,.10),rgba(63,185,80,.07));
                        border-radius:10px;padding:14px 16px 10px;display:flex;align-items:center;gap:12px;">
                <span style="font-size:1.9rem;flex-shrink:0;"><i class="bi bi-credit-card" style="color:#f0883e;"></i></span>
                <div>
                    <div style="font-family:var(--font-h);font-size:.98rem;font-weight:700;color:var(--tx-1);margin-bottom:2px;">
                        QcaRd
                    </div>
                    <div style="font-family:var(--font-b);font-size:.78rem;color:var(--tx-2);">
                        Create a digital business card with a scannable QR code.
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
            if st.button("Create QcaRd", key="banner_qcard", type="primary", width='stretch'):
                st.session_state["active_tab"]="QcaRd"; _clear_preview(); st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="gen-card">', unsafe_allow_html=True)
    st.markdown('<div class="gen-card-title">'
                '<i class="bi bi-qr-code-scan" style="color:var(--accent);"></i>'
                ' Generate a QR Code</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    inp1, inp2 = st.columns(2)
    with inp1: qr_name = st.text_input("Name", placeholder="e.g. My GitHub Profile", key="home_qr_name")
    with inp2: qr_link = st.text_input("Link / Text", placeholder="https://example.com", key="home_qr_link")
    g_col, _ = st.columns([1,3])
    with g_col: gen_btn = st.button("Generate", type="primary", width='stretch')

    if gen_btn:
        blocked, secs = is_rate_limited("generate")
        if blocked:
            st.warning(f"Slow down — too many generations. Please wait {format_wait_time(secs)}.")
        elif not qr_name.strip(): st.warning("Please enter a name for your QR code.")
        elif not qr_link.strip(): st.warning("Please enter a link or text.")
        else:
            record_attempt("generate")
            st.session_state.update({
                "qr_bytes": generate_qr_bytes(qr_link.strip()),
                "qr_data_val": qr_link.strip(),
                "qr_name_val": qr_name.strip(),
                "show_save_ui": True,
            })

    if st.session_state["show_save_ui"] and st.session_state["qr_bytes"]:
        st.markdown("---")
        with st.container(border=True):
            prev_col, act_col = st.columns([1, 2], gap="large")
            with prev_col:
                st.image(st.session_state["qr_bytes"],
                         caption=e(st.session_state["qr_name_val"]), width=200)
            with act_col:
                st.markdown(f"""
                <div class="meta-block">
                    <div class="meta-label">Name</div>
                    <div class="meta-val">{e(st.session_state["qr_name_val"])}</div>
                </div>
                <div class="meta-block">
                    <div class="meta-label">Link / Text</div>
                    <div class="meta-val-sm">{e(st.session_state["qr_data_val"])}</div>
                </div>""", unsafe_allow_html=True)
                save_col, cancel_col = st.columns(2)
                with save_col:
                    if st.button("Save QR Code", type="primary", width='stretch'):
                        b64 = base64.b64encode(st.session_state["qr_bytes"]).decode()
                        save_qr_to_db(
                            st.session_state["user_id"],
                            st.session_state["qr_name_val"],
                            st.session_state["qr_data_val"], b64,
                        )
                        st.success(f'Saved **{e(st.session_state["qr_name_val"])}**!')
                        _clear_preview(); st.rerun()
                with cancel_col:
                    if st.button("Discard", width='stretch'):
                        _clear_preview(); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MY QR CODES
# ══════════════════════════════════════════════════════════════════════════════
def render_my_qr():
    qr_list = get_user_qr_codes(st.session_state["user_id"]); count = len(qr_list)
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">My QR Codes <span class="count-chip">{e(str(count))}</span></div>
        <div class="page-header-sub">Your saved QR codes — download or remove them at any time.</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    if not qr_list:
        st.markdown("""<div class="empty-state">
            <i class="bi bi-inbox empty-icon"></i>
            <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">Nothing here yet</h3>
            <p class="empty-text">Head over to <strong>Home</strong> to generate your first QR code.</p>
        </div>""", unsafe_allow_html=True)
        return
    cols = st.columns(3)
    for idx, (qr_id, name, qr_data, qr_img_b64, created_at) in enumerate(qr_list):
        qr_bytes = base64.b64decode(qr_img_b64)
        short = qr_data if len(qr_data)<=40 else qr_data[:37]+"…"
        with cols[idx % 3]:
            with st.container(border=True):
                st.image(qr_bytes, width='stretch')
                st.markdown(f"""
                <div class="qr-card-meta">
                    <div class="qr-name">{e(name)}</div>
                    <div class="qr-link"><i class="bi bi-link-45deg"></i> {e(short)}</div>
                    <div class="qr-date"><i class="bi bi-calendar3"></i> {e(created_at.strftime("%b %d, %Y  %H:%M"))}</div>
                </div>""", unsafe_allow_html=True)
                st.write("")
                dl_c, del_c = st.columns(2)
                with dl_c:
                    st.download_button("Download", data=qr_bytes,
                                       file_name=f"{name}.png", mime="image/png",
                                       width='stretch', key=f"myqr_dl_{qr_id}")
                with del_c:
                    if st.button("Delete", key=f"myqr_del_{qr_id}", width='stretch'):
                        delete_qr_from_db(qr_id, st.session_state["user_id"]); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════════════
def render_history():
    qr_list = get_user_qr_codes(st.session_state["user_id"]); count = len(qr_list)
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">History <span class="count-chip">{e(str(count))}</span></div>
        <div class="page-header-sub">A full log of every QR code you've saved — newest first.</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    if not qr_list:
        st.markdown("""<div class="empty-state">
            <i class="bi bi-clock-history empty-icon"></i>
            <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">No history yet</h3>
            <p class="empty-text">Generate your first QR code from <strong>Home</strong>.</p>
        </div>""", unsafe_allow_html=True)
        return
    for qr_id, name, qr_data, qr_img_b64, created_at in qr_list:
        qr_bytes = base64.b64decode(qr_img_b64)
        with st.expander(f"{name}  ·  {created_at.strftime('%b %d, %Y  %H:%M')}", expanded=False):
            l_col, r_col = st.columns([1, 2], gap="large")
            with l_col: st.image(qr_bytes, width=148)
            with r_col:
                st.markdown(f"""
                <div class="meta-block"><div class="meta-label">Name</div><div class="meta-val">{e(name)}</div></div>
                <div class="meta-block"><div class="meta-label">Link / Text</div><div class="meta-val-sm">{e(qr_data)}</div></div>
                <div class="meta-block"><div class="meta-label">Created</div><div class="meta-val-sm">{e(created_at.strftime("%B %d, %Y at %H:%M"))}</div></div>
                """, unsafe_allow_html=True)
                dl2, del2 = st.columns(2)
                with dl2:
                    st.download_button("Download", data=qr_bytes,
                                       file_name=f"{name}.png", mime="image/png",
                                       key=f"hist_dl_{qr_id}")
                with del2:
                    if st.button("Delete", key=f"hist_del_{qr_id}"):
                        delete_qr_from_db(qr_id, st.session_state["user_id"]); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PHOTO QR
# ══════════════════════════════════════════════════════════════════════════════
def render_photo_qr():
    st.markdown("""
    <style>
    [data-testid="stCameraInput"] video,
    [data-testid="stCameraInput"] img {
        width:100% !important; aspect-ratio:16/9 !important;
        object-fit:cover !important; border-radius:12px 12px 0 0 !important; display:block !important;
    }
    @media(max-width:640px){
        [data-testid="stCameraInput"] video,
        [data-testid="stCameraInput"] img { aspect-ratio:9/16 !important; }
    }
    [data-testid="stCameraInputButton"]{
        display:flex !important; justify-content:center !important; align-items:center !important;
        background:rgba(13,17,23,.82) !important; border-radius:0 0 12px 12px !important;
        padding:16px 0 !important; border:1px solid rgba(255,255,255,.07) !important; border-top:none !important;
    }
    [data-testid="stCameraInputButton"] button{
        width:64px !important; height:64px !important; border-radius:50% !important;
        border:4px solid rgba(255,255,255,.88) !important;
        background:rgba(240,136,62,.18) !important;
        box-shadow:0 0 0 3px rgba(240,136,62,.38),inset 0 0 0 6px rgba(255,255,255,.10) !important;
        cursor:pointer !important; transition:all .15s !important; font-size:0 !important; padding:0 !important;
    }
    [data-testid="stCameraInputButton"] button:hover{
        background:rgba(240,136,62,.40) !important;
        box-shadow:0 0 0 5px rgba(240,136,62,.55),inset 0 0 0 6px rgba(255,255,255,.18) !important;
        transform:scale(1.07) !important;
    }
    [data-testid="stCameraInputButton"] span,
    [data-testid="stCameraInputButton"] p { display:none !important; }
    </style>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header" style="padding-bottom:8px;">
        <div class="page-header-title">PhotoQR</div>
        <div class="page-header-sub">Capture a photo and turn it into a shareable QR code.</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    tab_create, tab_mine = st.tabs(["Capture & Create", "My Photo QRs"])

    with tab_create:
        st.markdown("""
        <div class="meta-block" style="margin-bottom:6px;">
            <div class="meta-label"><i class="bi bi-camera-fill" style="color:var(--accent);"></i>&nbsp;Step 1 — Take a Photo</div>
        </div>""", unsafe_allow_html=True)

        cam_shot = st.camera_input("Take a photo", key="pqr_camera", label_visibility="collapsed")
        uploaded_photo = None
        if cam_shot is None:
            st.markdown("<div style='margin-top:12px; color:rgba(255,255,255,.7);'>No camera input detected. You can also upload an existing photo below.</div>", unsafe_allow_html=True)
            uploaded_photo = st.file_uploader(
                "Upload a photo instead", type=["jpg","jpeg","png"],
                key="pqr_photo_upload", label_visibility="collapsed",
            )

        photo_file = cam_shot if cam_shot is not None else uploaded_photo
        if photo_file is not None:
            st.markdown("""
            <div style="margin-top:8px;padding:9px 14px;background:rgba(240,136,62,.08);
                        border:1px solid rgba(240,136,62,.22);border-radius:8px;
                        display:flex;align-items:center;gap:8px;">
                <i class="bi bi-check-circle-fill" style="color:var(--green);font-size:1rem;flex-shrink:0;"></i>
                <span style="font-family:var(--font-b);font-size:.8rem;color:var(--tx-2);">
                    Photo ready! You can retake or upload a different one.
                </span>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        caption_val = st.text_input("Caption (optional)", placeholder="e.g. My vacation photo", key="pqr_caption")
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="meta-block" style="margin-bottom:8px;"><div class="meta-label">'
                        '<i class="bi bi-sliders" style="color:var(--accent);"></i>&nbsp;Step 2 — Visibility</div></div>',
                        unsafe_allow_html=True)
            visibility_val = st.radio(
                "Visibility", options=["public","private"],
                format_func=lambda x: "Public — anyone with the QR can view"
                    if x=="public" else "Private — requires a PIN to view",
                key="pqr_visibility",
            )
            pin_val = pin_val2 = ""
            if visibility_val == "private":
                pc1, pc2 = st.columns(2)
                with pc1: pin_val  = st.text_input("PIN", type="password", placeholder="4-12 chars", key="pqr_pin")
                with pc2: pin_val2 = st.text_input("Confirm PIN", type="password", placeholder="Re-enter", key="pqr_pin2")
            st.write("")
            create_btn = st.button("Generate PhotoQR", type="primary", width='stretch', key="pqr_create_btn")

        if create_btn:
            if photo_file is None:
                st.warning("Please take or upload a photo first.")
            elif visibility_val == "private" and not pin_val:
                st.warning("Please set a PIN for your private photo.")
            elif visibility_val == "private" and pin_val != pin_val2:
                st.error("PINs do not match.")
            elif visibility_val == "private" and (len(pin_val)<4 or len(pin_val)>12):
                st.warning("PIN must be between 4 and 12 characters.")
            else:
                with st.spinner("Generating your PhotoQR…"):
                    photo_b64 = base64.b64encode(photo_file.getvalue()).decode()
                    new_id    = save_photo_qr_to_db(
                        st.session_state["user_id"], photo_b64, caption_val,
                        visibility_val, pin_val if visibility_val=="private" else "",
                    )
                    viewer_url = f"{get_base_url()}/?view={new_id}"
                    qr_img = qrcode.make(viewer_url); qr_buf = io.BytesIO()
                    qr_img.save(qr_buf, format="PNG"); qr_bytes = qr_buf.getvalue()
                    save_qr_to_db(
                        st.session_state["user_id"],
                        f"PhotoQR — {caption_val or 'Untitled'}",
                        viewer_url,
                        base64.b64encode(qr_bytes).decode(),
                    )

                st.success("PhotoQR created and saved!")
                st.markdown("---")
                res_l, res_r = st.columns(2, gap="large")
                with res_l:
                    st.markdown('<div class="meta-block"><div class="meta-label">Your QR Code</div></div>',
                                unsafe_allow_html=True)
                    st.image(qr_bytes, width=220)
                    st.download_button("Download QR", data=qr_bytes,
                                       file_name=f"photoqr_{new_id}.png", mime="image/png",
                                       key=f"dl_new_qr_{new_id}")
                with res_r:
                    vis_icon  = "bi-globe2"    if visibility_val=="public" else "bi-lock-fill"
                    vis_color = "var(--green)" if visibility_val=="public" else "var(--accent)"
                    st.markdown(f"""
                    <div class="meta-block">
                        <div class="meta-label">Viewer Link</div>
                        <div class="meta-val-sm" style="word-break:break-all;">{e(viewer_url)}</div>
                    </div>
                    <div class="meta-block" style="margin-top:14px;">
                        <div class="meta-label">Visibility</div>
                        <div class="meta-val">
                            <i class="bi {vis_icon}" style="color:{vis_color};margin-right:6px;"></i>
                            {e(visibility_val.capitalize())}
                        </div>
                    </div>""", unsafe_allow_html=True)
                    if visibility_val == "private":
                        st.info("Share your PIN separately with people you want to give access to.")

    with tab_mine:
        photos   = get_user_photo_qrs(st.session_state["user_id"])
        base_url = get_base_url()
        if not photos:
            st.markdown("""<div class="empty-state">
                <i class="bi bi-camera empty-icon"></i>
                <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">No PhotoQRs yet</h3>
                <p class="empty-text">Go to <strong>Capture &amp; Create</strong> to make your first one.</p>
            </div>""", unsafe_allow_html=True)
        else:
            cols = st.columns(3)
            for idx, (pid, caption, visibility, created_at) in enumerate(photos):
                viewer_url = f"{base_url}/?view={pid}"
                qr_img = qrcode.make(viewer_url); qr_buf = io.BytesIO()
                qr_img.save(qr_buf, format="PNG"); qr_bytes = qr_buf.getvalue()
                vis_icon  = "bi-globe2"    if visibility=="public" else "bi-lock-fill"
                vis_color = "var(--green)" if visibility=="public" else "var(--accent)"
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.image(qr_bytes, width='stretch')
                        st.markdown(f"""
                        <div class="qr-card-meta">
                            <div class="qr-name">{e(caption) if caption else "<em>Untitled</em>"}</div>
                            <div class="qr-link"><i class="bi {vis_icon}" style="color:{vis_color};"></i>&nbsp;{e(visibility.capitalize())}</div>
                            <div class="qr-date"><i class="bi bi-calendar3"></i> {e(created_at.strftime("%b %d, %Y  %H:%M"))}</div>
                        </div>""", unsafe_allow_html=True)
                        st.write("")
                        dc, vc, xc = st.columns(3)
                        with dc:
                            st.download_button("QR", data=qr_bytes, file_name=f"photoqr_{pid}.png",
                                               mime="image/png", width='stretch', key=f"pqr_dl_{pid}")
                        with vc:
                            if st.button("View", key=f"pqr_view_{pid}", width='stretch'):
                                st.query_params["view"] = str(pid); st.rerun()
                        with xc:
                            if st.button("Del", key=f"pqr_del_{pid}", width='stretch'):
                                delete_photo_qr_from_db(pid, st.session_state["user_id"]); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# QCARD PAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_qcard():
    user_id = st.session_state["user_id"]

    # Load from DB on first visit (or after a save/navigate-away)
    if not st.session_state.get("_qcard_ready"):
        _init_qcard_session(user_id)

    st.markdown("""
    <div class="page-header">
        <div class="page-header-title">
            <i class="bi bi-person-vcard-fill" style="color:var(--accent);margin-right:10px;"></i>
            QcaRd
        </div>
        <div class="page-header-sub">
            Design your digital business card. Share it as a QR code, track every scan.
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.info("Only Full Name is required. All other fields are optional — add whatever contact details you want.")

    tab_edit, tab_stats = st.tabs(["Edit Card", "Stats & Share"])

    # ── EDIT TAB ─────────────────────────────────────────────────────────────
    with tab_edit:
        with st.form("qcard_editor_form", clear_on_submit=False):
            # ── Identity ──────────────────────────────────────────────────────
            with st.expander("👤  Identity", expanded=True):
                ec1, ec2 = st.columns(2)
                with ec1:
                    full_name = st.text_input(
                        "Full Name *", placeholder="Jane Doe",
                        key="qcard_full_name",
                    )
                with ec2:
                    job_title = st.text_input(
                        "Job Title / Role", placeholder="Senior Designer",
                        key="qcard_job_title",
                    )
                company = st.text_input(
                    "Company / Organization", placeholder="Acme Corp",
                    key="qcard_company",
                )
                bio = st.text_area(
                    "Short Bio / Tagline", placeholder="Passionate about great design and clean code.",
                    key="qcard_bio", height=80, max_chars=180,
                )

            # ── Contact ────────────────────────────────────────────────────────
            with st.expander("📞  Contact", expanded=True):
                cc1, cc2 = st.columns(2)
                with cc1:
                    email = st.text_input(
                        "Email Address", placeholder="jane@example.com",
                        key="qcard_email",
                    )
                with cc2:
                    phone = st.text_input(
                        "Phone Number", placeholder="+1 555 123 4567",
                        key="qcard_phone",
                    )
                address = st.text_input(
                    "Address / Location", placeholder="San Francisco, CA, USA",
                    key="qcard_address",
                )

            # ── Links ──────────────────────────────────────────────────────────
            with st.expander("🔗  Links"):
                lc1, lc2 = st.columns(2)
                with lc1:
                    website  = st.text_input("Website", placeholder="https://janedoe.dev", key="qcard_website")
                    linkedin = st.text_input("LinkedIn", placeholder="linkedin.com/in/janedoe", key="qcard_linkedin")
                with lc2:
                    github  = st.text_input("GitHub",  placeholder="github.com/janedoe", key="qcard_github")
                    twitter = st.text_input("X / Twitter", placeholder="x.com/janedoe", key="qcard_twitter")
                cll, clu = st.columns(2)
                with cll: cl_label = st.text_input("Custom Link Label", placeholder="Portfolio", key="qcard_custom_link_label")
                with clu: cl_url   = st.text_input("Custom Link URL",   placeholder="https://portfolio.io", key="qcard_custom_link_url")

            # ── Appearance ─────────────────────────────────────────────────────
            with st.expander("🎨  Appearance"):
                accent_color = st.color_picker(
                    "Card accent colour", key="qcard_accent_color",
                )

                st.markdown("**Profile Photo** *(optional — appears on front of card)*")
                prof_up = st.file_uploader(
                    "Upload profile photo", type=["jpg","jpeg","png"],
                    key="qcard_prof_uploader", label_visibility="collapsed",
                )
                if prof_up is not None:
                    raw = prof_up.read()
                    st.session_state["qcard_profile_b64"] = base64.b64encode(raw).decode()

                if st.session_state.get("qcard_profile_b64"):
                    try:
                        thmb = base64.b64decode(st.session_state["qcard_profile_b64"])
                        st.image(thmb, width=80, caption="Current profile photo")
                    except (ValueError, Exception):
                        st.warning("Profile photo data is corrupted. Please re-upload.")
                        st.session_state["qcard_profile_b64"] = ""
                    if st.form_submit_button("Remove Profile Photo", key="rm_prof"):
                        st.session_state["qcard_profile_b64"] = ""; st.rerun()

                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                st.markdown("**Background Photo** *(optional — overlays the card front)*")
                bg_up = st.file_uploader(
                    "Upload background photo", type=["jpg","jpeg","png"],
                    key="qcard_bg_uploader", label_visibility="collapsed",
                )
                if bg_up is not None:
                    raw = bg_up.read()
                    st.session_state["qcard_bg_b64"] = base64.b64encode(raw).decode()

                if st.session_state.get("qcard_bg_b64"):
                    try:
                        thmb = base64.b64decode(st.session_state["qcard_bg_b64"])
                        st.image(thmb, width=160, caption="Current background")
                    except (ValueError, Exception):
                        st.warning("⚠ Background photo data is corrupted. Please re-upload.")
                        st.session_state["qcard_bg_b64"] = ""
                    if st.form_submit_button("✕ Remove Background", key="rm_bg"):
                        st.session_state["qcard_bg_b64"] = ""; st.rerun()

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            save_col, _ = st.columns([1, 2])
            with save_col:
                save_btn = st.form_submit_button("Save QcaRd", type="primary", width='stretch', key="qcard_save_btn")

            if save_btn:
                if not st.session_state.get("qcard_full_name","").strip():
                    st.error("Full Name is required.")
                else:
                    data = {
                        "full_name":          st.session_state.get("qcard_full_name",""),
                        "job_title":          st.session_state.get("qcard_job_title",""),
                        "company":            st.session_state.get("qcard_company",""),
                        "bio":                st.session_state.get("qcard_bio",""),
                        "email":              st.session_state.get("qcard_email",""),
                        "phone":              st.session_state.get("qcard_phone",""),
                        "address":            st.session_state.get("qcard_address",""),
                        "website":            st.session_state.get("qcard_website",""),
                        "linkedin":           st.session_state.get("qcard_linkedin",""),
                        "github":             st.session_state.get("qcard_github",""),
                        "twitter":            st.session_state.get("qcard_twitter",""),
                        "custom_link_label":  st.session_state.get("qcard_custom_link_label",""),
                        "custom_link_url":    st.session_state.get("qcard_custom_link_url",""),
                        "accent_color":       st.session_state.get("qcard_accent_color","#f0883e"),
                        "profile_photo":      st.session_state.get("qcard_profile_b64",""),
                        "bg_photo":           st.session_state.get("qcard_bg_b64",""),
                    }
                    card_id = upsert_qcard(user_id, data)
                    st.session_state["qcard_db_id"] = card_id

                    # Refresh scan count from DB
                    fresh = get_user_qcard(user_id)
                    st.session_state["qcard_scan_count"] = fresh.get("scan_count", 0) if fresh else 0

                    st.success(" QcaRd saved! Head to **Stats & Share** for your QR code.")

        # ── LIVE PREVIEW REMOVED ─ Card shown only in Stats & Share tab ────────

    # ── STATS & SHARE TAB ─────────────────────────────────────────────────────
    with tab_stats:
        db_id = st.session_state.get("qcard_db_id")
        if not db_id:
            st.markdown("""
            <div class="empty-state">
                <i class="bi bi-person-vcard empty-icon" style="color:var(--accent);"></i>
                <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">No card saved yet</h3>
                <p class="empty-text">Fill in your details in the <strong>Edit Card</strong> tab and hit Save.</p>
            </div>""", unsafe_allow_html=True)
        else:
            # Always refresh stats from DB
            fresh      = get_user_qcard(user_id)
            scan_value = fresh.get("scan_count") if fresh and fresh.get("scan_count") is not None else fresh.get("visits_count") if fresh else 0
            try:
                scan_count = int(scan_value or 0)
            except (TypeError, ValueError):
                scan_count = 0

            base_url   = get_base_url()
            viewer_url = f"{base_url}/?qcard={db_id}"

            # Generate shareable QR
            qr_img = qrcode.make(viewer_url)
            qr_buf = io.BytesIO(); qr_img.save(qr_buf, format="PNG")
            qr_bytes = qr_buf.getvalue()

            # ── Card preview ────────────────────────────────────────────────
            st.markdown("""
            <div style="font-family:'Inter',sans-serif;font-size:.72rem;font-weight:700;
                        letter-spacing:.09em;text-transform:uppercase;color:#f0883e;margin-bottom:4px;">
                Your Card Preview  <span style="font-weight:400;color:rgba(255,255,255,.35);font-size:.65rem;">— as others will see it</span>
            </div>""", unsafe_allow_html=True)

            # Build preview from latest saved data
            preview_card = fresh or {}
            # Also overlay any unsaved session changes
            preview_card_data = {
                "full_name":         st.session_state.get("qcard_full_name", preview_card.get("full_name","")),
                "job_title":         st.session_state.get("qcard_job_title", preview_card.get("job_title","")),
                "company":           st.session_state.get("qcard_company",   preview_card.get("company","")),
                "bio":               st.session_state.get("qcard_bio",       preview_card.get("bio","")),
                "email":             st.session_state.get("qcard_email",     preview_card.get("email","")),
                "phone":             st.session_state.get("qcard_phone",     preview_card.get("phone","")),
                "website":           st.session_state.get("qcard_website",   preview_card.get("website","")),
                "address":           st.session_state.get("qcard_address",   preview_card.get("address","")),
                "linkedin":          st.session_state.get("qcard_linkedin",  preview_card.get("linkedin","")),
                "github":            st.session_state.get("qcard_github",    preview_card.get("github","")),
                "twitter":           st.session_state.get("qcard_twitter",   preview_card.get("twitter","")),
                "custom_link_label": st.session_state.get("qcard_custom_link_label", preview_card.get("custom_link_label","")),
                "custom_link_url":   st.session_state.get("qcard_custom_link_url",   preview_card.get("custom_link_url","")),
                "accent_color":      st.session_state.get("qcard_accent_color", preview_card.get("accent_color","#f0883e")),
                    "profile_photo":     st.session_state.get("qcard_profile_b64") or preview_card.get("profile_photo", "") or preview_card.get("photo_b64", ""),
                "bg_photo":          st.session_state.get("qcard_bg_b64") or preview_card.get("bg_photo", "") or preview_card.get("bg_b64", ""),
            }
            _st_components.html(
                _build_qcard_html(preview_card_data, large=True),
                height=380, scrolling=False,
            )
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

            # ── Stats row + QR ──────────────────────────────────────────────
            stat_l, stat_r = st.columns([1, 1], gap="large")

            with stat_l:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,rgba(240,136,62,.12),rgba(240,136,62,.04));
                            border:1px solid rgba(240,136,62,.25);border-radius:14px;
                            padding:24px 20px;text-align:center;margin-bottom:16px;">
                    <div style="font-family:'Inter',sans-serif;font-size:.72rem;font-weight:700;
                                letter-spacing:.1em;text-transform:uppercase;color:#f0883e;margin-bottom:8px;">
                        <i class="bi bi-graph-up-arrow"></i>&nbsp; Total QR Scans
                    </div>
                    <div style="font-family:'Playfair Display',serif;font-size:3.2rem;font-weight:700;
                                color:#e6edf3;line-height:1.1;">{scan_count:,}</div>
                    <div style="font-family:'Inter',sans-serif;font-size:.76rem;color:#6e7681;margin-top:6px;">
                        scan{'s' if scan_count!=1 else ''} recorded
                    </div>
                </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div class="meta-block">
                    <div class="meta-label"><i class="bi bi-link-45deg"></i> Shareable URL</div>
                    <div class="meta-val-sm" style="word-break:break-all;user-select:all;">
                        {e(viewer_url)}
                    </div>
                </div>""", unsafe_allow_html=True)

                vcf = generate_vcard(fresh or {})
                safe_name = re.sub(r'[^\w\-]', '_',
                    (fresh.get("full_name","card") if fresh else "card") or "card")
                st.download_button(
                    "Download vCard (.vcf)",
                    data=vcf, file_name=f"{safe_name}.vcf",
                    mime="text/vcard", width='stretch',
                    key="stats_vcf_dl",
                )

            with stat_r:
                st.markdown("""
                <div style="font-family:'Inter',sans-serif;font-size:.72rem;font-weight:700;
                            letter-spacing:.09em;text-transform:uppercase;color:#f0883e;margin-bottom:8px;">
                    Your QR Code
                </div>""", unsafe_allow_html=True)
                with st.container(border=True):
                    _, qr_c, _ = st.columns([1,3,1])
                    with qr_c: st.image(qr_bytes, width='stretch')
                st.download_button(
                    "⬇  Download QR Code",
                    data=qr_bytes, file_name=f"qcard_{db_id}.png",
                    mime="image/png", width='stretch', type="primary",
                    key="stats_qr_dl",
                )
                if st.button("Save QR Code", width='stretch', key="stats_qr_save_btn"):
                    save_qr_to_db(
                        st.session_state["user_id"],
                        f"QcaRd — {fresh.get('full_name','Card') or 'Card'}",
                        viewer_url,
                        base64.b64encode(qr_bytes).decode(),
                    )
                    st.success("Your QcaRd QR code has been saved to My QR Codes.")
                st.markdown("""
                <p style="font-family:'Inter',sans-serif;font-size:.72rem;color:#6e7681;
                           text-align:center;margin-top:8px;">
                    Share this QR code anywhere. Each scan is counted above.
                </p>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING
# ══════════════════════════════════════════════════════════════════════════════
params      = st.query_params
view_id     = params.get("view",  None)
qcard_param = params.get("qcard", None)

if view_id is not None:
    try:
        render_sidebar(is_viewer=True)
        render_photo_viewer(int(view_id))
        render_footer()
    except (ValueError, TypeError):
        st.error("Invalid photo link.")

elif qcard_param is not None:
    try:
        render_sidebar(is_viewer=True)
        render_qcard_viewer(int(qcard_param))
        render_footer()
    except (ValueError, TypeError):
        st.error("Invalid business card link.")

elif not st.session_state["logged_in"]:
    if st.session_state["auth_mode"] == "Signup": render_signup()
    else: render_login()

else:
    render_sidebar()
    _tab = st.session_state["active_tab"]
    if   _tab == "Home":    render_home();      render_footer()
    elif _tab == "MyQR":    render_my_qr();     render_footer()
    elif _tab == "History": render_history();   render_footer()
    elif _tab == "PhotoQR": render_photo_qr();  render_footer()
    elif _tab == "QcaRd":   render_qcard();     render_footer()