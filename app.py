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

    for df in [df_old, df_new]:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df['County'] = df['County'].astype(str).str.strip().str.title()
        df['Gender'] = df['Gender'].astype(str).str.strip().str.title()
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce')

    # Add missing columns to df_old
    for col in df_new.columns:
        if col not in df_old.columns:
            df_old[col] = pd.NA

    # Align column order
    df_old = df_old[df_new.columns]

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
st.subheader("📈 Summary Metrics")

total_sessions = df['Timestamp'].notna().sum()  # Count valid rows only
filtered_sessions = filtered_df['Timestamp'].notna().sum()
unique_counties = filtered_df['County'].nunique()
total_participants = filtered_df.drop_duplicates(subset=['County', 'Gender']).shape[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("✅ Total Sessions", f"{total_sessions:,}")
col2.metric("📊 Filtered Sessions", f"{filtered_sessions:,}")
col3.metric("📍 Counties Covered", unique_counties)
col4.metric("👥 Unique Participants", total_participants)

# -------------------- AUTO-GENERATED SUMMARY --------------------
st.subheader("📝 Auto-Generated Summary Report")
no_submission_counties = [c for c in all_counties_47 if c not in filtered_df['County'].unique()]
summary_text = f"""
📅 **Date Range**: {start_date} to {end_date}

✅ **Total Submissions**: {total_sessions:,}
📊 **Filtered Submissions**: {filtered_sessions:,}
📍 **Counties Covered**: {unique_counties}
👥 **Unique Participants**: {total_participants}

🚫 **Counties with No Submissions**: {len(no_submission_counties)} ({', '.join(no_submission_counties)})
"""
st.text_area("📋 Copy this Summary for Emailing:", value=summary_text, height=200)
if st.button("📋 Copy to Clipboard"):
    pyperclip.copy(summary_text)
    st.success("✅ Summary copied to clipboard!")

# -------------------- DOWNLOAD WORD REPORT --------------------
st.subheader("📄 Export Summary to Word Document")
if st.button("⬇️ Generate Word Report"):
    doc = Document()
    doc.add_heading("KNCCI Jiinue Mentorship Summary Report", level=1)
    doc.add_paragraph(summary_text)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    st.download_button(
        label="📥 Download Word Report",
        data=buffer,
        file_name=f"Mentorship_Summary_{datetime.now().date()}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# -------------------- COUNTY SUBMISSION BAR CHART --------------------
st.subheader("📍 Submissions by County")
county_counts = filtered_df.groupby('County').size().reset_index(name='Submissions')
fig_bar = px.bar(county_counts, x='County', y='Submissions', color='County', title='Number of Submissions by County')
st.plotly_chart(fig_bar, use_container_width=True)

# -------------------- SUBMISSIONS OVER TIME --------------------
st.subheader("📆 Submissions Over Time")
daily_counts = filtered_df.groupby(filtered_df['Timestamp'].dt.date).size().reset_index(name='Submissions')
fig_time = px.line(daily_counts, x='Timestamp', y='Submissions', title='Daily Submission Trend')
st.plotly_chart(fig_time, use_container_width=True)

# -------------------- NON-SUBMISSIONS --------------------
st.subheader("🚫 Counties with No Submissions")
if no_submission_counties:
    st.error(f"🚫 Counties with **NO** Submissions: {', '.join(no_submission_counties)}")
else:
    st.success("✅ All counties have submissions in selected date range.")

# -------------------- SAFE FILTERED DATA TABLE --------------------
st.subheader("📄 Filtered Data Table (Safe View)")

# Exclude columns that cause Arrow issues (giant text fields)
safe_columns = [col for col in filtered_df.columns if filtered_df[col].astype(str).str.len().max() < 500]
filtered_df_safe = filtered_df[safe_columns]

if not filtered_df.empty:
    st.dataframe(filtered_df_safe)
    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📅 Download CSV",
        data=csv_data,
        file_name=f"Mentorship_Submissions_{datetime.now().date()}.csv",
        mime='text/csv'
    )
else:
    st.info("ℹ️ No submissions match current filters.")

# -------------------- MERGED DATA TABLE AND DOWNLOAD --------------------
st.subheader("➕ Merged Data Table")
st.dataframe(df)

csv_data_merged = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Merged CSV",
    data=csv_data_merged,
    file_name=f"Mentorship_Merged_Data_{datetime.now().date()}.csv",
    mime='text/csv'
)
