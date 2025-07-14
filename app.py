import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="KNCCI Mentorship Dashboard",
    layout="wide"
)

st.title("KNCCI Jiinue Mentorship Dashboard")
st.caption("Tracking Mentorship Sessions by Field Officers")

# -------------------- SETTINGS --------------------
OLD_FORM_URL = "https://docs.google.com/spreadsheets/d/107tWhbwBgF89VGCRnNSL4-_WrCIa68NGSPA4GkwVjDE/export?format=csv"
NEW_FORM_URL = "https://docs.google.com/spreadsheets/d/1CA7WvTkEUfeMyLuxhP91BgSWbkhV_S8V94kACj5LUMM/export?format=csv"

# -------------------- LOAD AND MERGE --------------------
@st.cache_data(ttl=300)
def load_raw_data():
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

    for col in df_new.columns:
        if col not in df_old.columns:
            df_old[col] = pd.NA
    df_old = df_old[df_new.columns]

    merged_df = pd.concat([df_old, df_new], ignore_index=True)
    return merged_df

# -------------------- LOAD --------------------
df_raw = load_raw_data()
if df_raw.empty:
    st.error("❌ No data available! Please check both spreadsheets.")
    st.stop()

# -------------------- GLOBAL DEDUP --------------------
df_raw['Month'] = df_raw['Timestamp'].dt.to_period('M')
deduplicated_global_df = df_raw.drop_duplicates(subset=['Phone Number', 'ID'], keep='first').copy()
global_unique_count = deduplicated_global_df.shape[0]

# -------------------- FILTERS --------------------
st.sidebar.header("🗓️ Filter Sessions")
min_date = df_raw['Timestamp'].min().date()
max_date = df_raw['Timestamp'].max().date()

date_range = st.sidebar.date_input("Select Date Range:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
start_date, end_date = date_range if isinstance(date_range, tuple) else (date_range, date_range)

form_versions = df_raw['Form Version'].unique().tolist()
selected_versions = st.sidebar.multiselect("Select Form Version:", options=form_versions, default=form_versions)

counties = df_raw['County'].dropna().unique()
selected_counties = st.sidebar.multiselect("Select Counties:", options=sorted(counties), default=sorted(counties))

genders = df_raw['Gender'].dropna().unique()
selected_genders = st.sidebar.multiselect("Select Gender:", options=sorted(genders), default=sorted(genders))

# -------------------- APPLY FILTERS --------------------
filtered_df = df_raw[
    (df_raw['Timestamp'].dt.date >= start_date) &
    (df_raw['Timestamp'].dt.date <= end_date) &
    (df_raw['Form Version'].isin(selected_versions)) &
    (df_raw['County'].isin(selected_counties)) &
    (df_raw['Gender'].isin(selected_genders))
]

deduped_filtered_df = filtered_df.drop_duplicates(subset=['Phone Number', 'ID'])

# -------------------- METRICS --------------------
st.subheader("📈 Summary Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Filtered Raw Records", f"{filtered_df.shape[0]:,}")
col2.metric("✅ Unique After Cleaning", f"{deduped_filtered_df.shape[0]:,}")
col3.metric("📊 Global Unique Participants", f"{global_unique_count:,}")
col4.metric("📍 Counties Covered", deduped_filtered_df['County'].nunique())

# -------------------- GLOBAL UNIQUE: MONTHLY & COUNTY --------------------
st.subheader("📊 Monthly & County Stats (Global Unique Participants)")

monthly_county_stats = (
    deduplicated_global_df
    .groupby(['Month', 'County'])
    .size()
    .reset_index(name='Unique Participants')
    .sort_values(['Month', 'County'])
)
monthly_county_stats['Month'] = monthly_county_stats['Month'].astype(str)

if not monthly_county_stats.empty:
    st.dataframe(monthly_county_stats, use_container_width=True)

    heatmap_data = monthly_county_stats.pivot(index='County', columns='Month', values='Unique Participants').fillna(0)
    fig_heatmap = px.imshow(
        heatmap_data,
        labels=dict(x="Month", y="County", color="Participants"),
        text_auto=True,
        aspect="auto",
        title="Unique Participants by County and Month (Global Dedup)"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
else:
    st.info("ℹ️ No data for monthly & county breakdown.")

# -------------------- AGE/GENDER BREAKDOWN --------------------
st.subheader("👥 Age & Gender Breakdown")

def categorize(row):
    try:
        age = int(row['Age'])
    except:
        return "Unknown"
    gender = str(row['Gender']).strip().lower()
    if 18 <= age <= 35:
        if gender == "female":
            return "Young female (18–35)"
        elif gender == "male":
            return "Young male (18–35)"
    elif age > 35:
        if gender == "female":
            return "Female above 35"
        elif gender == "male":
            return "Male above 35"
    return "Unknown"

deduped_filtered_df['Category'] = deduped_filtered_df.apply(categorize, axis=1)

cat_counts = deduped_filtered_df['Category'].value_counts()
cols = st.columns(5)
cols[0].metric("👩 Young Females", cat_counts.get('Young female (18–35)', 0))
cols[1].metric("👨 Young Males", cat_counts.get('Young male (18–35)', 0))
cols[2].metric("👩‍🦳 Females >35", cat_counts.get('Female above 35', 0))
cols[3].metric("👨‍🦳 Males >35", cat_counts.get('Male above 35', 0))
cols[4].metric("❓ Unknown", cat_counts.get('Unknown', 0))

# -------------------- COUNTY BAR CHART --------------------
st.subheader("📍 Submissions by County (Filtered View)")
county_counts = deduped_filtered_df.groupby('County').size().reset_index(name='Submissions')
fig_bar = px.bar(county_counts, x='County', y='Submissions', color='County', title='Unique Submissions by County')
st.plotly_chart(fig_bar, use_container_width=True)

# -------------------- DAILY TREND --------------------
st.subheader("📆 Unique Submissions Over Time (Filtered View)")
daily_counts = deduped_filtered_df.groupby(deduped_filtered_df['Timestamp'].dt.date).size().reset_index(name='Submissions')
fig_time = px.line(daily_counts, x='Timestamp', y='Submissions', title='Daily Unique Submission Trend')
st.plotly_chart(fig_time, use_container_width=True)

# -------------------- CLEANED TABLE --------------------
st.subheader("✅ Cleaned Unique Records (Post-Filter)")
st.dataframe(deduped_filtered_df)

# -------------------- DOWNLOADS --------------------
st.subheader("⬇️ Downloads")
st.download_button(
    label="📥 Download Global Unique Monthly & County Stats CSV",
    data=monthly_county_stats.to_csv(index=False).encode('utf-8'),
    file_name=f"Mentorship_Global_Unique_Monthly_County_{datetime.now().date()}.csv",
    mime='text/csv'
)

st.download_button(
    label="📥 Download Filtered Unique Records",
    data=deduped_filtered_df.to_csv(index=False).encode('utf-8'),
    file_name=f"Mentorship_Filtered_Unique_{datetime.now().date()}.csv",
    mime='text/csv'
)
