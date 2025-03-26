import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pyperclip

# -------------------- PAGE CONFIGURATION --------------------
st.set_page_config(
    page_title="KNCCI Mentorship Dashboard",
    page_icon="",
    layout="wide"
)

st.title(" KNCCI Jiinue Mentorship Dashboard")
st.caption("Tracking Mentorship Sessions by Field Officers")

# -------------------- SETTINGS --------------------
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/107tWhbwBgF89VGCRnNSL4-_WrCIa68NGSPA4GkwVjDE/export?format=csv"

# -------------------- FUNCTION TO LOAD DATA --------------------
@st.cache_data(ttl=300)
def load_data(url):
    with st.spinner("Loading data..."):
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()

        # Convert and clean
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df['County'] = df['County'].str.strip().str.title()
        df['Gender'] = df['Gender'].str.strip().str.title()

        # Clean Age column
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce')

    return df

# -------------------- LOAD DATA --------------------
df = load_data(SHEET_CSV_URL)

# -------------------- VALIDATION --------------------
if df.empty:
    st.error(" No data available! Please check the spreadsheet link.")
    st.stop()

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header(" Filter Sessions")

min_date = df['Timestamp'].min().date()
max_date = df['Timestamp'].max().date()

# Show date range in sidebar
st.sidebar.markdown(f" **Earliest Submission**: `{min_date}`")
st.sidebar.markdown(f" **Latest Submission**: `{max_date}`")

# Date Range Filter
date_range = st.sidebar.date_input(
    "Select Date Range:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Unpack tuple or single date
if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

# County Filter
counties = df['County'].dropna().unique()
selected_counties = st.sidebar.multiselect(
    "Select Counties:",
    options=sorted(counties),
    default=sorted(counties)
)

# Gender Filter
genders = df['Gender'].dropna().unique()
selected_genders = st.sidebar.multiselect(
    "Select Gender:",
    options=sorted(genders),
    default=sorted(genders)
)

# Type of TA Received (Includes all values even if no filter is selected)
ta_types = df['Type of TA Received'].dropna().unique()
selected_ta = st.sidebar.multiselect(
    "Select Type of TA Received:",
    options=sorted(ta_types)
)

# Reset Filters Button
if st.sidebar.button(" Reset Filters"):
    st.experimental_rerun()

# -------------------- APPLY FILTERS --------------------
filtered_df = df[
    (df['Timestamp'].dt.date >= start_date) &
    (df['Timestamp'].dt.date <= end_date) &
    (df['County'].isin(selected_counties)) &
    (df['Gender'].isin(selected_genders))
]

# Apply "Type of TA Received" filter only if selected
if selected_ta:
    filtered_df = filtered_df[filtered_df['Type of TA Received'].isin(selected_ta)]
# Filter counties with no submissions within the selected date range
submitted_counties = df[df['Timestamp'].dt.date.between(start_date, end_date)]['County'].unique().tolist()

no_submission_counties = [county for county in all_counties_47 if county not in submitted_counties]

# Display counties with no submissions
if no_submission_counties:
    st.error(f" Counties with **NO** Submissions between `{start_date}` and `{end_date}`:")
    st.markdown(", ".join(no_submission_counties))
    st.write(f"Total Counties with No Submissions: **{len(no_submission_counties)}**")

    # Prepare copy text
    copy_text = f"""
 Counties with No Submissions

 Period: {start_date} to {end_date}

Counties with NO Submissions:
"""
    for county in no_submission_counties:
        copy_text += f"- {county}\n"

    copy_text += f"\n Total Counties with No Submissions: {len(no_submission_counties)}"

    # Text area for preview and manual copy
    st.text_area(" Copy the report below:", value=copy_text, height=250)

    # Copy to clipboard button
    if st.button(" Copy to Clipboard"):
        pyperclip.copy(copy_text)
        st.success(" Text copied to clipboard!")

else:
    st.success(" All counties have submissions in the selected date range.")

# -------------------- DATA TABLE --------------------
st.subheader(" Filtered Data Table")

if not filtered_df.empty:
    st.dataframe(filtered_df)
else:
    st.info(" No submissions found for the selected filters.")

# -------------------- DOWNLOAD BUTTON --------------------
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if not filtered_df.empty:
    csv_data = convert_df_to_csv(filtered_df)

    st.download_button(
        label=" Download Filtered Data as CSV",
        data=csv_data,
        file_name=f"Mentorship_Submissions_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime='text/csv'
    )

st.success(" Dashboard updated in real-time!")
