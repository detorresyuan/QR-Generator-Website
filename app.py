import streamlit as st
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

def _load_css() -> str:
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    try:
        with open(css_path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""

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

def _db_cfg() -> dict:
    try:
        s = st.secrets["db"]
        return {"dbname": s["dbname"], "user": s["user"], "password": s["password"], "host": s["host"], "port": str(s["port"])}
    except Exception:
        return {"dbname": os.environ.get("DB_NAME","postgres"), "user": os.environ.get("DB_USER","postgres"), "password": os.environ.get("DB_PASSWORD",""), "host": os.environ.get("DB_HOST","localhost"), "port": os.environ.get("DB_PORT","5432")}

def get_connection():
    return psycopg2.connect(dbname="postgres", user="postgres", password="group2", host="localhost", port="5432")

@st.cache_resource(show_spinner=False)
def init_db():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, password TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS qr_codes (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, name VARCHAR(200) NOT NULL, qr_data TEXT NOT NULL, qr_image TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS photo_qr (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, photo_data TEXT NOT NULL, caption VARCHAR(300) DEFAULT '', visibility VARCHAR(10) DEFAULT 'public' CHECK (visibility IN ('public','private')), pin_hash TEXT DEFAULT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("ALTER TABLE qr_codes ENABLE ROW LEVEL SECURITY;")
    cur.execute("""DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='qr_codes' AND policyname='user_isolation') THEN CREATE POLICY user_isolation ON qr_codes USING (user_id=(current_setting('app.current_user_id',true)::INTEGER)); END IF; END $$;""")
    conn.commit(); cur.close(); conn.close()
    return True

init_db()

def get_authed_connection(user_id: int):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SET LOCAL app.current_user_id = %s;", (user_id,)); cur.close()
    return conn

@st.cache_data(ttl=30, show_spinner=False)
def _fetch_qr_codes(user_id: int):
    conn = get_authed_connection(user_id); cur = conn.cursor()
    cur.execute("SELECT id, name, qr_data, qr_image, created_at FROM qr_codes WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows

def get_user_qr_codes(user_id: int): return _fetch_qr_codes(user_id)
def _bust_cache(): _fetch_qr_codes.clear()

def save_qr_to_db(user_id: int, name: str, qr_data: str, qr_image_b64: str):
    conn = get_authed_connection(user_id); cur = conn.cursor()
    cur.execute("INSERT INTO qr_codes (user_id, name, qr_data, qr_image) VALUES (%s,%s,%s,%s)", (user_id, name, qr_data, qr_image_b64))
    conn.commit(); cur.close(); conn.close(); _bust_cache()

def delete_qr_from_db(qr_id: int, user_id: int):
    conn = get_authed_connection(user_id); cur = conn.cursor()
    cur.execute("DELETE FROM qr_codes WHERE id = %s AND user_id = %s", (qr_id, user_id))
    conn.commit(); cur.close(); conn.close(); _bust_cache()

def get_base_url() -> str:
    try:
        r = requests.get("http://localhost:4040/api/tunnels", timeout=2)
        tunnels = r.json().get("tunnels", [])
        for t in tunnels:
            if t.get("proto") == "https":
                return t["public_url"].rstrip("/")
        if tunnels:
            return tunnels[0]["public_url"].rstrip("/")
    except Exception:
        pass
    return "http://localhost:8501"

def save_photo_qr_to_db(user_id: int, photo_b64: str, caption: str, visibility: str, pin: str = "") -> int:
    pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode() if pin else None
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO photo_qr (user_id, photo_data, caption, visibility, pin_hash) VALUES (%s,%s,%s,%s,%s) RETURNING id", (user_id, photo_b64, caption.strip(), visibility, pin_hash))
    new_id = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
    return new_id

def get_photo_qr(photo_id: int):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT p.id, p.user_id, p.photo_data, p.caption, p.visibility, p.pin_hash, p.created_at, u.username FROM photo_qr p JOIN users u ON u.id=p.user_id WHERE p.id=%s", (photo_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row

def get_user_photo_qrs(user_id: int):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, caption, visibility, created_at FROM photo_qr WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows

def delete_photo_qr_from_db(photo_id: int, user_id: int):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM photo_qr WHERE id=%s AND user_id=%s", (photo_id, user_id))
    conn.commit(); cur.close(); conn.close()

def verify_photo_pin(pin: str, pin_hash: str) -> bool:
    try: return bcrypt.checkpw(pin.encode(), pin_hash.encode())
    except Exception: return False

def hash_password(pw: str) -> str: return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def verify_password(pw: str, hashed: str) -> bool: return bcrypt.checkpw(pw.encode(), hashed.encode())

def lookup_user(username: str):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, password FROM users WHERE username=%s", (username.strip(),))
    row = cur.fetchone(); cur.close(); conn.close()
    return row

@st.cache_data(show_spinner=False)
def generate_qr_bytes(data: str) -> bytes:
    img = qrcode.make(data); buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

@st.cache_data(show_spinner=False)
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception: return None

def e(value) -> str: return html.escape(str(value), quote=True)

# ═══════════════════════════════════════════════════════════════
# RATE LIMITING — human-readable time (minutes / hours, not seconds)
# ═══════════════════════════════════════════════════════════════
_RATE_CFG = {
    "login":    {"max": 5,  "window": 60,  "lockout": 300},
    "signup":   {"max": 3,  "window": 300, "lockout": 600},
    "generate": {"max": 20, "window": 60,  "lockout": 30},
}

def format_wait_time(secs: int) -> str:
    if secs < 60:
        return "less than 1 minute"
    total_mins = round(secs / 60)
    if total_mins < 60:
        return f"{total_mins} minute{'s' if total_mins != 1 else ''}"
    hours = total_mins // 60
    mins  = total_mins % 60
    h_str = f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{h_str} and {mins} minute{'s' if mins != 1 else ''}" if mins else h_str

def _rate_key(action: str) -> str: return f"_rl_{action}"

def is_rate_limited(action: str) -> tuple[bool, int]:
    cfg = _RATE_CFG[action]; key = _rate_key(action); now = time.time()
    if key not in st.session_state:
        st.session_state[key] = {"attempts": [], "locked_until": 0}
    rl = st.session_state[key]
    if now < rl["locked_until"]: return True, int(rl["locked_until"] - now)
    rl["attempts"] = [t for t in rl["attempts"] if now - t < cfg["window"]]
    if len(rl["attempts"]) >= cfg["max"]:
        rl["locked_until"] = now + cfg["lockout"]; return True, cfg["lockout"]
    return False, 0

def record_attempt(action: str):
    key = _rate_key(action)
    if key not in st.session_state: st.session_state[key] = {"attempts": [], "locked_until": 0}
    st.session_state[key]["attempts"].append(time.time())

def clear_attempts(action: str):
    st.session_state[_rate_key(action)] = {"attempts": [], "locked_until": 0}

# ═══════════════════════════════════════════════════════════════
# PASSWORD STRENGTH
# ═══════════════════════════════════════════════════════════════
def check_password_strength(password: str):
    checks = [
        (len(password) >= 8,                                                  "At least 8 characters"),
        (bool(re.search(r'[A-Z]', password)),                                 "At least one uppercase letter (A-Z)"),
        (bool(re.search(r'[a-z]', password)),                                 "At least one lowercase letter (a-z)"),
        (bool(re.search(r'\d', password)),                                    "At least one number (0-9)"),
        (bool(re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\\/_\-+=~`]', password)), "At least one special character"),
    ]
    score = sum(1 for ok, _ in checks if ok)
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
    if not password: return
    cache_key = f"_pw_cache_{db_key}"
    cached = st.session_state.get(cache_key)
    if cached is None or cached["pw"] != password:
        score, missing = check_password_strength(password)
        st.session_state[cache_key] = {"pw": password, "score": score, "missing": missing}
    else:
        score, missing = cached["score"], cached["missing"]
    label, color, pct = _STRENGTH.get(score, _STRENGTH[0])
    st.markdown(f"""
    <div class="pw-wrap">
        <div class="pw-track"><div class="pw-fill" style="width:{pct}%;background:{color};"></div></div>
        <p class="pw-lbl" style="color:{color};">Strength: {label}</p>
    </div>
    """, unsafe_allow_html=True)
    if missing:
        with st.expander("Requirements not yet met", expanded=(score < 3)):
            for m in missing:
                st.markdown(f'<i class="bi bi-x-circle-fill" style="color:#f85149;margin-right:6px;"></i>{e(m)}', unsafe_allow_html=True)
    else:
        st.markdown('<i class="bi bi-check-circle-fill" style="color:#3fb950;margin-right:6px;"></i>**All requirements met!**', unsafe_allow_html=True)

def _debounce_input(key: str, value: str, delay: float = 0.45) -> bool:
    now = time.time(); val_key = f"_dbi_v_{key}"; time_key = f"_dbi_t_{key}"
    last_val = st.session_state.get(val_key, ""); last_changed = st.session_state.get(time_key, 0)
    if value != last_val:
        st.session_state[val_key] = value; st.session_state[time_key] = now; return False
    return (now - last_changed) >= delay

# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
_DEFAULTS = {
    "logged_in": False, "username": "", "user_id": None,
    "active_tab": "Home", "auth_mode": "Login",
    "qr_bytes": None, "qr_data_val": "", "qr_name_val": "", "show_save_ui": False,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state: st.session_state[_k] = _v

def _clear_preview():
    st.session_state["show_save_ui"] = False; st.session_state["qr_bytes"] = None
    st.session_state["qr_data_val"] = ""; st.session_state["qr_name_val"] = ""

# ═══════════════════════════════════════════════════════════════
# PHOTO VIEWER
# ═══════════════════════════════════════════════════════════════
def render_photo_viewer(photo_id: int):
    row = get_photo_qr(photo_id)
    if not row:
        st.markdown("""
        <div class="empty-state">
            <i class="bi bi-exclamation-triangle empty-icon" style="color:var(--red);"></i>
            <h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">Photo Not Found</h3>
            <p class="empty-text">This QR code may have been deleted or the link is invalid.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    _id, owner_id, photo_b64, caption, visibility, pin_hash, created_at, username = row
    vis_icon  = "bi-globe2"    if visibility == "public" else "bi-lock-fill"
    vis_color = "var(--green)" if visibility == "public" else "var(--accent)"

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">PhotoQR Viewer</div>
        <div class="page-header-sub">
            <i class="bi {vis_icon}" style="color:{vis_color};margin-right:4px;"></i>
            {"Public" if visibility == "public" else "Private"} photo
            shared by <strong>{e(username)}</strong>
            &nbsp;·&nbsp; {e(created_at.strftime("%b %d, %Y"))}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    if visibility == "private":
        unlock_key = f"_pqr_unlocked_{_id}"
        if not st.session_state.get(unlock_key, False):
            st.markdown("""
            <div style="max-width:360px;margin:0 auto;text-align:center;padding:40px 0;">
                <i class="bi bi-lock-fill" style="font-size:2.8rem;color:var(--accent);display:block;margin-bottom:18px;"></i>
                <div style="font-family:var(--font-h);font-size:1.5rem;font-weight:700;color:var(--tx-1);margin-bottom:8px;">Private Photo</div>
                <p style="font-family:var(--font-b);color:var(--tx-2);font-size:.9rem;margin-bottom:24px;">Enter the PIN provided by the owner to view this photo.</p>
            </div>
            """, unsafe_allow_html=True)
            _, pin_col, _ = st.columns([1, 2, 1])
            with pin_col:
                with st.container(border=True):
                    entered_pin = st.text_input("PIN", type="password", placeholder="Enter PIN...", key=f"pin_input_{_id}")
                    if st.button("Unlock Photo", type="primary", use_container_width=True, key=f"pin_btn_{_id}"):
                        if verify_photo_pin(entered_pin, pin_hash):
                            st.session_state[unlock_key] = True; st.rerun()
                        else:
                            st.error("Incorrect PIN. Please try again.")
            return

    try:
        img_bytes = base64.b64decode(photo_b64)
    except Exception:
        st.error("Could not decode the photo. It may be corrupted."); return

    _, img_col, _ = st.columns([1, 2, 1])
    with img_col:
        with st.container(border=True):
            initial = e(username[0].upper())
            st.markdown(f"""
            <div class="user-chip" style="margin-bottom:14px;">
                <div class="avatar">{initial}</div>
                <div>
                    <div class="uname">{e(username)}</div>
                    <div class="urole">Photo shared on {e(created_at.strftime("%B %d, %Y"))}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.image(img_bytes, use_container_width=True)
            if caption:
                st.markdown(f"""
                <div class="meta-block" style="margin-top:12px;">
                    <div class="meta-label">Caption</div>
                    <div class="meta-val">{e(caption)}</div>
                </div>
                """, unsafe_allow_html=True)
            st.download_button("Download Photo", data=img_bytes, file_name=f"photoqr_{_id}.jpg", mime="image/jpeg", use_container_width=True, key=f"viewer_dl_{_id}")

    st.markdown("---")
    _, back_col, _ = st.columns([1, 2, 1])
    with back_col:
        if st.button("Back to QR Studio", use_container_width=True, key="viewer_back"):
            st.query_params.clear()
            if st.session_state.get("logged_in"): st.session_state["active_tab"] = "PhotoQR"
            st.rerun()

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
def render_sidebar(is_viewer: bool = False):
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-brand">
            {QR_LOGO_SM}
            <div>
                <div class="brand-name">QR Studio</div>
                <div class="brand-sub">Group 2 · 2026</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Guest viewing a photo: show subtle sign-up nudge, not in their face
        if is_viewer and not st.session_state["logged_in"]:
            st.markdown("""
            <div style="padding:10px 2px 8px;">
                <p style="font-family:var(--font-b);font-size:.82rem;color:var(--tx-3);
                           margin:0 0 8px;text-align:center;line-height:1.5;">
                    Don't have an account yet?
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Create a free account", use_container_width=True, key="sidebar_guest_signup"):
                st.query_params.clear()
                st.session_state["auth_mode"] = "Signup"
                st.rerun()
            st.markdown("""
            <div style="padding:6px 2px 0;">
                <p style="font-family:var(--font-b);font-size:.73rem;color:var(--tx-3);
                           margin:0;text-align:center;">
                    Save &amp; share your own photos as QR codes.
                </p>
            </div>
            """, unsafe_allow_html=True)
            return

        if not st.session_state["logged_in"]: return

        initial = e(st.session_state["username"][0].upper())
        uname   = e(st.session_state["username"])
        st.markdown(f"""
        <div class="user-chip">
            <div class="avatar">{initial}</div>
            <div>
                <div class="uname">{uname}</div>
                <div class="urole">Member</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Navigation", expanded=True):
            for label, key in [("Home","Home"),("My QR Codes","MyQR"),("History","History"),("PhotoQR","PhotoQR")]:
                active = st.session_state["active_tab"] == key
                if st.button(label, key=f"nav_{key}", use_container_width=True, type="primary" if active else "secondary"):
                    if st.session_state["active_tab"] != key:
                        st.session_state["active_tab"] = key; _clear_preview(); st.rerun()

        with st.expander("Recent QR Codes"):
            recent = get_user_qr_codes(st.session_state["user_id"])[:5]
            if recent:
                for _, name, _, _, ts in recent:
                    safe_name = e(name); truncated = (safe_name[:21] + "...") if len(safe_name) > 21 else safe_name
                    st.markdown(f"""
                    <div class="rq-item">
                        <i class="bi bi-qr-code rq-icon"></i>
                        <div>
                            <div class="rq-name">{truncated}</div>
                            <div class="rq-date">{e(ts.strftime("%b %d, %Y"))}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("Nothing saved yet.")

        with st.expander("Account"):
            st.caption(f"Signed in as **{e(st.session_state['username'])}**")
            st.write("")
            if st.button("Sign Out", use_container_width=True):
                for k, v in _DEFAULTS.items(): st.session_state[k] = v
                st.rerun()

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
        st.markdown(f'<div class="auth-logo">{QR_LOGO_SVG}</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">QR Studio</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-tagline">A QR code, anytime, anywhere.</div>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username  = st.text_input("Username", placeholder="Enter your username")
            password  = st.text_input("Password", type="password", placeholder="........")
            st.write("")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

        if submitted:
            blocked, secs = is_rate_limited("login")
            if blocked:
                st.error(f"Too many failed attempts. Please wait {format_wait_time(secs)} before trying again.")
            elif not username.strip() or not password:
                st.error("Please enter your username and password.")
            else:
                record_attempt("login")
                result = lookup_user(username)
                if result and verify_password(password, result[1]):
                    clear_attempts("login")
                    st.session_state["logged_in"] = True; st.session_state["username"] = username.strip()
                    st.session_state["user_id"] = result[0]; st.session_state["active_tab"] = "Home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        st.markdown("<div class=\"auth-switch\">Don't have an account?</div>", unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Create an account ->", use_container_width=True, key="go_signup"):
                st.session_state["auth_mode"] = "Signup"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_signup():
    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
        st.markdown(f'<div class="auth-logo">{QR_LOGO_SVG}</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">Create Account</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-tagline">Join QR Studio today.</div>', unsafe_allow_html=True)

        with st.container(border=True):
            new_user = st.text_input("Username", placeholder="Choose a username", key="su_user")
            new_pass = st.text_input(
                "Password",
                type="password",
                placeholder="e.g. MyPass@123",
                key="su_pass",
            )
            # Password format hint box
            st.markdown("""
            <div style="margin:-4px 0 8px;padding:9px 12px;
                        background:rgba(240,136,62,.07);
                        border:1px solid rgba(240,136,62,.20);
                        border-radius:8px;">
                <p style="font-family:var(--font-b);font-size:.76rem;color:var(--tx-3);margin:0 0 4px;">
                    <i class="bi bi-lightbulb" style="color:var(--accent);margin-right:4px;"></i>
                    Must have: 8+ characters, uppercase, lowercase, number &amp; special character.
                </p>
                <p style="font-family:var(--font-b);font-size:.76rem;color:var(--accent);margin:0;font-weight:600;">
                    Examples: &nbsp;MyPass@123 &nbsp;&middot;&nbsp; Hello$456 &nbsp;&middot;&nbsp; Secure#99
                </p>
            </div>
            """, unsafe_allow_html=True)
            render_strength_bar(new_pass or "", db_key="signup")
            confirm = st.text_input("Confirm Password", type="password", placeholder="........", key="su_confirm")
            st.write("")
            reg_btn = st.button("Create Account", type="primary", use_container_width=True)

        if reg_btn:
            blocked, secs = is_rate_limited("signup")
            if blocked:
                st.error(f"Too many registration attempts. Please wait {format_wait_time(secs)}.")
            else:
                score, _ = check_password_strength(new_pass or "")
                if not new_user.strip():
                    st.error("Please enter a username.")
                elif not new_pass:
                    st.error("Please enter a password.")
                elif score < 3:
                    st.error("Password is too weak - please meet at least 3 of the 5 requirements.")
                elif new_pass != confirm:
                    st.error("Passwords do not match.")
                else:
                    record_attempt("signup")
                    try:
                        conn = get_connection(); cur = conn.cursor()
                        cur.execute("INSERT INTO users(username, password) VALUES (%s,%s)", (new_user.strip(), hash_password(new_pass)))
                        conn.commit(); cur.close(); conn.close()
                        clear_attempts("signup")
                        st.success("Account created! Redirecting to sign in...")
                        time.sleep(1.2); st.session_state["auth_mode"] = "Login"; st.rerun()
                    except Exception as ex:
                        if "unique" in str(ex).lower(): st.error("That username is already taken.")
                        else: st.error("Registration failed. Please try again.")

        st.markdown('<div class="auth-switch">Already have an account?</div>', unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Sign in instead ->", use_container_width=True, key="go_login"):
                st.session_state["auth_mode"] = "Login"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# MAIN TABS
# ═══════════════════════════════════════════════════════════════
def render_home():
    lottie_anim = load_lottieurl("https://lottie.host/6a3ab8e3-b3c8-4e40-ad93-b7adfdc4a3eb/Ql1QsdyMTr.json")
    qr_count = len(get_user_qr_codes(st.session_state["user_id"]))
    left_h, right_h = st.columns([3, 2], gap="large")
    with left_h:
        st.markdown(f"""
        <div class="hero">
            <div class="hero-eyebrow"><i class="bi bi-lightning-charge-fill"></i>&nbsp;QR Studio</div>
            <div class="hero-title">Generate QR codes<br><span class="accent">in seconds.</span></div>
            <p class="hero-desc">A fast, elegant QR code generator built for the modern web. Create, save, and manage your QR codes - for links, contacts, or anything in between. Built with Python &amp; Streamlit.</p>
        </div>
        """, unsafe_allow_html=True)
    with right_h:
        if HAS_LOTTIE and lottie_anim:
            st_lottie(lottie_anim, height=220, key="hero_lottie")
        else:
            st.markdown(f'<div style="display:flex;justify-content:center;align-items:center;height:220px;">{QR_LOGO_SVG}</div>', unsafe_allow_html=True)

    st.markdown("---")
    s1, s2, s3 = st.columns(3)
    for col, (num, lbl) in zip([s1, s2, s3], [(str(qr_count),"QR Codes Saved"),("inf","Links Supported"),("PNG","Export Format")]):
        with col:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{e(num)}</div><div class="stat-lbl">{e(lbl)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="gen-card">', unsafe_allow_html=True)
    st.markdown('<div class="gen-card-title"><i class="bi bi-qr-code-scan" style="color:var(--accent);"></i> Generate a QR Code</div>', unsafe_allow_html=True)
    inp1, inp2 = st.columns(2)
    with inp1: qr_name = st.text_input("Name", placeholder="e.g. My GitHub Profile", key="home_qr_name")
    with inp2: qr_link = st.text_input("Link / Text", placeholder="https://example.com", key="home_qr_link")
    g_col, _ = st.columns([1, 3])
    with g_col: gen_btn = st.button("Generate", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if gen_btn:
        blocked, secs = is_rate_limited("generate")
        if blocked:
            st.warning(f"Slow down - too many generations. Please wait {format_wait_time(secs)}.")
        elif not qr_name.strip():
            st.warning("Please enter a name for your QR code.")
        elif not qr_link.strip():
            st.warning("Please enter a link or text.")
        else:
            record_attempt("generate")
            st.session_state["qr_bytes"] = generate_qr_bytes(qr_link.strip())
            st.session_state["qr_data_val"] = qr_link.strip()
            st.session_state["qr_name_val"] = qr_name.strip()
            st.session_state["show_save_ui"] = True

    if st.session_state["show_save_ui"] and st.session_state["qr_bytes"]:
        st.markdown("---")
        with st.container(border=True):
            prev_col, act_col = st.columns([1, 2], gap="large")
            with prev_col:
                st.image(st.session_state["qr_bytes"], caption=e(st.session_state["qr_name_val"]), width=200)
            with act_col:
                st.markdown(f"""
                <div class="meta-block">
                    <div class="meta-label">Name</div>
                    <div class="meta-val">{e(st.session_state["qr_name_val"])}</div>
                </div>
                <div class="meta-block">
                    <div class="meta-label">Link / Text</div>
                    <div class="meta-val-sm">{e(st.session_state["qr_data_val"])}</div>
                </div>
                """, unsafe_allow_html=True)
                save_col, cancel_col = st.columns(2)
                with save_col:
                    if st.button("Save QR Code", type="primary", use_container_width=True):
                        b64 = base64.b64encode(st.session_state["qr_bytes"]).decode()
                        save_qr_to_db(st.session_state["user_id"], st.session_state["qr_name_val"], st.session_state["qr_data_val"], b64)
                        st.success(f'Saved **{e(st.session_state["qr_name_val"])}**!'); _clear_preview(); st.rerun()
                with cancel_col:
                    if st.button("Discard", use_container_width=True): _clear_preview(); st.rerun()


def render_my_qr():
    qr_list = get_user_qr_codes(st.session_state["user_id"]); count = len(qr_list)
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">My QR Codes <span class="count-chip">{e(str(count))}</span></div>
        <div class="page-header-sub">Your saved QR codes - download or remove them at any time.</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    if not qr_list:
        st.markdown('<div class="empty-state"><i class="bi bi-inbox empty-icon"></i><h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">Nothing here yet</h3><p class="empty-text">Head over to <strong>Home</strong> to generate your first QR code.</p></div>', unsafe_allow_html=True)
        return
    cols = st.columns(3)
    for idx, (qr_id, name, qr_data, qr_img_b64, created_at) in enumerate(qr_list):
        qr_bytes = base64.b64decode(qr_img_b64)
        short_link = qr_data if len(qr_data) <= 40 else qr_data[:37] + "..."
        with cols[idx % 3]:
            with st.container(border=True):
                st.image(qr_bytes, use_container_width=True)
                st.markdown(f"""
                <div class="qr-card-meta">
                    <div class="qr-name">{e(name)}</div>
                    <div class="qr-link"><i class="bi bi-link-45deg"></i> {e(short_link)}</div>
                    <div class="qr-date"><i class="bi bi-calendar3"></i> {e(created_at.strftime("%b %d, %Y  %H:%M"))}</div>
                </div>
                """, unsafe_allow_html=True)
                st.write("")
                dl_c, del_c = st.columns(2)
                with dl_c: st.download_button("Download", data=qr_bytes, file_name=f"{name}.png", mime="image/png", use_container_width=True, key=f"myqr_dl_{qr_id}")
                with del_c:
                    if st.button("Delete", key=f"myqr_del_{qr_id}", use_container_width=True):
                        delete_qr_from_db(qr_id, st.session_state["user_id"]); st.rerun()


def render_history():
    qr_list = get_user_qr_codes(st.session_state["user_id"]); count = len(qr_list)
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">History <span class="count-chip">{e(str(count))}</span></div>
        <div class="page-header-sub">A full log of every QR code you've saved - newest first.</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    if not qr_list:
        st.markdown('<div class="empty-state"><i class="bi bi-clock-history empty-icon"></i><h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">No history yet</h3><p class="empty-text">Generate your first QR code from <strong>Home</strong>.</p></div>', unsafe_allow_html=True)
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
                with dl2: st.download_button("Download", data=qr_bytes, file_name=f"{name}.png", mime="image/png", key=f"hist_dl_{qr_id}")
                with del2:
                    if st.button("Delete", key=f"hist_del_{qr_id}"):
                        delete_qr_from_db(qr_id, st.session_state["user_id"]); st.rerun()


# ═══════════════════════════════════════════════════════════════
# PHOTO QR PAGE
# ═══════════════════════════════════════════════════════════════
def render_photo_qr():
    # Camera styling: landscape on desktop, portrait on mobile,
    # circular shutter button at bottom-center of frame
    st.markdown("""
    <style>
    [data-testid="stCameraInput"] { position: relative !important; }
    [data-testid="stCameraInput"] video,
    [data-testid="stCameraInput"] img {
        width: 100% !important;
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        border-radius: 12px 12px 0 0 !important;
        display: block !important;
    }
    @media (max-width: 640px) {
        [data-testid="stCameraInput"] video,
        [data-testid="stCameraInput"] img {
            aspect-ratio: 9 / 16 !important;
        }
    }
    [data-testid="stCameraInputButton"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        background: rgba(13,17,23,0.80) !important;
        border-radius: 0 0 12px 12px !important;
        padding: 16px 0 !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        border-top: none !important;
    }
    [data-testid="stCameraInputButton"] button {
        width: 64px !important;
        height: 64px !important;
        border-radius: 50% !important;
        border: 4px solid rgba(255,255,255,0.88) !important;
        background: rgba(240,136,62,0.18) !important;
        box-shadow: 0 0 0 3px rgba(240,136,62,0.38), inset 0 0 0 6px rgba(255,255,255,0.10) !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        font-size: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stCameraInputButton"] button:hover {
        background: rgba(240,136,62,0.38) !important;
        box-shadow: 0 0 0 4px rgba(240,136,62,0.58), inset 0 0 0 6px rgba(255,255,255,0.16) !important;
        transform: scale(1.07) !important;
    }
    [data-testid="stCameraInputButton"] button:active {
        background: rgba(240,136,62,0.68) !important;
        transform: scale(0.95) !important;
    }
    [data-testid="stCameraInputButton"] span,
    [data-testid="stCameraInputButton"] p { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header" style="padding-bottom:8px;">
        <div class="page-header-title">PhotoQR</div>
        <div class="page-header-sub">Capture a photo and turn it into a shareable QR code.</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    tab_create, tab_mine = st.tabs(["Capture & Create", "My Photo QRs"])

    with tab_create:
        st.markdown("""
        <div class="meta-block" style="margin-bottom:6px;">
            <div class="meta-label"><i class="bi bi-camera-fill" style="color:var(--accent);"></i>&nbsp;Step 1 - Take a Photo</div>
            <div class="meta-val-sm">Click the circular shutter button inside the frame to capture. Works on phones (portrait) and desktops (landscape).</div>
        </div>
        """, unsafe_allow_html=True)

        cam_shot = st.camera_input("Take a photo", key="pqr_camera", label_visibility="collapsed")

        st.markdown("""
        <div style="margin-top:6px;margin-bottom:14px;">
            <p style="font-family:var(--font-b);font-size:.75rem;color:var(--tx-3);margin:0;">
                <i class="bi bi-info-circle" style="margin-right:4px;"></i>
                If the camera doesn't appear: allow camera access in your browser settings, or try Chrome / Safari.
                A stable internet connection is required for the QR viewer link to work.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Caption directly below the camera frame
        st.markdown("""
        <div class="meta-block" style="margin-bottom:4px;">
            <div class="meta-label"><i class="bi bi-chat-left-text" style="color:var(--accent);"></i>&nbsp;Caption (optional)</div>
        </div>
        """, unsafe_allow_html=True)
        caption_val = st.text_input("Caption", placeholder="e.g. My vacation photo", key="pqr_caption", label_visibility="collapsed")

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        # Visibility + PIN below caption
        with st.container(border=True):
            st.markdown("""
            <div class="meta-block" style="margin-bottom:8px;">
                <div class="meta-label"><i class="bi bi-sliders" style="color:var(--accent);"></i>&nbsp;Step 2 - Visibility Settings</div>
            </div>
            """, unsafe_allow_html=True)

            visibility_val = st.radio(
                "Visibility",
                options=["public", "private"],
                format_func=lambda x: "Public - anyone with the QR can view" if x == "public" else "Private - requires a PIN to view",
                key="pqr_visibility",
            )

            pin_val = ""; pin_val2 = ""
            if visibility_val == "private":
                st.markdown('<div class="meta-block" style="margin-top:8px;"><div class="meta-label">Set a PIN for this photo</div></div>', unsafe_allow_html=True)
                pin_col1, pin_col2 = st.columns(2)
                with pin_col1: pin_val  = st.text_input("PIN", type="password", placeholder="4-12 characters", key="pqr_pin")
                with pin_col2: pin_val2 = st.text_input("Confirm PIN", type="password", placeholder="Re-enter PIN", key="pqr_pin2")

            st.write("")
            create_btn = st.button("Generate PhotoQR", type="primary", use_container_width=True, key="pqr_create_btn")

        if create_btn:
            if cam_shot is None:
                st.warning("Please take a photo first using the camera above.")
            elif visibility_val == "private" and not pin_val:
                st.warning("Please set a PIN for your private photo.")
            elif visibility_val == "private" and pin_val != pin_val2:
                st.error("PINs do not match. Please re-enter.")
            elif visibility_val == "private" and (len(pin_val) < 4 or len(pin_val) > 12):
                st.warning("PIN must be between 4 and 12 characters.")
            else:
                with st.spinner("Generating your PhotoQR..."):
                    img_bytes = cam_shot.getvalue()
                    photo_b64 = base64.b64encode(img_bytes).decode()
                    new_id = save_photo_qr_to_db(user_id=st.session_state["user_id"], photo_b64=photo_b64, caption=caption_val, visibility=visibility_val, pin=pin_val if visibility_val == "private" else "")
                    base_url = get_base_url(); viewer_url = f"{base_url}/?view={new_id}"
                    qr_img = qrcode.make(viewer_url); qr_buf = io.BytesIO(); qr_img.save(qr_buf, format="PNG")
                    qr_bytes = qr_buf.getvalue(); qr_b64 = base64.b64encode(qr_bytes).decode()
                    save_qr_to_db(user_id=st.session_state["user_id"], name=f"PhotoQR - {caption_val or 'Untitled'}", qr_data=viewer_url, qr_image_b64=qr_b64)

                st.success("PhotoQR created and saved!")
                st.markdown("---")
                res_l, res_r = st.columns([1, 1], gap="large")
                with res_l:
                    st.markdown('<div class="meta-block"><div class="meta-label">Your QR Code</div><div class="meta-val-sm">Scan this to view the photo</div></div>', unsafe_allow_html=True)
                    st.image(qr_bytes, width=220)
                    st.download_button("Download QR Code", data=qr_bytes, file_name=f"photoqr_{new_id}.png", mime="image/png", key=f"dl_new_qr_{new_id}")
                with res_r:
                    vis_icon  = "bi-globe2" if visibility_val == "public" else "bi-lock-fill"
                    vis_color = "var(--green)" if visibility_val == "public" else "var(--accent)"
                    st.markdown(f"""
                    <div class="meta-block">
                        <div class="meta-label">Viewer Link</div>
                        <div class="meta-val-sm" style="word-break:break-all;">{e(viewer_url)}</div>
                    </div>
                    <div class="meta-block" style="margin-top:14px;">
                        <div class="meta-label">Visibility</div>
                        <div class="meta-val"><i class="bi {vis_icon}" style="color:{vis_color};margin-right:6px;"></i>{e(visibility_val.capitalize())}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if visibility_val == "private":
                        st.info("Share your PIN separately with people you want to give access to.")

    with tab_mine:
        photos = get_user_photo_qrs(st.session_state["user_id"]); base_url = get_base_url()
        if not photos:
            st.markdown('<div class="empty-state"><i class="bi bi-camera empty-icon"></i><h3 style="color:var(--tx-2);font-family:var(--font-b);font-weight:600;">No PhotoQRs yet</h3><p class="empty-text">Go to <strong>Capture &amp; Create</strong> to make your first one.</p></div>', unsafe_allow_html=True)
        else:
            cols = st.columns(3)
            for idx, (pid, caption, visibility, created_at) in enumerate(photos):
                viewer_url = f"{base_url}/?view={pid}"
                qr_img = qrcode.make(viewer_url); qr_buf = io.BytesIO(); qr_img.save(qr_buf, format="PNG"); qr_bytes = qr_buf.getvalue()
                vis_icon  = "bi-globe2" if visibility == "public" else "bi-lock-fill"
                vis_color = "var(--green)" if visibility == "public" else "var(--accent)"
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.image(qr_bytes, use_container_width=True)
                        st.markdown(f"""
                        <div class="qr-card-meta">
                            <div class="qr-name">{e(caption) if caption else "<em>Untitled</em>"}</div>
                            <div class="qr-link"><i class="bi {vis_icon}" style="color:{vis_color};"></i>&nbsp;{e(visibility.capitalize())}</div>
                            <div class="qr-date"><i class="bi bi-calendar3"></i> {e(created_at.strftime("%b %d, %Y  %H:%M"))}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.write("")
                        dl_c, view_c, del_c = st.columns(3)
                        with dl_c: st.download_button("QR", data=qr_bytes, file_name=f"photoqr_{pid}.png", mime="image/png", use_container_width=True, key=f"pqr_dl_{pid}")
                        with view_c:
                            if st.button("View", key=f"pqr_view_{pid}", use_container_width=True):
                                st.query_params["view"] = str(pid); st.rerun()
                        with del_c:
                            if st.button("Del", key=f"pqr_del_{pid}", use_container_width=True):
                                delete_photo_qr_from_db(pid, st.session_state["user_id"]); st.rerun()


# ═══════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════
params  = st.query_params
view_id = params.get("view", None)

if view_id is not None:
    try:
        render_sidebar(is_viewer=True)
        render_photo_viewer(int(view_id))
    except (ValueError, TypeError):
        st.error("Invalid photo link.")
elif not st.session_state["logged_in"]:
    if st.session_state["auth_mode"] == "Signup": render_signup()
    else: render_login()
else:
    render_sidebar()
    _tab = st.session_state["active_tab"]
    if   _tab == "Home":    render_home()
    elif _tab == "MyQR":    render_my_qr()
    elif _tab == "History": render_history()
    elif _tab == "PhotoQR": render_photo_qr()