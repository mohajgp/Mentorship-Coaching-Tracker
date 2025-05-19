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

    df_old.columns = df_old.columns.str.strip()
    df_new.columns = df_new.columns.str.strip()

    df_old['Form Version'] = 'Original'
    df_new['Form Version'] = 'New'

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

    df_old['Timestamp'] = pd.to_datetime(df_old['Timestamp'], errors='coerce')
    df_new['Timestamp'] = pd.to_datetime(df_new['Timestamp'], errors='coerce')

    return pd.concat([df_old, df_new], ignore_index=True)

# -------------------- LOAD DATA --------------------
df = load_and_merge_data()

if df.empty:
    st.error("❌ No data available! Please check both spreadsheets.")
    st.stop()

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🗓️ Filter Sessions")
min_date = df['Timestamp'].min().date()
max_date = df['Timestamp'].max().date()

# Date Range Filter
date_range = st.sidebar.date_input("Select Date Range:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
start_date, end_date = date_range if isinstance(date_range, tuple) else (date_range, date_range)

filtered_df = df[(df['Timestamp'].dt.date >= start_date) & (df['Timestamp'].dt.date <= end_date)]

# -------------------- METRICS --------------------
st.subheader("📈 Summary Metrics")
total_sessions = df.shape[0]
filtered_sessions = filtered_df.shape[0]

col1, col2 = st.columns(2)
col1.metric("✅ Total Sessions", f"{total_sessions:,}")
col2.metric("📊 Filtered Sessions", f"{filtered_sessions:,}")

# -------------------- COUNTY TOTALS --------------------
st.subheader("📍 Submissions by County")
county_totals = filtered_df['County'].value_counts().reset_index()
county_totals.columns = ['County', 'Submissions']
county_totals['Total Submissions'] = county_totals['Submissions'].sum()
st.dataframe(county_totals)

fig_bar = px.bar(county_totals, x='County', y='Submissions', color='County', title='Number of Submissions by County')
st.plotly_chart(fig_bar, use_container_width=True)

# -------------------- DOWNLOAD COUNTY TOTALS --------------------
st.subheader("⬇️ Download County Submissions CSV")
csv_data = county_totals.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download County Submissions CSV",
    data=csv_data,
    file_name=f"County_Submissions_{datetime.now().date()}.csv",
    mime='text/csv'
)

