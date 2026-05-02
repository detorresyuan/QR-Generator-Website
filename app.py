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
# CSS
# ═══════════════════════════════════════════════════════════════
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
        with open(css_path, encoding="utf-8-sig") as fh:  # utf-8-sig strips hidden BOM
            return fh.read()
    except FileNotFoundError:
        return ""

st.markdown(GLOBAL_CSS_LINKS, unsafe_allow_html=True)
st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)
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


def _db_cfg() -> dict:
    """
    Pull connection details from st.secrets (preferred) with a
    fallback to environment variables so the app still works in
    non-Streamlit runners such as pytest or Docker.
    """
    try:
        s = st.secrets["db"]
        return {
            "dbname":   s["dbname"],
            "user":     s["user"],
            "password": s["password"],
            "host":     s["host"],
            "port":     str(s["port"]),
        }
    except Exception:
        # env-var fallback (e.g. Docker / CI)
        return {
            "dbname":   os.environ.get("DB_NAME",     "postgres"),
            "user":     os.environ.get("DB_USER",     "postgres"),
            "password": os.environ.get("DB_PASSWORD", ""),
            "host":     os.environ.get("DB_HOST",     "localhost"),
            "port":     os.environ.get("DB_PORT",     "5432"),
        }


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

    # ── Core tables ──────────────────────────────────────────────────────────
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

    cur.execute("ALTER TABLE qr_codes ENABLE ROW LEVEL SECURITY;")

    cur.execute("""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE tablename = 'qr_codes'
            AND   policyname = 'user_isolation'
          ) THEN
            CREATE POLICY user_isolation ON qr_codes
              USING (
                user_id = (
                  current_setting('app.current_user_id', true)::INTEGER
                )
              );
          END IF;
        END
        $$;
    """)

    conn.commit(); cur.close(); conn.close()
    return True

init_db()


# ── Authenticated connection: sets the RLS context variable ────────────────────
def get_authed_connection(user_id: int):
    """
    Returns a connection with app.current_user_id set so that
    the RLS policy on qr_codes is scoped to this user only.
    """
    conn = get_connection()
    cur  = conn.cursor()
    # SET LOCAL scopes the variable to the current transaction
    cur.execute("SET LOCAL app.current_user_id = %s;", (user_id,))
    cur.close()
    return conn


# ── QR list with 30-second TTL cache ───────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _fetch_qr_codes(user_id: int):
    """Fetch via an authed connection so RLS is active."""
    conn = get_authed_connection(user_id)
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, name, qr_data, qr_image, created_at
        FROM qr_codes
        WHERE user_id = %s          -- belt-and-suspenders alongside RLS
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_user_qr_codes(user_id: int):
    return _fetch_qr_codes(user_id)

def _bust_cache():
    _fetch_qr_codes.clear()

def save_qr_to_db(user_id: int, name: str, qr_data: str, qr_image_b64: str):
    conn = get_authed_connection(user_id)
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO qr_codes (user_id, name, qr_data, qr_image) VALUES (%s,%s,%s,%s)",
        (user_id, name, qr_data, qr_image_b64),
    )
    conn.commit()
    cur.close(); conn.close()
    _bust_cache()

def delete_qr_from_db(qr_id: int, user_id: int):
    """
    Always pass user_id so the WHERE clause is explicit even if
    the RLS policy were ever disabled during maintenance.
    """
    conn = get_authed_connection(user_id)
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM qr_codes WHERE id = %s AND user_id = %s",
        (qr_id, user_id),
    )
    conn.commit()
    cur.close(); conn.close()
    _bust_cache()


