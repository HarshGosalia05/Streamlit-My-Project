import streamlit as st
import pymongo
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import hashlib
import io
import base64
from typing import Dict, List, Optional
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
import os

# MongoDB connection
@st.cache_resource
def init_connection():
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["EnergyTracker"]
        return db
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# Initialize database
db = init_connection()
if db is not None:
    users_collection = db["users"]
    consumption_collection = db["consumption"]
    data_collection = db["data_collection"]  # New collection for login data

# Utility functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def create_user(username: str, email: str, password: str) -> bool:
    """Create new user account"""
    if db is None:
        return False
    
    # Check if user already exists
    if users_collection.find_one({"username": username}):
        return False
    
    user_data = {
        "username": username,
        "email": email,
        "password": hash_password(password),
        "created_at": datetime.now(),
        "profile": {
            "city": "",
            "area": "",
            "age": 0,
            "phone": "",
            "full_name": "",
            "occupation": "",
            "household_size": 1
        }
    }
    
    try:
        users_collection.insert_one(user_data)
        return True
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate user login and store login data"""
    if db is None:
        return None
    
    user = users_collection.find_one({"username": username})
    if user and verify_password(password, user["password"]):
        # Store login data in data_collection
        login_data = {
            "username": username,
            "login_time": datetime.now(),
            "login_date": datetime.now().strftime("%Y-%m-%d"),
            "session_id": str(datetime.now().timestamp()),
            "ip_address": "localhost",  # You can get actual IP if needed
            "user_agent": "Streamlit App"
        }
        
        try:
            data_collection.insert_one(login_data)
        except Exception as e:
            st.error(f"Error storing login data: {e}")
        
        return user
    return None

def save_consumption_data(username: str, appliances: Dict, total_energy: float, cost: float):
    """Save daily consumption data"""
    if db is None:
        return False
    
    today = datetime.now()
    data = {
        "username": username,
        "date": today.strftime("%Y-%m-%d"),
        "day_of_week": today.strftime("%A"),
        "timestamp": today,
        "appliances": appliances,
        "total_energy_kwh": round(total_energy, 2),
        "estimated_cost": round(cost, 2)
    }
    
    try:
        # Check if entry for today already exists
        existing = consumption_collection.find_one({
            "username": username,
            "date": today.strftime("%Y-%m-%d")
        })
        
        if existing:
            consumption_collection.update_one(
                {"_id": existing["_id"]},
                {"$set": data}
            )
        else:
            consumption_collection.insert_one(data)
        
        return True
    except Exception as e:
        st.error(f"Error saving consumption data: {e}")
        return False

def get_user_consumption_data(username: str, days: int = 14) -> List[Dict]:
    """Get user's consumption data for last N days"""
    if db is None:
        return []
    
    start_date = datetime.now() - timedelta(days=days)
    
    try:
        data = list(consumption_collection.find({
            "username": username,
            "timestamp": {"$gte": start_date}
        }).sort("timestamp", 1))
        
        return data
    except Exception as e:
        st.error(f"Error retrieving consumption data: {e}")
        return []

def get_user_login_data(username: str) -> List[Dict]:
    """Get user's login history"""
    if db is None:
        return []
    
    try:
        data = list(data_collection.find({
            "username": username
        }).sort("login_time", -1).limit(10))
        
        return data
    except Exception as e:
        st.error(f"Error retrieving login data: {e}")
        return []

def calculate_energy_consumption(appliances: Dict) -> float:
    """Calculate total energy consumption"""
    energy_rates = {
        "lights": 0.2,
        "fans": 0.2,
        "tvs": 0.3,
        "ac": 3.0,
        "fridge": 3.1,
        "washing_machine": 2.8
    }
    
    total = 0
    for appliance, count in appliances.items():
        if appliance in energy_rates:
            total += count * energy_rates[appliance]
    
    return total

