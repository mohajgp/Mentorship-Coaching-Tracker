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

    # Rename columns to a consistent set for critical filters/display
    # This only renames existing columns, doesn't drop others.
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

    # Convert Timestamp to datetime objects
    df_old['Timestamp'] = pd.to_datetime(df_old['Timestamp'], errors='coerce')
    df_new['Timestamp'] = pd.to_datetime(df_new['Timestamp'], errors='coerce')

    # Standardize 'County', 'Gender' by stripping spaces and title-casing
    df_old['County'] = df_old['County'].astype(str).str.strip().str.title()
    df_new['County'] = df_new['County'].astype(str).str.strip().str.title()

    df_old['Gender'] = df_old['Gender'].astype(str).str.strip().str.title()
    df_new['Gender'] = df_new['Gender'].astype(str).str.strip().str.title()

    # Convert 'Age' to numeric
    df_old['Age'] = pd.to_numeric(df_old['Age'], errors='coerce')
    df_new['Age'] = pd.to_numeric(df_new['Age'], errors='coerce')

    # Concatenate without dropping any columns.
    # Missing columns will be filled with NaN.
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

# NEW: Single County Selector for Detailed Report
st.sidebar.subheader("Generate County-Specific Report")
report_county = st.sidebar.selectbox("Select County for Detailed Report:", options=['None'] + sorted(counties.tolist()))


# Apply Filters for the main dashboard view
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
# Note: 'Unique Participants' calculation here is simplistic. If you have unique IDs for participants
# it would be better to use those to count unique individuals.
total_participants = filtered_df.drop_duplicates(subset=['County', 'Gender', 'Age']).shape[0] # More robust for this dataset

col1, col2, col3, col4 = st.columns(4)
col1.metric("✅ Total Sessions", f"{total_sessions:,}")
col2.metric("📊 Filtered Sessions", f"{filtered_sessions:,}")
col3.metric("📍 Counties Covered", unique_counties)
col4.metric("👥 Unique Participants (Est.)", total_participants) # Label changed for clarity

# -------------------- AUTO-GENERATED SUMMARY --------------------
st.subheader("📝 Auto-Generated Summary Report")
no_submission_counties = [c for c in all_counties_47 if c not in filtered_df['County'].unique()]
summary_text = f"""
📅 **Date Range**: {start_date} to {end_date}

✅ **Total Submissions**: {total_sessions:,}
📊 **Filtered Submissions**: {filtered_sessions:,}
📍 **Counties Covered**: {unique_counties}
👥 **Unique Participants (Est.)**: {total_participants}

🚫 **Counties with No Submissions (within selected filters)**: {len(no_submission_counties)}
"""
st.text_area("📋 Copy this Summary for Emailing:", value=summary_text, height=200)
if st.button("📋 Copy Overall Summary to Clipboard"):
    pyperclip.copy(summary_text)
    st.success("✅ Summary copied to clipboard!")

# -------------------- DOWNLOAD WORD REPORT (OVERALL) --------------------
st.subheader("📄 Export Overall Summary to Word Document")
if st.button("⬇️ Generate Overall Word Report"):
    doc = Document()
    doc.add_heading("KNCCI Jiinue Mentorship Overall Summary Report", level=1)
    doc.add_paragraph(summary_text)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    st.download_button(
        label="📥 Download Overall Word Report",
        data=buffer,
        file_name=f"Mentorship_Summary_Overall_{datetime.now().date()}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# -------------------- COUNTY-SPECIFIC REPORT --------------------
st.markdown("---") # Separator for visual clarity
if report_county != 'None':
    st.subheader(f"📝 Detailed Report for {report_county} County")

    # This DataFrame is specific to the selected `report_county` and current date/form/gender filters
    county_filtered_df = df[
        (df['Timestamp'].dt.date >= start_date) &
        (df['Timestamp'].dt.date <= end_date) &
        (df['Form Version'].isin(selected_versions)) &
        (df['County'] == report_county) & # Key filter for this section
        (df['Gender'].isin(selected_genders))
    ]

    if county_filtered_df.empty:
        st.info(f"ℹ️ No submissions found for **{report_county}** within the selected filters.")
    else:
        total_county_submissions = county_filtered_df.shape[0]

        # Calculate breakdown by Form Version
        form_version_counts = county_filtered_df['Form Version'].value_counts().to_dict()
        old_template_count = form_version_counts.get('Original', 0) # 'Original' corresponds to Old Template
        new_template_count = form_version_counts.get('New', 0) # 'New' corresponds to New Template

        county_report_text = f"""
Good afternoon,

Please find attached the data submission for {report_county} County.
The file includes:

A total of {total_county_submissions} business verifications
Mentorship and coaching data, split into two sheets based on the template used:
Old Template: {old_template_count} entries
New Template: {new_template_count} entries

Thank you.
"""
        st.text_area(f"📋 Copy Report for {report_county}:", value=county_report_text, height=250, key=f"county_report_text_{report_county}")

        col_copy, col_download = st.columns(2)
        with col_copy:
            if st.button(f"📋 Copy {report_county} Report to Clipboard", key=f"copy_button_{report_county}"):
                pyperclip.copy(county_report_text)
                st.success(f"✅ Report for {report_county} copied to clipboard!")
        with col_download:
            if st.button(f"⬇️ Generate Word Report for {report_county}", key=f"generate_word_button_{report_county}"):
                doc = Document()
                doc.add_heading(f"KNCCI Jiinue Mentorship Report - {report_county} County", level=1)
                doc.add_paragraph(county_report_text)
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                st.download_button(
                    label=f"📥 Download Word Report for {report_county}",
                    data=buffer,
                    file_name=f"Mentorship_Report_{report_county}_{datetime.now().date()}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"download_word_button_{report_county}"
                )
st.markdown("---") # Separator after county-specific report


# -------------------- COUNTY SUBMISSION BAR CHART --------------------
st.subheader("📍 Submissions by County")
if not filtered_df.empty:
    county_counts = filtered_df.groupby('County').size().reset_index(name='Submissions')
    fig_bar = px.bar(county_counts, x='County', y='Submissions', color='County', title='Number of Submissions by County')
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("ℹ️ No data to display for 'Submissions by County' based on current filters.")

# -------------------- COUNTY SUBMISSION TABLE AND DOWNLOAD --------------------
st.subheader("📊 County Submissions Data")
if not filtered_df.empty:
    county_submission_df = filtered_df.groupby('County').size().reset_index(name='Submissions')
    st.dataframe(county_submission_df)  # Display the table in Streamlit

    csv_data = county_submission_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download County Submissions CSV",
        data=csv_data,
        file_name=f"County_Submissions_{datetime.now().date()}.csv",
        mime='text/csv'
    )
