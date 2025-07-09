import streamlit as st
import pymongo
from pymongo.errors import ServerSelectionTimeoutError
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os
import hashlib

# Load .env variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB connection
@st.cache_resource
def init_connection():
    if not MONGO_URI:
        st.error("❌ MONGO_URI not found. Please set it in .env or Streamlit secrets.")
        return None
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # force connection on load
        db = client["EnergyTracker"]
        return db
    except ServerSelectionTimeoutError as e:
        st.error(f"❌ Could not connect to MongoDB: {e}")
        return None

db = init_connection()
users_collection = db["users"] if db else None
consumption_collection = db["consumption"] if db else None

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def authenticate_user(username, password):
    if not users_collection:
        return None
    user = users_collection.find_one({"username": username})
    return user if user and verify_password(password, user["password"]) else None

def create_user(username, email, password):
    if not users_collection:
        return False
    if users_collection.find_one({"username": username}):
        return False
    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": hash_password(password),
        "created_at": datetime.now()
    })
    return True

# UI functions
def show_login():
    st.title("🔐 Login / Signup")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                user = authenticate_user(username, password)
                if user:
                    st.session_state["user"] = user
                    st.success("✅ Logged in successfully!")
                    st.experimental_rerun()
                else:
                    st.error("❌ Invalid credentials.")

    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="su_user")
            email = st.text_input("Email")
            new_password = st.text_input("Password", type="password", key="su_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="su_pass2")
            submitted = st.form_submit_button("Sign Up")
            if submitted:
                if new_password != confirm_password:
                    st.error("❌ Passwords do not match.")
                elif create_user(new_username, email, new_password):
                    st.success("✅ Account created. Please log in.")
                else:
                    st.error("❌ Username already exists.")

def show_dashboard():
    st.title("📊 Energy Tracker Dashboard")
    st.markdown(f"Welcome, **{st.session_state['user']['username']}** 👋")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.experimental_rerun()

    st.write("Add your dashboard logic here.")

# Main app
def main():
    if db is None:
        st.stop()

    if "user" not in st.session_state:
        show_login()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