# Custom CSS for better styling
def load_css():
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .energy-input {
        background: #f0f2f6;
        border-radius: 5px;
        padding: 0.5rem;
        margin: 0.25rem 0;
    }
    
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    
    .warning-message {
        background: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #ffeaa7;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2C3E50 0%, #34495E 100%);
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        border: none;
        color: white;
        font-weight: bold;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .profile-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #4ECDC4;
    }
    
    .login-history {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------- Login / Signup Page ----------
def show_login_page():
    st.markdown('<h1 class="main-header">⚡ Energy Tracker Login</h1>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])

    with tab1:
        st.subheader("Welcome Back!")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            if st.form_submit_button("Login", use_container_width=True):
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("⚠️ Please fill in all fields")

    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Username", placeholder="Choose a username", key="su_user")
            new_email = st.text_input("Email", placeholder="Enter your email", key="su_email")
            new_password = st.text_input("Password", type="password", placeholder="Create a password", key="su_pass")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="su_cpass")

            if st.form_submit_button("Sign Up", use_container_width=True):
                if new_username and new_email and new_password and confirm_password:
                    if new_password == confirm_password:
                        if create_user(new_username, new_email, new_password):
                            st.success("✅ Account created successfully! Please login.")
                        else:
                            st.error("❌ Username already exists or database error")
                    else:
                        st.error("❌ Passwords do not match")
                else:
                    st.warning("⚠️ Please fill in all fields")

# Main dashboard
def show_dashboard():
    user = st.session_state.user
    username = user["username"]
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### Welcome, {username}! 👋")
        st.markdown("---")
        
        # Theme toggle
        if st.button("🌙 Toggle Dark Mode"):
            st.session_state.dark_mode = not st.session_state.get('dark_mode', False)
        
        # Navigation
        page = st.selectbox(
            "Navigate",
            ["📊 Dashboard", "⚡ Add Energy Data", "📈 Analytics", "👤 Profile", "📁 Export Data"]
        )
        
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()
    
    # Main content based on selected page
    if page == "📊 Dashboard":
        show_dashboard_home(username)
    elif page == "⚡ Add Energy Data":
        show_energy_input(username)
    elif page == "📈 Analytics":
        show_analytics(username)
    elif page == "👤 Profile":
        show_profile(username)
    elif page == "📁 Export Data":
        show_export_data(username)

def show_dashboard_home(username: str):
    st.markdown('<h1 class="main-header">⚡ Energy Dashboard</h1>', unsafe_allow_html=True)
    
    # Get recent data
    recent_data = get_user_consumption_data(username, days=7)
    
    if not recent_data:
        st.warning("No energy data found. Add your first entry using the 'Add Energy Data' page!")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_energy = sum(entry['total_energy_kwh'] for entry in recent_data)
    total_cost = sum(entry['estimated_cost'] for entry in recent_data)
    avg_daily = total_energy / len(recent_data) if recent_data else 0
    monthly_projection = avg_daily * 30
    
    with col1:
        st.metric("🔋 Total Energy (7d)", f"{total_energy:.2f} kWh")
    
    with col2:
        st.metric("💰 Total Cost (7d)", f"₹{total_cost:.2f}")
    
    with col3:
        st.metric("📊 Daily Average", f"{avg_daily:.2f} kWh")
    
    with col4:
        st.metric("📅 Monthly Projection", f"{monthly_projection:.2f} kWh")
    
    # Recent entries table
    st.subheader("📋 Recent Entries")
    if recent_data:
        df_data = []
        for entry in recent_data[-7:]:  # Show last 7 entries
            df_data.append({
                "Date": entry['date'],
                "Day": entry['day_of_week'],
                "Energy (kWh)": entry['total_energy_kwh'],
                "Cost (₹)": entry['estimated_cost']
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
    
    # Quick energy input
    st.subheader("⚡ Quick Energy Entry")
    with st.expander("Add today's consumption"):
        show_energy_input_form(username, compact=True)

def show_energy_input(username: str):
    st.markdown('<h2 class="main-header">⚡ Add Energy Data</h2>', unsafe_allow_html=True)
    show_energy_input_form(username)

def show_energy_input_form(username: str, compact: bool = False):
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Check if today's data already exists
    existing_data = consumption_collection.find_one({
        "username": username,
        "date": today
    }) if db is not None else None
    
    if existing_data and not compact:
        st.info(f"⚠️ You already have an entry for today ({today}). Submitting will update your existing entry.")
    
    with st.form("energy_form"):
        if not compact:
            st.subheader("🏠 Home Appliances")
        
        col1, col2 = st.columns(2)
        
        with col1:
            lights = st.number_input("💡 Number of Lights", min_value=0, max_value=50, value=0,
                                   help="LED bulbs, tube lights, etc.")
            fans = st.number_input("🌀 Number of Fans", min_value=0, max_value=20, value=0,
                                 help="Ceiling fans, table fans, etc.")
            tvs = st.number_input("📺 Number of TVs", min_value=0, max_value=10, value=0,
                                help="LED, LCD, Smart TVs, etc.")
        
        with col2:
            # Conditional appliances
            has_ac = st.checkbox("❄️ Do you have Air Conditioner?")
            ac_count = st.number_input("Number of ACs", min_value=0, max_value=10, value=0,
                                     disabled=not has_ac, help="Split, Window, Central AC") if has_ac else 0
            
            has_fridge = st.checkbox("🧊 Do you have Refrigerator?")
            fridge_count = st.number_input("Number of Refrigerators", min_value=0, max_value=5, value=0,
                                         disabled=not has_fridge, help="Single door, Double door, etc.") if has_fridge else 0
            
            has_wm = st.checkbox("👕 Do you have Washing Machine?")
            wm_count = st.number_input("Number of Washing Machines", min_value=0, max_value=5, value=0,
                                     disabled=not has_wm, help="Top load, Front load, etc.") if has_wm else 0
        
        # Calculate energy
        appliances = {
            "lights": lights,
            "fans": fans,
            "tvs": tvs,
            "ac": ac_count,
            "fridge": fridge_count,
            "washing_machine": wm_count
        }
        
        total_energy = calculate_energy_consumption(appliances)
        rate_per_unit = 8  # ₹ per kWh
        total_cost = total_energy * rate_per_unit
        
        # Show preview
        if not compact:
            st.subheader("📊 Consumption Preview")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🔋 Total Energy", f"{total_energy:.2f} kWh")
            with col2:
                st.metric("💰 Estimated Cost", f"₹{total_cost:.2f}")
        
        # Submit button
        submit_button = st.form_submit_button("💾 Save Energy Data", use_container_width=True)
        
        if submit_button:
            if total_energy > 0:
                if save_consumption_data(username, appliances, total_energy, total_cost):
                    st.success("✅ Energy data saved successfully!")
                    if not compact:
                        st.balloons()
                else:
                    st.error("❌ Failed to save data. Please try again.")
            else:
                st.warning("⚠️ Please enter at least one appliance.")

def show_analytics(username: str):
    st.markdown('<h2 class="main-header">📈 Energy Analytics</h2>', unsafe_allow_html=True)
    
    # Get data for different time periods
    col1, col2 = st.columns([3, 1])
    
    with col2:
        days_range = st.selectbox("📅 Time Period", [7, 14, 30, 60], index=1)
    
    data = get_user_consumption_data(username, days=days_range)
    
    if not data:
        st.warning("No data available for the selected period.")
        return
    
    # Prepare data for plotting
    dates = [datetime.strptime(entry['date'], '%Y-%m-%d') for entry in data]
    energy_values = [entry['total_energy_kwh'] for entry in data]
    cost_values = [entry['estimated_cost'] for entry in data]
    
    # Create matplotlib chart
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Energy consumption chart
    ax1.plot(dates, energy_values, marker='o', linewidth=2, markersize=6, color='#4ECDC4')
    
    # Highlight high consumption days (>15 kWh)
    high_consumption = [(date, energy) for date, energy in zip(dates, energy_values) if energy > 15]
    if high_consumption:
        high_dates, high_values = zip(*high_consumption)
        ax1.scatter(high_dates, high_values, color='red', s=100, zorder=5, alpha=0.7)
    
    # Annotate points
    for date, energy in zip(dates, energy_values):
        ax1.annotate(f'{energy:.1f}', (date, energy), 
                    textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
    
    ax1.set_title('Your Daily Energy Usage Trend', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Energy (kWh)')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%a\n%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    
    # Cost chart
    ax2.bar(dates, cost_values, color='#FF6B6B', alpha=0.7)
    ax2.set_title('Daily Cost Breakdown', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Cost (₹)')
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%a\n%Y-%m-%d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    
    plt.tight_layout()
    plt.xticks(rotation=45)
    
    # Display chart
    st.pyplot(fig)
    
    # Download option
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    
    st.download_button(
        label="📥 Download Chart as PNG",
        data=buf.getvalue(),
        file_name=f"energy_chart_{username}_{datetime.now().strftime('%Y%m%d')}.png",
        mime="image/png"
    )
    
    # Summary statistics
    st.subheader("📊 Summary Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Average Daily Usage", f"{sum(energy_values)/len(energy_values):.2f} kWh")
        st.metric("📈 Peak Usage", f"{max(energy_values):.2f} kWh")
    
    with col2:
        st.metric("💰 Average Daily Cost", f"₹{sum(cost_values)/len(cost_values):.2f}")
        st.metric("💸 Highest Cost", f"₹{max(cost_values):.2f}")
    
    with col3:
        st.metric("🔋 Total Energy", f"{sum(energy_values):.2f} kWh")
        st.metric("💳 Total Cost", f"₹{sum(cost_values):.2f}")

def show_profile(username: str):
    st.markdown('<h2 class="main-header">👤 User Profile</h2>', unsafe_allow_html=True)
    
    user = users_collection.find_one({"username": username}) if db is not None else None
    
    if not user:
        st.error("User data not found.")
        return
    
    # Display current profile information
    st.markdown('<div class="profile-section">', unsafe_allow_html=True)
    st.subheader("📋 Current Profile Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**👤 Username:** {user['username']}")
        st.write(f"**📧 Email:** {user.get('email', 'Not provided')}")
        st.write(f"**🏙️ City:** {user.get('profile', {}).get('city', 'Not provided')}")
        st.write(f"**📍 Area:** {user.get('profile', {}).get('area', 'Not provided')}")
    
    with col2:
        st.write(f"**👶 Age:** {user.get('profile', {}).get('age', 'Not provided')}")
        st.write(f"**📅 Account Created:** {user.get('created_at', 'Unknown').strftime('%Y-%m-%d %H:%M:%S') if isinstance(user.get('created_at'), datetime) else 'Unknown'}")
        st.write(f"**📱 Phone:** {user.get('profile', {}).get('phone', 'Not provided')}")
        st.write(f"**💼 Occupation:** {user.get('profile', {}).get('occupation', 'Not provided')}")
    
    st.write(f"**👥 Household Size:** {user.get('profile', {}).get('household_size', 'Not provided')}")
    st.write(f"**🏠 Full Name:** {user.get('profile', {}).get('full_name', 'Not provided')}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    
    
    # Update Profile Form
    st.subheader("✏️ Update Profile Information")
    
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("👤 Full Name", value=user.get('profile', {}).get('full_name', ''))
            city = st.text_input("🏙️ City", value=user.get('profile', {}).get('city', ''))
            area = st.text_input("📍 Area", value=user.get('profile', {}).get('area', ''))
            phone = st.text_input("📱 Phone", value=user.get('profile', {}).get('phone', ''))
        
        with col2:
            # Fix for age input: ensure the value is at least min_value
            current_age = user.get('profile', {}).get('age', 25)
            # If current age is less than min_value, use min_value instead
            age_value = max(current_age, 10) if current_age is not None else 25
            
            age = st.number_input("👶 Age", min_value=10, max_value=120, value=age_value)
            email = st.text_input("📧 Email", value=user.get('email', ''))
            occupation = st.text_input("💼 Occupation", value=user.get('profile', {}).get('occupation', ''))
            
            # Fix for household size: ensure the value is at least min_value
            current_household = user.get('profile', {}).get('household_size', 1)
            household_value = max(current_household, 1) if current_household is not None else 1
            
            household_size = st.number_input("👥 Household Size", min_value=1, max_value=20,
                                           value=household_value)
        
        if st.form_submit_button("💾 Update Profile", use_container_width=True):
            update_data = {
                "$set": {
                    "profile.full_name": full_name,
                    "profile.city": city,
                    "profile.area": area,
                    "profile.age": age,
                    "profile.phone": phone,
                    "profile.occupation": occupation,
                    "profile.household_size": household_size,
                    "email": email,
                    "updated_at": datetime.now()
                }
            }
            
            try:
                if db is not None:
                    users_collection.update_one({"username": username}, update_data)
                    st.success("✅ Profile updated successfully!")
                    st.rerun()
                else:
                    st.error("❌ Database connection error.")
            except Exception as e:
                st.error(f"❌ Error updating profile: {e}")

    # Login History
    st.subheader("🔒 Recent Login History")
    login_history = get_user_login_data(username)
    
    if login_history:
        for i, login in enumerate(login_history[:5]):  # Show last 5 logins
            login_time = login['login_time'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(login['login_time'], datetime) else str(login['login_time'])
            st.markdown(f'<div class="login-history">**Login {i+1}:** {login_time}</div>', unsafe_allow_html=True)
    else:
        st.info("No login history available.")

                
def show_export_data(username: str):
    st.markdown('<h2 class="main-header">📁 Export Data</h2>', unsafe_allow_html=True)
    
    # Get all user data
    all_data = get_user_consumption_data(username, days=365)  # Get full year
    
    if not all_data:
        st.warning("No data available to export.")
        return
    
    # Prepare data for export
    export_data = []
    for entry in all_data:
        row = {
            "Date": entry['date'],
            "Day of Week": entry['day_of_week'],
            "Lights": entry['appliances']['lights'],
            "Fans": entry['appliances']['fans'],
            "TVs": entry['appliances']['tvs'],
            "Air Conditioners": entry['appliances']['ac'],
            "Refrigerators": entry['appliances']['fridge'],
            "Washing Machines": entry['appliances']['washing_machine'],
            "Total Energy (kWh)": entry['total_energy_kwh'],
            "Estimated Cost (₹)": entry['estimated_cost']
        }
        export_data.append(row)
    
    df = pd.DataFrame(export_data)
    
    # Show preview
    st.subheader("📋 Data Preview")
    st.dataframe(df.head(10), use_container_width=True)
    
    # Export options
    st.subheader("📥 Export Options")
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV export
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📄 Download as CSV",
            data=csv_data,
            file_name=f"energy_data_{username}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Excel export
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        st.download_button(
            label="📊 Download as Excel",
            data=excel_buffer.getvalue(),
            file_name=f"energy_data_{username}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # Summary
    st.subheader("📊 Export Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📁 Total Records", len(df))
    
    with col2:
        st.metric("📅 Date Range", f"{df['Date'].min()} to {df['Date'].max()}")
    
    with col3:
        st.metric("🔋 Total Energy", f"{df['Total Energy (kWh)'].sum():.2f} kWh")


# Main app logic
def main():
    load_css()
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Check database connection
    if db is None:
        st.error("❌ Database connection failed. Please ensure MongoDB is running on localhost:27017")
        st.stop()
    
    # Show appropriate page based on login status
    if st.session_state.user is None:
        show_login_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
