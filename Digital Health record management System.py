# app.py
import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd

# ---------------------- DB HELPERS ----------------------
DB_NAME = "migrant_health.db"

def init_db():
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()

    # Users (for simple role-based login)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    # Migrant workers master table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS migrants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            state_origin TEXT,
            language_pref TEXT,
            phone TEXT,
            aadhaar TEXT,
            migrant_id TEXT UNIQUE,
            district TEXT,
            occupation TEXT
        )
    """)

    # Health records table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS health_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migrant_id TEXT,
            visit_date TEXT,
            facility TEXT,
            complaints TEXT,
            diagnosis TEXT,
            treatment TEXT,
            follow_up_date TEXT,
            doctor_name TEXT,
            sdg_tag TEXT,               -- SDG3, SDG10 etc.
            FOREIGN KEY (migrant_id) REFERENCES migrants(migrant_id)
        )
    """)

    # SDG indicators table (optional manual entries)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sdg_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_name TEXT,
            indicator_value REAL,
            last_updated TEXT
        )
    """)

    con.commit()

    # create default user if not exists
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", "admin", "doctor")
        )
        con.commit()

    con.close()


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


# ---------------------- AUTH ----------------------
def login(username, password):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT id, username, role FROM users WHERE username=? AND password=?",
        (username, password)
    )
    row = cur.fetchone()
    con.close()
    return row  # (id, username, role) or None


# ---------------------- MIGRANT CRUD ----------------------
def create_migrant(data):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO migrants (
            name, age, gender, state_origin, language_pref,
            phone, aadhaar, migrant_id, district, occupation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    con.commit()
    con.close()


def get_all_migrants():
    con = get_connection()
    df = pd.read_sql_query("SELECT * FROM migrants", con)
    con.close()
    return df


def get_migrant_by_mid(mid):
    con = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM migrants WHERE migrant_id = ?",
        con,
        params=(mid,)
    )
    con.close()
    return df


# ---------------------- HEALTH RECORD CRUD ----------------------
def add_health_record(data):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO health_records (
            migrant_id, visit_date, facility, complaints,
            diagnosis, treatment, follow_up_date, doctor_name, sdg_tag
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    con.commit()
    con.close()


def get_health_records_for_migrant(mid):
    con = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM health_records WHERE migrant_id = ? ORDER BY visit_date DESC",
        con,
        params=(mid,)
    )
    con.close()
    return df


def get_all_health_records():
    con = get_connection()
    df = pd.read_sql_query("SELECT * FROM health_records", con)
    con.close()
    return df


# ---------------------- SDG INDICATORS ----------------------
def upsert_sdg_indicator(name, value):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT id FROM sdg_indicators WHERE indicator_name = ?",
        (name,)
    )
    row = cur.fetchone()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if row:
        cur.execute(
            "UPDATE sdg_indicators SET indicator_value=?, last_updated=? WHERE id=?",
            (value, now, row[0])
        )
    else:
        cur.execute(
            "INSERT INTO sdg_indicators (indicator_name, indicator_value, last_updated) VALUES (?, ?, ?)",
            (name, value, now)
        )
    con.commit()
    con.close()


def get_sdg_indicators():
    con = get_connection()
    df = pd.read_sql_query("SELECT * FROM sdg_indicators", con)
    con.close()
    return df


# ---------------------- UI SECTIONS ----------------------
def show_home():
    st.markdown("## Digital Health Record System")
    st.write(
        "This prototype manages digital health records for migrant workers in Kerala "
        "with a focus on SDG 3 (Good Health & Well‑Being) and SDG 10 (Reduced Inequalities)."
    )


def show_register_migrant():
    st.markdown("### Register Migrant Worker")
    with st.form("migrant_form"):
        name = st.text_input("Name")
        age = st.number_input("Age", min_value=0, max_value=100, value=30)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        state_origin = st.text_input("State of Origin (e.g., Bihar, Assam)")
        language_pref = st.text_input("Preferred Language (e.g., Hindi, Bengali, Odia)")
        phone = st.text_input("Phone")
        aadhaar = st.text_input("Aadhaar (optional)")
        migrant_id = st.text_input("Migrant Health ID (unique, portable)")
        district = st.text_input("District in Kerala (e.g., Ernakulam, Kozhikode)")
        occupation = st.text_input("Occupation (construction, hospitality, etc.)")

        submitted = st.form_submit_button("Register")

        if submitted:
            if not migrant_id:
                st.error("Migrant Health ID is required.")
            else:
                try:
                    create_migrant((
                        name, age, gender, state_origin, language_pref,
                        phone, aadhaar, migrant_id, district, occupation
                    ))
                    st.success(f"Migrant {name} registered with ID {migrant_id}.")
                except Exception as e:
                    st.error(f"Error: {e}")


def show_view_migrants():
    st.markdown("### All Migrant Profiles")
    df = get_all_migrants()
    st.dataframe(df)

    mid = st.text_input("Enter Migrant Health ID to view full profile")
    if mid:
        mdf = get_migrant_by_mid(mid)
        if not mdf.empty:
            st.subheader("Profile")
            st.json(mdf.to_dict(orient="records")[0])

            hdf = get_health_records_for_migrant(mid)
            st.subheader("Health Records")
            st.dataframe(hdf)
        else:
            st.warning("No migrant found with that ID.")


def show_add_health_record():
    st.markdown("### Add Health Record")
    mid = st.text_input("Migrant Health ID")
    visit_date = st.date_input("Visit Date", datetime.today())
    facility = st.text_input("Health Facility (PHC, Govt Hospital, Clinic, camp etc.)")
    complaints = st.text_area("Chief Complaints")
    diagnosis = st.text_area("Diagnosis")
    treatment = st.text_area("Treatment / Medication")
    follow_up_date = st.date_input("Follow‑up Date (if any)", datetime.today())
    doctor_name = st.text_input("Doctor / Health Worker Name")
    sdg_tag = st.selectbox(
        "SDG Alignment Tag",
        ["SDG3: Good Health", "SDG10: Reduced Inequalities", "Both SDG3 & SDG10", "Other"]
    )

    if st.button("Save Health Record"):
        if not mid:
            st.error("Migrant Health ID is required.")
        else:
            add_health_record((
                mid,
                str(visit_date),
                facility,
                complaints,
                diagnosis,
                treatment,
                str(follow_up_date),
                doctor_name,
                sdg_tag
            ))
            st.success("Health record saved.")


def show_sdg_dashboard():
    st.markdown("### SDG‑Aligned Analytics Dashboard")

    hdf = get_all_health_records()
    mdf = get_all_migrants()

    if hdf.empty or mdf.empty:
        st.info("Need some migrant profiles and health records to show analytics.")
        return

    # Merge to see district/state-wise coverage
    merged = hdf.merge(mdf, on="migrant_id", suffixes=("_visit", "_migrant"))

    # Simple KPIs
    total_migrants = len(mdf)
    unique_migrants_with_visits = merged["migrant_id"].nunique()
    coverage_pct = round((unique_migrants_with_visits / total_migrants) * 100, 2)

    st.metric("Total Registered Migrant Workers", total_migrants)
    st.metric("Workers with at least one health visit", unique_migrants_with_visits)
    st.metric("Health coverage (%)", coverage_pct)

    # Update SDG indicators table
    upsert_sdg_indicator("Migrant health coverage (%) - SDG3", coverage_pct)

    # District-wise coverage
    district_counts = merged.groupby("district")["migrant_id"].nunique().reset_index()
    st.subheader("District‑wise unique workers with health records")
    st.bar_chart(district_counts.set_index("district"))

    # SDG tags distribution
    sdg_counts = hdf["sdg_tag"].value_counts().reset_index()
    sdg_counts.columns = ["sdg_tag", "count"]
    st.subheader("SDG‑tagged health records")
    st.bar_chart(sdg_counts.set_index("sdg_tag"))

    st.subheader("Stored SDG indicators")
    st.dataframe(get_sdg_indicators())


def show_multilingual_help():
    st.markdown("### Multilingual Support (Concept)")

    st.write("This system is meant for migrant workers from multiple states and languages in Kerala.")
    st.write("- Use simple icons and color codes so non‑literate workers can understand status.")
    st.write("- Add language toggle (Malayalam, Hindi, Bengali, Odia) using translation files later.")
    st.write("- Aligns with SDG10 by reducing inequalities in access due to language barriers.")


# ---------------------- MAIN APP ----------------------
def main():
    st.set_page_config(
        page_title="Digital Health Record Management - Migrant Workers Kerala",
        layout="wide"
    )

    init_db()

    if "user" not in st.session_state:
        st.session_state.user = None

    st.title("Digital Health Record Management System")
    st.caption("For Migrant Workers in Kerala – aligned with SDG 3 & SDG 10")

    if st.session_state.user is None:
        st.sidebar.subheader("Login")

        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user = login(username, password)
            if user:
                st.session_state.user = {
                    "id": user[0],
                    "username": user[1],
                    "role": user[2]
                }
                st.success(f"Welcome, {user[1]} ({user[2]})")
            else:
                st.error("Invalid credentials. Use admin / admin for demo.")
        st.info("Use **admin / admin** to log in for the demo.")
        show_home()
        return

    # Logged‑in UI
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user['username']} ({user['role']})")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()

    menu = [
        "Home",
        "Register Migrant",
        "View Migrants & Records",
        "Add Health Record",
        "SDG Dashboard",
        "Multilingual / Inclusion Notes"
    ]
    choice = st.sidebar.selectbox("Navigate", menu)

    if choice == "Home":
        show_home()
    elif choice == "Register Migrant":
        show_register_migrant()
    elif choice == "View Migrants & Records":
        show_view_migrants()
    elif choice == "Add Health Record":
        show_add_health_record()
    elif choice == "SDG Dashboard":
        show_sdg_dashboard()
    elif choice == "Multilingual / Inclusion Notes":
        show_multilingual_help()


if __name__ == "__main__":
    main()