# ── Auth helpers ────────────────────────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def lookup_user(username: str):
    """Returns (id, hashed_password) or None."""
    conn = get_connection(); cur = conn.cursor()
    cur.execute(
        "SELECT id, password FROM users WHERE username = %s",
        (username.strip(),),
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


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


def e(value) -> str:
    """
    Escape a value for safe embedding inside HTML.
    Converts  <  >  "  '  &  to their HTML entities.
    """
    return html.escape(str(value), quote=True)


_RATE_CFG = {
    "login":    {"max": 5,  "window": 60,  "lockout": 300},   # 5 tries / 60s → 5-min lockout
    "signup":   {"max": 3,  "window": 300, "lockout": 600},   # 3 tries / 5min → 10-min lockout
    "generate": {"max": 20, "window": 60,  "lockout": 30},    # 20 generates / 60s → 30s cooldown
}

def _rate_key(action: str) -> str:
    return f"_rl_{action}"

def is_rate_limited(action: str) -> tuple[bool, int]:
    """
    Returns (blocked: bool, seconds_remaining: int).
    Call this before executing the action.
    """
    cfg  = _RATE_CFG[action]
    key  = _rate_key(action)
    now  = time.time()

    if key not in st.session_state:
        st.session_state[key] = {"attempts": [], "locked_until": 0}

    rl = st.session_state[key]

    # Still in lockout?
    if now < rl["locked_until"]:
        return True, int(rl["locked_until"] - now)

    # Prune attempts outside the window
    rl["attempts"] = [t for t in rl["attempts"] if now - t < cfg["window"]]

    if len(rl["attempts"]) >= cfg["max"]:
        rl["locked_until"] = now + cfg["lockout"]
        return True, cfg["lockout"]

    return False, 0

def record_attempt(action: str):
    """Call this every time the user triggers the action (success or fail)."""
    key = _rate_key(action)
    if key not in st.session_state:
        st.session_state[key] = {"attempts": [], "locked_until": 0}
    st.session_state[key]["attempts"].append(time.time())

def clear_attempts(action: str):
    """Call on successful login/signup to reset the counter."""
    key = _rate_key(action)
    st.session_state[key] = {"attempts": [], "locked_until": 0}


# ═══════════════════════════════════════════════════════════════
# PASSWORD STRENGTH
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
                    f'<i class="bi bi-x-circle-fill" style="color:#f85149;margin-right:6px;"></i>{e(m)}',
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
    "user_id":      None,   # ← stored so we never re-query it
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

        # ── User chip — e() prevents XSS via crafted usernames ────────────────
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

        with st.expander("Recent QR Codes"):
            recent = get_user_qr_codes(st.session_state["user_id"])[:5]
            if recent:
                for _, name, _, _, ts in recent:
                    safe_name = e(name)
                    truncated = (safe_name[:21] + "…") if len(safe_name) > 21 else safe_name
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
        st.markdown(f'<div class="auth-logo">{QR_LOGO_SVG}</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">QR Studio</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-tagline">A QR code, anytime, anywhere.</div>',
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            username  = st.text_input("Username", placeholder="Enter your username")
            password  = st.text_input("Password", type="password", placeholder="••••••••")
            st.write("")
            submitted = st.form_submit_button(
                "Sign In", type="primary", use_container_width=True,
            )

        if submitted:
            # ── Rate-limit check ───────────────────────────────────────────────
            blocked, secs = is_rate_limited("login")
            if blocked:
                st.error(
                    f"Too many failed attempts. Please wait {secs} seconds before trying again."
                )
            elif not username.strip() or not password:
                st.error("Please enter your username and password.")
            else:
                record_attempt("login")
                result = lookup_user(username)
                if result and verify_password(password, result[1]):
                    clear_attempts("login")
                    st.session_state["logged_in"] = True
                    st.session_state["username"]   = username.strip()
                    st.session_state["user_id"]    = result[0]
                    st.session_state["active_tab"] = "Home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        st.markdown(
            "<div class=\"auth-switch\">Don't have an account?</div>",
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
        st.markdown('<div class="auth-title">Create Account</div>', unsafe_allow_html=True)
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
            reg_btn  = st.button("Create Account", type="primary", use_container_width=True)

        if reg_btn:
            # ── Rate-limit check ───────────────────────────────────────────────
            blocked, secs = is_rate_limited("signup")
            if blocked:
                st.error(
                    f"Too many registration attempts. Please wait {secs} seconds."
                )
            else:
                score, _ = check_password_strength(new_pass or "")
                if not new_user.strip():
                    st.error("Please enter a username.")
                elif not new_pass:
                    st.error("Please enter a password.")
                elif score < 3:
                    st.error(
                        "Password is too weak — please meet at least 3 of the 5 requirements."
                    )
                elif new_pass != confirm:
                    st.error("Passwords do not match.")
                else:
                    record_attempt("signup")
                    try:
                        conn = get_connection(); cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO users(username, password) VALUES (%s,%s)",
                            (new_user.strip(), hash_password(new_pass)),
                        )
                        conn.commit(); cur.close(); conn.close()
                        clear_attempts("signup")
                        st.success("Account created! Redirecting to sign in…")
                        time.sleep(1.2)
                        st.session_state["auth_mode"] = "Login"
                        st.rerun()
                    except Exception as ex:
                        if "unique" in str(ex).lower():
                            st.error("That username is already taken.")
                        else:
                            # Don't expose raw DB error messages to the user
                            st.error("Registration failed. Please try again.")

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
    qr_count = len(get_user_qr_codes(st.session_state["user_id"]))

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
                <div class="stat-num">{e(num)}</div>
                <div class="stat-lbl">{e(lbl)}</div>
            </div>""", unsafe_allow_html=True)

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
        qr_name = st.text_input("Name", placeholder="e.g. My GitHub Profile", key="home_qr_name")
    with inp2:
        qr_link = st.text_input("Link / Text", placeholder="https://example.com", key="home_qr_link")

    g_col, _ = st.columns([1, 3])
    with g_col:
        gen_btn = st.button("Generate", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if gen_btn:
        # ── Rate-limit QR generation ───────────────────────────────────────────
        blocked, secs = is_rate_limited("generate")
        if blocked:
            st.warning(f"Slow down — too many generations. Wait {secs}s.")
        elif not qr_name.strip():
            st.warning("Please enter a name for your QR code.")
        elif not qr_link.strip():
            st.warning("Please enter a link or text.")
        else:
            record_attempt("generate")
            st.session_state["qr_bytes"]     = generate_qr_bytes(qr_link.strip())
            st.session_state["qr_data_val"]  = qr_link.strip()
            st.session_state["qr_name_val"]  = qr_name.strip()
            st.session_state["show_save_ui"] = True

    if st.session_state["show_save_ui"] and st.session_state["qr_bytes"]:
        st.markdown("---")
        with st.container(border=True):
            prev_col, act_col = st.columns([1, 2], gap="large")

            with prev_col:
                st.image(
                    st.session_state["qr_bytes"],
                    caption=e(st.session_state["qr_name_val"]),
                    width=200,
                )

            with act_col:
                # e() escapes name and data before they touch the DOM
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
                        save_qr_to_db(
                            st.session_state["user_id"],
                            st.session_state["qr_name_val"],
                            st.session_state["qr_data_val"],
                            b64,
                        )
                        st.success(f'Saved **{e(st.session_state["qr_name_val"])}**!')
                        _clear_preview()
                        st.rerun()
                with cancel_col:
                    if st.button("Discard", use_container_width=True):
                        _clear_preview()
                        st.rerun()


def render_my_qr():
    qr_list = get_user_qr_codes(st.session_state["user_id"])
    count   = len(qr_list)

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">
            My QR Codes
            <span class="count-chip">{e(str(count))}</span>
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
                # ── e() prevents <script> inside name/link from executing ──────
                st.markdown(f"""
                <div class="qr-card-meta">
                    <div class="qr-name">{e(name)}</div>
                    <div class="qr-link">
                        <i class="bi bi-link-45deg"></i> {e(short_link)}
                    </div>
                    <div class="qr-date">
                        <i class="bi bi-calendar3"></i>
                        {e(created_at.strftime("%b %d, %Y  %H:%M"))}
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
                    if st.button("Delete", key=f"myqr_del_{qr_id}", use_container_width=True):
                        delete_qr_from_db(qr_id, st.session_state["user_id"])
                        st.rerun()


def render_history():
    qr_list = get_user_qr_codes(st.session_state["user_id"])
    count   = len(qr_list)

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-title">
            History
            <span class="count-chip">{e(str(count))}</span>
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
                    <div class="meta-val">{e(name)}</div>
                </div>
                <div class="meta-block">
                    <div class="meta-label">Link / Text</div>
                    <div class="meta-val-sm">{e(qr_data)}</div>
                </div>
                <div class="meta-block">
                    <div class="meta-label">Created</div>
                    <div class="meta-val-sm">{e(created_at.strftime("%B %d, %Y at %H:%M"))}</div>
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
                    if st.button("Delete", key=f"hist_del_{qr_id}"):
                        delete_qr_from_db(qr_id, st.session_state["user_id"])
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