import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pyperclip
from io import BytesIO
from docx import Document

# -------------------- PAGE CONFIGURATION --------------------
st.set_page_config(
    page_title="KNCCI Mentorship Dashboard",
    layout="wide"
)

st.title("KNCCI Jiinue Mentorship Dashboard")
st.caption("Tracking Mentorship Sessions by Field Officers")

# -------------------- SETTINGS --------------------
OLD_FORM_URL = "https://docs.google.com/spreadsheets/d/107tWhbwBgF89VGCRnNSL4-_WrCIa68NGSPA4GkwVjDE/export?format=csv"
NEW_FORM_URL = "https://docs.google.com/spreadsheets/d/1CA7WvTkEUfeMyLuxhP91BgSWbkhV_S8V94kACj5LUMM/export?format=csv"

# -------------------- FUNCTION TO LOAD AND MERGE DATA --------------------
@st.cache_data(ttl=300)
def load_and_merge_data():
    df_old = pd.read_csv(OLD_FORM_URL)
    df_new = pd.read_csv(NEW_FORM_URL)

    # Strip and normalize column names
    df_old.columns = df_old.columns.str.strip()
    df_new.columns = df_new.columns.str.strip()

    # Tag form versions
    df_old['Form Version'] = 'Original'
    df_new['Form Version'] = 'New'

    # Rename important columns
    df_old.rename(columns={
        'Timestamp': 'Timestamp',
        'County': 'County',
        'Gender': 'Gender',
        'Age': 'Age',
    }, inplace=True)

    df_new.rename(columns={
        'Timestamp': 'Timestamp',
        '14. County of Business Location': 'County',
        '12. Gender of mentee (participant)': 'Gender',
        '11. Age of mentee (full years)': 'Age',
    }, inplace=True)

    # Convert and clean types
    for df in [df_old, df_new]:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df['County'] = df['County'].astype(str).str.strip().str.title()
        df['Gender'] = df['Gender'].astype(str).str.strip().str.title()
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce')

    # Add missing columns to df_old to match df_new
    for col in df_new.columns:
        if col not in df_old.columns:
            df_old[col] = pd.NA

    # Reorder df_old to match df_new
    df_old = df_old[df_new.columns]

    # Merge both
    merged_df = pd.concat([df_old, df_new], ignore_index=True)

    return merged_df

# -------------------- ALL COUNTIES --------------------
all_counties_47 = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta",
    "Garissa", "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka Nithi",
    "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga",
    "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia",
    "Uasin Gishu", "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru",
    "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma",
    "Busia", "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi"
]

# -------------------- LOAD DATA --------------------
df = load_and_merge_data()

if df.empty:
    st.error("❌ No data available! Please check both spreadsheets.")
    st.stop()

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🗓️ Filter Sessions")

min_date = df['Timestamp'].min().date()
max_date = df['Timestamp'].max().date()

st.sidebar.markdown(f"🗓️ **Earliest Submission**: {min_date}")
st.sidebar.markdown(f"🗓️ **Latest Submission**: {max_date}")

date_range = st.sidebar.date_input("Select Date Range:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
start_date, end_date = date_range if isinstance(date_range, tuple) else (date_range, date_range)

form_versions = df['Form Version'].unique().tolist()
selected_versions = st.sidebar.multiselect("Select Form Version:", options=form_versions, default=form_versions)

counties = df['County'].dropna().unique()
selected_counties = st.sidebar.multiselect("Select Counties:", options=sorted(counties), default=sorted(counties))

genders = df['Gender'].dropna().unique()
selected_genders = st.sidebar.multiselect("Select Gender:", options=sorted(genders), default=sorted(genders))

filtered_df = df[
    (df['Timestamp'].dt.date >= start_date) &
    (df['Timestamp'].dt.date <= end_date) &
    (df['Form Version'].isin(selected_versions)) &
    (df['County'].isin(selected_counties)) &
    (df['Gender'].isin(selected_genders))
]

# -------------------- METRICS --------------------
st.subheader("📊 Summary Metrics")

total_sessions = df.shape[0]
filtered_sessions = filtered_df.shape[0]
unique_counties = filtered_df['County'].nunique()
total_participants = filtered_df.drop_duplicates(subset=['County', 'Gender']).shape[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("✅ Total Sessions", f"{total_sessions:,}")
col2.metric("📊 Filtered Sessions", f"{filtered_sessions:,}")
col3.metric("📍 Counties Covered", unique_counties)
col4.metric("👥 Unique Participants", total_participants)

# -------------------- MONTHLY AGE-GENDER BREAKDOWN --------------------
st.subheader("📆 Monthly Age & Gender Breakdown")

# Add Age Group Category
def get_age_gender_group(row):
    try:
        age = int(row['Age'])
        gender = str(row['Gender']).strip().lower()
        if age <= 35:
            return 'Young Female' if gender == 'female' else 'Young Male' if gender == 'male' else 'Other'
        else:
            return 'Above 35 Female' if gender == 'female' else 'Above 35 Male' if gender == 'male' else 'Other'
    except:
        return 'Other'

# Apply categorization
filtered_df['AgeGenderGroup'] = filtered_df.apply(get_age_gender_group, axis=1)
filtered_df['Month'] = filtered_df['Timestamp'].dt.to_period('M')

# Summarize by Month and Group
monthly_summary = (
    filtered_df.groupby(['Month', 'AgeGenderGroup'])
    .size()
    .reset_index(name='Count')
    .pivot(index='Month', columns='AgeGenderGroup', values='Count')
    .fillna(0)
    .astype(int)
    .reset_index()
)

# Ensure all 4 columns are always present
for col in ['Young Female', 'Young Male', 'Above 35 Female', 'Above 35 Male']:
    if col not in monthly_summary.columns:
        monthly_summary[col] = 0

# Show table
st.dataframe(monthly_summary)

# -------------------- MAY SPECIFIC SUMMARY --------------------
st.subheader(":star: May 2025 Mentorship Breakdown")
may_summary = monthly_summary[monthly_summary['Month'] == '2025-05']

if not may_summary.empty:
    may_row = may_summary.iloc[0]
    st.markdown("""
    - **Young Female**: {}
    - **Young Male**: {}
    - **Above 35 Female**: {}
    - **Above 35 Male**: {}
    """.format(
        may_row.get('Young Female', 0),
        may_row.get('Young Male', 0),
        may_row.get('Above 35 Female', 0),
        may_row.get('Above 35 Male', 0),
    ))
else:
    st.info("No mentorship sessions recorded in May 2025.")
