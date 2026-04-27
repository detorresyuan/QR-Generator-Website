import streamlit as st
import psycopg2
import bcrypt
import requests
import qrcode
import io
import base64
import re
from datetime import datetime
from streamlit_lottie import st_lottie

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Group 2 QR Generator", page_icon=":cat_face:", layout="wide")

@st.cache_data(show_spinner=False)
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

lottie_coding = load_lottieurl(
    "https://lottie.host/6a3ab8e3-b3c8-4e40-ad93-b7adfdc4a3eb/Ql1QsdyMTr.json"
)

# ============================================================
# DATABASE FUNCTIONS
# ============================================================
def get_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="group2",
        host="localhost",
        port="5432"
    )

@st.cache_resource(show_spinner=False)
def init_db():
    """Auto-create tables on first startup. Cached so it only runs once."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            qr_data TEXT NOT NULL,
            qr_image TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    return True

init_db()  # runs once per server session

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def save_qr_to_db(username, name, qr_data, qr_image_b64):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    if user:
        cur.execute(
            "INSERT INTO qr_codes (user_id, name, qr_data, qr_image) VALUES (%s, %s, %s, %s)",
            (user[0], name, qr_data, qr_image_b64)
        )
        conn.commit()
    cur.close()
    conn.close()

def get_user_qr_codes(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT qc.id, qc.name, qc.qr_data, qc.qr_image, qc.created_at
        FROM qr_codes qc
        JOIN users u ON qc.user_id = u.id
        WHERE u.username = %s
        ORDER BY qc.created_at DESC
    """, (username,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

def delete_qr_from_db(qr_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM qr_codes WHERE id = %s", (qr_id,))
    conn.commit()
    cur.close()
    conn.close()

# ============================================================
# PASSWORD STRENGTH HELPERS
# ============================================================
def check_password_strength(password):
    checks = [
        (len(password) >= 8,                          "At least 8 characters"),
        (bool(re.search(r'[A-Z]', password)),         "At least one uppercase letter (A–Z)"),
        (bool(re.search(r'[a-z]', password)),         "At least one lowercase letter (a–z)"),
        (bool(re.search(r'\d', password)),            "At least one number (0–9)"),
        (bool(re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\\/_\-+=~`]', password)),
                                                       "At least one special character (!@#$…)"),
    ]
    score = sum(1 for passed, _ in checks if passed)
    missing = [msg for passed, msg in checks if not passed]
    return score, missing

def strength_info(score):
    """Returns (label, hex_color, percent)."""
    levels = [
        (0,  "No input",    "#cccccc",  0),
        (1,  "Very Weak",   "#e53935", 20),
        (2,  "Weak",        "#fb8c00", 40),
        (3,  "Moderate",    "#fdd835", 60),
        (4,  "Strong",      "#7cb342", 80),
        (5,  "Very Strong", "#2e7d32", 100),
    ]
    entry = next((l for l in levels if l[0] == score), levels[0])
    return entry[1], entry[2], entry[3]

def render_strength_bar(password):
    if not password:
        return
    score, missing = check_password_strength(password)
    label, color, pct = strength_info(score)
    st.markdown(f"""
    <div style="margin-top:6px; margin-bottom:4px;">
        <div style="background:#e0e0e0; border-radius:8px; height:10px; width:100%;">
            <div style="background:{color}; border-radius:8px; height:10px;
                        width:{pct}%; transition:width 0.35s ease;"></div>
        </div>
        <p style="color:{color}; margin:5px 0 2px; font-weight:600; font-size:0.9rem;">
            Password Strength: {label}
        </p>
    </div>
    """, unsafe_allow_html=True)
    if missing:
        with st.expander("❗ Requirements not yet met", expanded=True):
            for m in missing:
                st.markdown(f"- ❌ {m}")
    else:
        st.markdown("✅ All password requirements met!")

# ============================================================
# QR CODE GENERATION (in-memory — no temp file, faster)
# ============================================================
def generate_qr_bytes(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ============================================================
# SESSION STATE DEFAULTS
# ============================================================
_DEFAULTS = {
    "logged_in":        False,
    "username":         "",
    "active_tab":       "Home",
    "qr_bytes":         None,
    "qr_data_val":      "",
    "qr_name_val":      "",
    "show_save_ui":     False,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("🐱 Group 2 QR")

if not st.session_state["logged_in"]:
    # ---- not logged in ----
    auth_choice = st.sidebar.selectbox("Go to", ["Login", "Signup"])

else:
    # ---- logged in ----
    st.sidebar.markdown(f"👤 **{st.session_state['username']}**")
    st.sidebar.write("---")

    nav = st.sidebar.radio(
        "Navigate",
        ["🏠  Home", "📂  My QR Codes", "📜  History"],
        label_visibility="collapsed",
    )

    # Map radio label → internal tab key
    _tab_map = {
        "🏠  Home":       "Home",
        "📂  My QR Codes": "MyQR",
        "📜  History":    "History",
    }
    if _tab_map[nav] != st.session_state["active_tab"]:
        st.session_state["active_tab"] = _tab_map[nav]
        # reset pending QR when switching tabs
        st.session_state["show_save_ui"] = False
        st.session_state["qr_bytes"] = None

    st.sidebar.write("---")

    # ---- mini history preview in sidebar ----
    st.sidebar.markdown("**🕑 Recent QR Codes**")
    _recent = get_user_qr_codes(st.session_state["username"])[:5]
    if _recent:
        for _, _name, _link, _, _ts in _recent:
            st.sidebar.markdown(
                f"• **{_name}**  \n"
                f"  <span style='font-size:0.75rem;color:gray;'>{_ts.strftime('%b %d, %Y')}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.sidebar.caption("No QR codes saved yet.")

    st.sidebar.write("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        for _k, _v in _DEFAULTS.items():
            st.session_state[_k] = _v
        st.rerun()

    auth_choice = None  # not on an auth page

# ============================================================
# AUTH PAGES  (only shown when not logged in)
# ============================================================
if not st.session_state["logged_in"]:

    # ---- SIGNUP ----
    if auth_choice == "Signup":
        st.subheader("Create New Account")

        new_user = st.text_input("Username", key="su_user")
        new_pass = st.text_input("Password", type="password", key="su_pass")

        # live password strength bar
        render_strength_bar(new_pass)

        confirm_pass = st.text_input("Confirm Password", type="password", key="su_confirm")

        if st.button("Register", type="primary"):
            score, missing = check_password_strength(new_pass)
            if not new_user.strip():
                st.error("Please enter a username.")
            elif not new_pass:
                st.error("Please enter a password.")
            elif score < 3:
                st.error(
                    "Password is too weak. Please satisfy at least 3 of the 5 requirements shown above."
                )
            elif new_pass != confirm_pass:
                st.error("Passwords do not match.")
            else:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    hashed_pw = hash_password(new_pass)
                    cur.execute(
                        "INSERT INTO users(username, password) VALUES (%s, %s)",
                        (new_user.strip(), hashed_pw),
                    )
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("✅ Account created! Please go to Login.")
                except Exception as e:
                    st.error(f"Database Error: {e}")

    # ---- LOGIN ----
    elif auth_choice == "Login":
        st.subheader("Login to Access QR Generator")

        username = st.text_input("Username", key="li_user")
        password = st.text_input("Password", type="password", key="li_pass")

        if st.button("Login", type="primary"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT password FROM users WHERE username = %s", (username,))
            result = cur.fetchone()
            cur.close()
            conn.close()

            if result and verify_password(password, result[0]):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["active_tab"] = "Home"
                st.rerun()
            else:
                st.error("Invalid username or password.")

    else:
        st.warning("Please Login or Signup from the sidebar to access the QR Generator.")

# ============================================================
# MAIN APP  (only shown when logged in)
# ============================================================
else:
    tab = st.session_state["active_tab"]

    # ===========================================================
    # TAB: HOME
    # ===========================================================
    if tab == "Home":
        # --- Hero ---
        with st.container():
            st.subheader(f"Welcome back, {st.session_state['username']}! 🐱")
            st.title("QR Code Generator")
            st.write(
                "This is a group project that utilizes the power of Python using "
                "Streamlit while also integrating PostgreSQL."
            )
            st.write("[Learn More >](https://www.youtube.com/watch?v=VqgUkExPvLY)")

        # --- What is this section ---
        with st.container():
            st.write("---")
            left_col, right_col = st.columns(2)
            with left_col:
                st.header("What is this?")
                st.write("##")
                st.write(
                    "This is a QR Code generator that generates QR codes from any link "
                    "you provide. It uses the power of Python and Streamlit to create a "
                    "simple and easy-to-use interface for users to generate QR codes."
                )
            with right_col:
                st_lottie(lottie_coding, height=300, key="coding_anim")

        # --- Generator Section ---
        with st.container():
            st.write("---")
            st.title("Generate Your QR Code")

            qr_name_input = st.text_input(
                "📛 QR Code Name",
                placeholder="e.g. My GitHub Profile",
                key="home_qr_name",
            )
            qr_link_input = st.text_input(
                "🔗 Link / Text for QR Code",
                placeholder="https://example.com",
                key="home_qr_link",
            )

            if st.button("⚡ Generate QR Code", type="primary"):
                if not qr_name_input.strip():
                    st.warning("Please enter a name for your QR code.")
                elif not qr_link_input.strip():
                    st.warning("Please enter a link or text for the QR code.")
                else:
                    # Generate in-memory (fast — no disk I/O)
                    st.session_state["qr_bytes"]    = generate_qr_bytes(qr_link_input.strip())
                    st.session_state["qr_data_val"] = qr_link_input.strip()
                    st.session_state["qr_name_val"] = qr_name_input.strip()
                    st.session_state["show_save_ui"] = True

            # --- Save / Cancel UI ---
            if st.session_state["show_save_ui"] and st.session_state["qr_bytes"]:
                st.write("---")
                preview_col, action_col = st.columns([1, 2])

                with preview_col:
                    st.image(
                        st.session_state["qr_bytes"],
                        caption=st.session_state["qr_name_val"],
                        width=250,
                    )

                with action_col:
                    st.markdown(f"**Name:** {st.session_state['qr_name_val']}")
                    st.markdown(f"**Link:** {st.session_state['qr_data_val']}")
                    st.write("")

                    save_btn, cancel_btn = st.columns(2)

                    with save_btn:
                        if st.button("💾 Save", type="primary", use_container_width=True):
                            qr_b64 = base64.b64encode(
                                st.session_state["qr_bytes"]
                            ).decode()
                            save_qr_to_db(
                                st.session_state["username"],
                                st.session_state["qr_name_val"],
                                st.session_state["qr_data_val"],
                                qr_b64,
                            )
                            st.success(
                                f"✅ QR Code **{st.session_state['qr_name_val']}** saved!"
                            )
                            # reset state
                            st.session_state["show_save_ui"] = False
                            st.session_state["qr_bytes"]     = None
                            st.session_state["qr_data_val"]  = ""
                            st.session_state["qr_name_val"]  = ""
                            st.rerun()

                    with cancel_btn:
                        if st.button("❌ Cancel", use_container_width=True):
                            st.session_state["show_save_ui"] = False
                            st.session_state["qr_bytes"]     = None
                            st.session_state["qr_data_val"]  = ""
                            st.session_state["qr_name_val"]  = ""
                            st.rerun()

    # ===========================================================
    # TAB: MY QR CODES
    # ===========================================================
    elif tab == "MyQR":
        st.title("📂 My QR Codes")
        st.write("---")

        qr_list = get_user_qr_codes(st.session_state["username"])

        if not qr_list:
            st.info("You have no saved QR codes yet. Head to **🏠 Home** to generate one!")
        else:
            st.markdown(f"**{len(qr_list)} QR code(s) saved**")
            st.write("")

            cols = st.columns(3)
            for idx, (qr_id, name, qr_data, qr_img_b64, created_at) in enumerate(qr_list):
                qr_bytes = base64.b64decode(qr_img_b64)
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.image(qr_bytes, use_container_width=True)
                        st.markdown(f"**{name}**")
                        short_link = qr_data if len(qr_data) <= 38 else qr_data[:35] + "…"
                        st.caption(f"🔗 {short_link}")
                        st.caption(f"📅 {created_at.strftime('%b %d, %Y  %H:%M')}")

                        dl_col, del_col = st.columns(2)
                        with dl_col:
                            st.download_button(
                                "⬇️ Download",
                                data=qr_bytes,
                                file_name=f"{name}.png",
                                mime="image/png",
                                use_container_width=True,
                                key=f"myqr_dl_{qr_id}",
                            )
                        with del_col:
                            if st.button(
                                "🗑️ Delete",
                                key=f"myqr_del_{qr_id}",
                                use_container_width=True,
                            ):
                                delete_qr_from_db(qr_id)
                                st.rerun()

    # ===========================================================
    # TAB: HISTORY
    # ===========================================================
    elif tab == "History":
        st.title("📜 QR Code History")
        st.write("---")

        qr_list = get_user_qr_codes(st.session_state["username"])

        if not qr_list:
            st.info("No history yet. Generate your first QR code from **🏠 Home**!")
        else:
            st.markdown(f"**Total QR Codes Created: {len(qr_list)}**")
            st.write("")

            for qr_id, name, qr_data, qr_img_b64, created_at in qr_list:
                qr_bytes = base64.b64decode(qr_img_b64)
                with st.expander(
                    f"📌  {name}   —   {created_at.strftime('%B %d, %Y  %H:%M')}",
                    expanded=False,
                ):
                    left, right = st.columns([1, 2])
                    with left:
                        st.image(qr_bytes, width=160)
                    with right:
                        st.markdown(f"**Name:** {name}")
                        st.markdown(f"**Link / Text:** {qr_data}")
                        st.markdown(
                            f"**Created:** {created_at.strftime('%B %d, %Y at %H:%M')}"
                        )
                        st.write("")
                        dl2, del2 = st.columns(2)
                        with dl2:
                            st.download_button(
                                "⬇️ Download",
                                data=qr_bytes,
                                file_name=f"{name}.png",
                                mime="image/png",
                                key=f"hist_dl_{qr_id}",
                            )
                        with del2:
                            if st.button(
                                "🗑️ Delete", key=f"hist_del_{qr_id}"
                            ):
                                delete_qr_from_db(qr_id)
                                st.rerun()