else:
    st.info("ℹ️ No data to display for 'County Submissions Data' based on current filters.")

# -------------------- SUBMISSIONS OVER TIME --------------------
st.subheader("📆 Submissions Over Time")
if not filtered_df.empty:
    daily_counts = filtered_df.groupby(filtered_df['Timestamp'].dt.date).size().reset_index(name='Submissions')
    daily_counts.columns = ['Date', 'Submissions'] # Rename column for clarity
    fig_time = px.line(daily_counts, x='Date', y='Submissions', title='Daily Submission Trend')
    st.plotly_chart(fig_time, use_container_width=True)
else:
    st.info("ℹ️ No data to display for 'Submissions Over Time' based on current filters.")

# -------------------- NON-SUBMISSIONS --------------------
st.subheader("🚫 Counties with No Submissions (within filtered data)")
if no_submission_counties:
    st.error(f"🚫 Counties with **NO** Submissions: {', '.join(no_submission_counties)}")
else:
    st.success("✅ All counties have submissions in selected date range and filters.")

# -------------------- DATA TABLE & DOWNLOAD --------------------
st.subheader("📄 Filtered Data Table")
if not filtered_df.empty:
    st.dataframe(filtered_df)

    # Prepare data for multi-sheet Excel download
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Filter for 'Original' (Old Template)
        df_original = filtered_df[filtered_df['Form Version'] == 'Original']
        if not df_original.empty:
            # Optionally drop 'Form Version' if you prefer it not to appear on the sheet
            df_original_to_excel = df_original.drop(columns=['Form Version'], errors='ignore')
            df_original_to_excel.to_excel(writer, sheet_name='Old Template Data', index=False)
        else:
            # Create an empty DataFrame to write an empty sheet or a sheet with a message
            pd.DataFrame({"Message": ["No data for Old Template in this selection."]}).to_excel(writer, sheet_name='Old Template Data', index=False)


        # Filter for 'New' (New Template)
        df_new = filtered_df[filtered_df['Form Version'] == 'New']
        if not df_new.empty:
            # Optionally drop 'Form Version' if you prefer it not to appear on the sheet
            df_new_to_excel = df_new.drop(columns=['Form Version'], errors='ignore')
            df_new_to_excel.to_excel(writer, sheet_name='New Template Data', index=False)
        else:
            # Create an empty DataFrame to write an empty sheet or a sheet with a message
            pd.DataFrame({"Message": ["No data for New Template in this selection."]}).to_excel(writer, sheet_name='New Template Data', index=False)

    output.seek(0) # Rewind the buffer to the beginning

    st.download_button(
        label="📥 Download Filtered Data (Excel)",
        data=output,
        file_name=f"Mentorship_Filtered_Data_{datetime.now().date()}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
else:
    st.info("ℹ️ No submissions match current filters.")

# -------------------- MERGED DATA TABLE AND DOWNLOAD --------------------
st.subheader("➕ Merged Data Table (Raw Data)")
st.dataframe(df)

csv_data_merged = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Merged CSV",
    data=csv_data_merged,
    file_name=f"Mentorship_Merged_Data_{datetime.now().date()}.csv",
    mime='text/csv'
)
