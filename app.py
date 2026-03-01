import streamlit as st
import psycopg2
import bcrypt
import requests
from streamlit_lottie import st_lottie

# --- PAGE CONFIG ---
st.set_page_config(page_title="Group 2 Meme Generator", page_icon=":monkey_face:", layout="wide")

# --- DATABASE FUNCTIONS ---
def get_connection():
    return psycopg2.connect(
        dbname="postgres", 
        user="postgres", 
        password="group2", 
        host="localhost",
        port="5432"
    )

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# --- LOTTIE ANIMATION FUNCTION ---
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

lottie_coding = load_lottieurl("https://lottie.host/48be386f-b15c-436b-b6e9-b185247ce9bf/gyNTPoA2g4.json")

# --- SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
if not st.session_state['logged_in']:
    menu = ["Login", "Signup"]
else:
    menu = ["Home", "Meme Generator", "Logout"]

choice = st.sidebar.selectbox("Go to", menu)

# --- AUTHENTICATION LOGIC ---
if choice == "Signup":
    st.subheader("Create New Account")
    new_user = st.text_input("Username")
    new_password = st.text_input("Password", type='password')
    if st.button("Register"):
        try:
            conn = get_connection()
            cur = conn.cursor()
            hashed_pw = hash_password(new_password)
            cur.execute("INSERT INTO users(username, password) VALUES (%s,%s)", (new_user, hashed_pw))
            conn.commit()
            st.success("Account created successfully!")
            cur.close()
            conn.close()
        except Exception as e:
            # THIS LINE WILL SHOW YOU THE REAL ERROR MESSAGE
            st.error(f"Database Error: {e}")

elif choice == "Login":
    st.subheader("Login to Access Meme Generator")
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')
    if st.button("Login"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username = %s", (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and verify_password(password, result[0]):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.rerun()
        else:
            st.error("Invalid Username or Password")

elif choice == "Logout":
    st.session_state['logged_in'] = False
    st.rerun()

# --- MAIN APP CONTENT  ---
if st.session_state['logged_in']:
    # Header
    with st.container():
        st.subheader(f"Welcome back, {st.session_state['username']}! :monkey_face:")
        st.title("Click to monke")
        st.write("This is a group project that utilizes the power of Python using streamlit while also integrating PostgreSQL.")
        st.write("[Learn More >](https://www.youtube.com/watch?v=VqgUkExPvLY)")

    # Intro Section
    with st.container():
        st.write("---")
        leftcol, rightcol = st.columns(2)
        with leftcol:
            st.header("What is this?")
            st.write("##")
            st.write(
                "This is a meme generator that generates random memes when you click the button. "
                "It uses the power of Python and Streamlit to create a simple "
                "and easy to use interface for users to generate memes."
            )
        
        with rightcol:
            # Adding the Lottie Animation here as requested
            st_lottie(lottie_coding, height=300, key="coding_anim")

else:
    if choice not in ["Login", "Signup"]:
        st.warning("Please Login or Signup from the sidebar to access the Meme Generator.")