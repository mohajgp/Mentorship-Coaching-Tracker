import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Mentorship Dashboard", layout="wide")
st.title("🤝 Mentorship Session Tracker")

uploaded_file = st.file_uploader("Upload cleaned mentorship Excel file", type=["xlsx"])
if uploaded_file is None:
    st.info("Please upload a file to proceed.")
    st.stop()

# -------------------- LOAD DATA --------------------
df = pd.read_excel(uploaded_file)
df.columns = df.columns.str.strip()

# Standardize column names
rename_map = {
    "Session Date": "Date",
    "County of session": "County",
    "Phone Number": "Phone",
    "ID Number": "ID",
    "Session Topic": "Topic",
    "Mentor Name": "Mentor",
    "Gender of the Participant": "Gender",
    "Age  of the Participant": "Age"
}
df.rename(columns=rename_map, inplace=True)

# Parse dates and clean strings
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df[df["Date"].notna()]
df["Phone"] = df["Phone"].astype(str).str.extract(r'(\d{9,12})')
df["ID"] = df["ID"].astype(str).str.extract(r'(\d{5,})')
df["Gender"] = df["Gender"].str.strip().str.title()
df["County"] = df["County"].str.strip().str.title()
df["Mentor"] = df["Mentor"].str.strip().str.title()

# -------------------- FILTERS --------------------
st.sidebar.header("📊 Filters")
all_counties = df["County"].dropna().unique()
selected_counties = st.sidebar.multiselect("Select Counties", sorted(all_counties), default=sorted(all_counties))
start_date = st.sidebar.date_input("Start Date", df["Date"].min())
end_date = st.sidebar.date_input("End Date", df["Date"].max())

date_mask = (df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))
county_mask = df["County"].isin(selected_counties)
filtered_df = df[date_mask & county_mask]

# -------------------- DEDUPLICATION --------------------
deduped_df = filtered_df.drop_duplicates(subset=["ID", "Phone", "County", "Date"], keep="first")
total_unique_rows = deduped_df.shape[0]

# -------------------- METRICS --------------------
st.subheader("\ud83d\udcca Summary Metrics")

# Youth and Female Youth Calculation
youth_df = deduped_df[(deduped_df['Age'] >= 18) & (deduped_df['Age'] <= 35)]
female_youth_df = youth_df[youth_df['Gender'] == "Female"]

total_records = deduped_df.shape[0]
youth_pct = (len(youth_df) / total_records * 100) if total_records else 0
female_youth_pct = (len(female_youth_df) / total_records * 100) if total_records else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("\ud83d\udcc4 Filtered Raw Records", f"{filtered_df.shape[0]:,}")
col2.metric("\u2705 Unique Records (Post-Dedup)", f"{total_unique_rows:,}")
col3.metric("\ud83d\udcca Filtered Sessions", f"{total_unique_rows:,}")
col4.metric("\ud83d\udccd Counties Covered", deduped_df['County'].nunique())
col5.metric("\ud83e\uddd2 % Youth (18-35)", f"{youth_pct:.1f}%")
col6.metric("\u2640\ufe0f % Female Youth", f"{female_youth_pct:.1f}%")

# -------------------- AUTO SUMMARY --------------------
full_county_list = [
    "Homa Bay", "Trans Nzoia", "Kisumu", "Baringo", "Uasin Gishu", "Kericho", "Marsabit", "Kakamega",
    "Nyandarua", "Kajiado", "Nairobi", "Bungoma", "West Pokot", "Nyeri", "Nandi", "Laikipia", "Makueni",
    "Samburu", "Busia", "Kirinyaga", "Nakuru", "Isiolo", "Tharaka Nithi", "Elgeyo Marakwet", "Kiambu", "Kisii",
    "Siaya", "Turkana", "Nyamira", "Murang'A", "Vihiga", "Wajir", "Machakos", "Migori", "Kitui", "Kwale",
    "Tana River", "Bomet", "Narok", "Mombasa", "Mandera", "Garissa", "Embu", "Lamu", "Taita Taveta",
    "Meru", "Kilifi"
]
no_submission_counties = [c for c in full_county_list if c not in deduped_df["County"].unique()]

summary_text = f"""
\ud83d\udcc5 **Date Range**: {start_date} to {end_date}

\ud83d\udcc4 **Filtered Raw Records**: {filtered_df.shape[0]:,}
\u2705 **Unique Records (Post-Dedup)**: {total_unique_rows:,}
\ud83d\udcca **Filtered Sessions**: {total_unique_rows:,}
\ud83e\uddd2 **% Youth (18–35 years)**: {youth_pct:.1f}%
\u2640\ufe0f **% Female Youth (18–35)**: {female_youth_pct:.1f}%
\ud83d\udccd **Counties Covered**: {deduped_df['County'].nunique()}
\ud83d\udeab **Counties with No Submissions**: {len(no_submission_counties)} ({', '.join(no_submission_counties)})
"""
st.info(summary_text)

# -------------------- DATA TABLE --------------------
st.subheader("\ud83d\udcc3 Cleaned Mentorship Submissions")
st.dataframe(deduped_df.sort_values("Date", ascending=False), use_container_width=True)
