import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pyperclip
from io import BytesIO
from docx import Document

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="KNCCI Mentorship Dashboard",
    layout="wide"
)

st.title("KNCCI Jiinue Mentorship Dashboard")
st.caption("Tracking Mentorship Sessions by Field Officers")

# -------------------- GOOGLE SHEET LINKS --------------------
OLD_FORM_URL = "https://docs.google.com/spreadsheets/d/107tWhbwBgF89VGCRnNSL4-_WrCIa68NGSPA4GkwVjDE/export?format=csv"
NEW_FORM_URL = "https://docs.google.com/spreadsheets/d/1CA7WvTkEUfeMyLuxhP91BgSWbkhV_S8V94kACj5LUMM/export?format=csv"

# -------------------- LOAD & COMBINE DATA --------------------
@st.cache_data(ttl=300)
def load_data():
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
        'Business Phone Number': 'Phone Number'
    }, inplace=True)

    df_new.rename(columns={
        'Timestamp': 'Timestamp',
        '14. County of Business Location': 'County',
        '12. Gender of mentee (participant)': 'Gender',
        '11. Age of mentee (full years)': 'Age',
        '10. Mobile phone Number (Format: 2547XXXXXXXX)': 'Phone Number',
        '8. National ID (5 to 11 digits)': 'ID'
    }, inplace=True)

    for df in [df_old, df_new]:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df['County'] = df['County'].astype(str).str.strip().str.title()
        df['Gender'] = df['Gender'].astype(str).str.strip().str.title()
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
        df['Phone Number'] = df['Phone Number'].astype(str).str.extract(r'(\d{9,12})')
        if 'ID' not in df.columns:
            df['ID'] = pd.NA

    # Align columns and concatenate
    for col in df_new.columns:
        if col not in df_old.columns:
            df_old[col] = pd.NA
    df_old = df_old[df_new.columns]

    combined_df = pd.concat([df_old, df_new], ignore_index=True)
    return combined_df, combined_df.shape[0]

# -------------------- KNOWN COUNTIES --------------------
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
df_raw, total_raw_rows = load_data()
if df_raw.empty:
    st.error("❌ No data available! Please check the spreadsheets.")
    st.stop()

# -------------------- FILTER UI --------------------
st.sidebar.header("🗓️ Filter Sessions")
min_date = df_raw['Timestamp'].min().date()
max_date = df_raw['Timestamp'].max().date()

date_range = st.sidebar.date_input("Select Date Range:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
start_date, end_date = date_range if isinstance(date_range, tuple) else (date_range, date_range)

form_versions = df_raw['Form Version'].dropna().unique().tolist()
selected_versions = st.sidebar.multiselect("Select Form Version:", options=form_versions, default=form_versions)

counties = df_raw['County'].dropna().unique()
selected_counties = st.sidebar.multiselect("Select Counties:", options=sorted(counties), default=sorted(counties))

genders = df_raw['Gender'].dropna().unique()
selected_genders = st.sidebar.multiselect("Select Gender:", options=sorted(genders), default=sorted(genders))

# -------------------- FILTER DATA --------------------
filtered_df = df_raw[
    (df_raw['Timestamp'].dt.date >= start_date) &
    (df_raw['Timestamp'].dt.date <= end_date) &
    (df_raw['Form Version'].isin(selected_versions)) &
    (df_raw['County'].isin(selected_counties)) &
    (df_raw['Gender'].isin(selected_genders))
]

deduped_df = filtered_df.drop_duplicates(subset=['Phone Number', 'ID'])
total_unique_rows = deduped_df.shape[0]

# -------------------- SUMMARY METRICS --------------------
st.subheader("📈 Summary Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Raw Submissions", f"{total_raw_rows:,}")
col2.metric("✅ Unique Mentorship Records", f"{total_unique_rows:,}")
col3.metric("📊 Filtered Sessions", f"{filtered_df.shape[0]:,}")
col4.metric("📍 Counties Covered", deduped_df['County'].nunique())

# -------------------- AUTO-GENERATED SUMMARY --------------------
st.subheader("📝 Auto-Generated Summary Report")
no_submission_counties = [c for c in all_counties_47 if c not in deduped_df['County'].unique()]
summary_text = f"""
📅 **Date Range**: {start_date} to {end_date}

📄 **Raw Submissions**: {total_raw_rows:,}
✅ **Unique Records (Filtered)**: {total_unique_rows:,}
📊 **Filtered Submissions**: {filtered_df.shape[0]:,}
📍 **Counties Covered**: {deduped_df['County'].nunique()}
🚫 **Counties with No Submissions**: {len(no_submission_counties)} ({', '.join(no_submission_counties)})
"""
st.text_area("📋 Copy this Summary for Emailing:", value=summary_text, height=200)
if st.button("📋 Copy to Clipboard"):
    pyperclip.copy(summary_text)
    st.success("✅ Summary copied to clipboard!")

# -------------------- WORD EXPORT --------------------
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

# -------------------- COUNTY VISUALIZATION --------------------
st.subheader("📍 Submissions by County")
county_counts = deduped_df.groupby('County').size().reset_index(name='Submissions')
fig_bar = px.bar(county_counts, x='County', y='Submissions', color='County', title='Number of Unique Submissions by County')
st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("📊 County Submissions Data")
st.dataframe(county_counts)

csv_data = county_counts.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Download County Submissions CSV",
    data=csv_data,
    file_name=f"County_Submissions_{datetime.now().date()}.csv",
    mime='text/csv'
)

# -------------------- DAILY TREND --------------------
st.subheader("📆 Submissions Over Time")
daily_counts = deduped_df.groupby(deduped_df['Timestamp'].dt.date).size().reset_index(name='Submissions')
fig_time = px.line(daily_counts, x='Timestamp', y='Submissions', title='Daily Submission Trend')
st.plotly_chart(fig_time, use_container_width=True)

# -------------------- NO-SUBMISSION COUNTIES --------------------
st.subheader("🚫 Counties with No Submissions")
if no_submission_counties:
    st.error(f"🚫 Counties with **NO** Submissions: {', '.join(no_submission_counties)}")
else:
    st.success("✅ All counties have submissions!")

# -------------------- DATA TABLES --------------------
st.subheader("📄 Filtered Raw Records (With Duplicates)")
st.dataframe(filtered_df)

st.subheader("✅ Cleaned Unique Records (Post-Filter)")
st.dataframe(deduped_df)

# -------------------- DOWNLOADS --------------------
csv_filtered = filtered_df.to_csv(index=False).encode('utf-8')
csv_deduped = deduped_df.to_csv(index=False).encode('utf-8')

st.download_button(
    label="📥 Download Filtered Data (Raw)",
    data=csv_filtered,
    file_name=f"Mentorship_Filtered_{datetime.now().date()}.csv",
    mime='text/csv'
)

st.download_button(
    label="✅ Download Cleaned Unique Records",
    data=csv_deduped,
    file_name=f"Mentorship_Unique_{datetime.now().date()}.csv",
    mime='text/csv'
)
