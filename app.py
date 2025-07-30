import pandas as pd
import streamlit as st

st.title("KNCCI Mobilization Summary - Submissions by County")

# File uploader
uploaded_file = st.file_uploader("Upload the Mobilization Excel file", type=["xlsx"])

if uploaded_file:
    # Read the file
    df = pd.read_excel(uploaded_file)

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Normalize key column names
    column_map = {
        "County": "County",
        "Name of the Participant": "Name",
        " Phone Number(verify before entry)": "Phone",
        "Verified ID Number(Verify before entry)": "ID",
        "Age  of the Participant": "Age",
        "Gender of the Participant": "Gender"
    }

    df = df.rename(columns=column_map)

    # Remove rows with missing county or name
    df_cleaned = df.dropna(subset=["County", "Name"])

    # Group by County and count submissions
    county_counts = df_cleaned.groupby("County")["Name"].count().reset_index()
    county_counts = county_counts.rename(columns={"Name": "Submissions"})

    # Ensure all 47 counties are included
    all_counties = [
        "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta",
        "Garissa", "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka Nithi",
        "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga",
        "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia",
        "Uasin Gishu", "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru",
        "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma",
        "Busia", "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi"
    ]

    full_county_df = pd.DataFrame({'County': all_counties})
    merged = full_county_df.merge(county_counts, on='County', how='left')
    merged['Submissions'] = merged['Submissions'].fillna(0).astype(int)

    # Show submission table
    st.subheader("County Submissions")
    st.dataframe(merged.sort_values("Submissions", ascending=False).reset_index(drop=True))

    # Add Youth and Female Youth % calculation
    df_cleaned['Gender'] = df_cleaned['Gender'].astype(str).str.strip().str.lower()
    df_cleaned['Age'] = pd.to_numeric(df_cleaned['Age'], errors='coerce')

    is_youth = (df_cleaned['Age'] >= 18) & (df_cleaned['Age'] <= 35)
    is_female_youth = is_youth & (df_cleaned['Gender'] == 'female')

    county_summary = df_cleaned.groupby('County').agg(
        Total=('Name', 'count'),
        Youth=('Age', lambda x: ((x >= 18) & (x <= 35)).sum()),
        Female_Youth=('Age', lambda x: ((x >= 18) & (x <= 35) & (df_cleaned.loc[x.index, 'Gender'] == 'female')).sum())
    ).reset_index()

    county_summary['% Youth'] = (county_summary['Youth'] / county_summary['Total']) * 100
    county_summary['% Female Youth'] = (county_summary['Female_Youth'] / county_summary['Total']) * 100

    st.subheader("Youth Metrics by County")
    st.dataframe(county_summary.style.format({
        "% Youth": "{:.1f}%", 
        "% Female Youth": "{:.1f}%"
    }))

    # Show total number of rows for context
    st.info(f"Total Rows in Dataset: {len(df)} | Rows with valid County & Name: {len(df_cleaned)}")
