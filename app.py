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

    df_old['County'] = df_old['County'].astype(str).str.strip().str.title()
    df_new['County'] = df_new['County'].astype(str).str.strip().str.title()

    df_old['Gender'] = df_old['Gender'].astype(str).str.strip().str.title()
    df_new['Gender'] = df_new['Gender'].astype(str).str.strip().str.title()

    df_old['Age'] = pd.to_numeric(df_old['Age'], errors='coerce')
    df_new['Age'] = pd.to_numeric(df_new['Age'], errors='coerce')

    return pd.concat([df_old, df_new], ignore_index=True)

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

# Date Range Filter
date_range = st.sidebar.date_input("Select Date Range:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
start_date, end_date = date_range if isinstance(date_range, tuple) else (date_range, date_range)

# Form Version Filter
form_versions = df['Form Version'].unique().tolist()
selected_versions = st.sidebar.multiselect("Select Form Version:", options=form_versions, default=form_versions)

# County Filter
counties = df['County'].dropna().unique()
selected_counties = st.sidebar.multiselect("Select Counties:", options=sorted(counties), default=sorted(counties))

# Gender Filter
genders = df['Gender'].dropna().unique()
selected_genders = st.sidebar.multiselect("Select Gender:", options=sorted(genders), default=sorted(genders))

# Apply Filters
filtered_df = df[
    (df['Timestamp'].dt.date >= start_date) &
    (df['Timestamp'].dt.date <= end_date) &
    (df['Form Version'].isin(selected_versions)) &
    (df['County'].isin(selected_counties)) &
    (df['Gender'].isin(selected_genders))
]

# -------------------- METRICS --------------------
st.subheader("📈 Summary Metrics")

total_sessions = df.shape[0]
filtered_sessions = filtered_df.shape[0]
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

🚫 **Counties with No Submissions**: {len(no_submission_counties)}
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

# -------------------- COUNTY SUBMISSION TABLE AND DOWNLOAD --------------------
st.subheader("📊 County Submissions Data")
county_submission_df = filtered_df.groupby('County').size().reset_index(name='Submissions')
st.dataframe(county_submission_df)  # Display the table in Streamlit

csv_data = county_submission_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Download County Submissions CSV",
    data=csv_data,
    file_name=f"County_Submissions_{datetime.now().date()}.csv",
    mime='text/csv'
)

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

# -------------------- DATA TABLE & DOWNLOAD --------------------
st.subheader("📄 Filtered Data Table")
if not filtered_df.empty:
    st.dataframe(filtered_df)

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


