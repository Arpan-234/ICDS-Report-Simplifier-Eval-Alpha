import streamlit as st
import pandas as pd
import io
import os
from collections import defaultdict

st.title("AWC-Centric CSV Merger with Total Row")

# Upload centres.txt
st.header("Step 1: Upload centres.txt")
centres_file = st.file_uploader("Upload centres.txt", type=["txt"])

# Upload multiple CSVs
st.header("Step 2: Upload all CSV files")
csv_files = st.file_uploader(
    "Upload one or more CSV files",
    type=["csv"],
    accept_multiple_files=True
)

month_name = st.text_input("Enter the Month for file naming (e.g., April)")

def file_to_list(file_obj):
    """Read centres.txt into a list of AWC names."""
    lines = file_obj.read().decode("utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip()]

def read_clean_csv(file_obj):
    """Skip non-header rows and return a clean DataFrame."""
    content = file_obj.read().decode("utf-8").splitlines()
    header_row = next((i for i, line in enumerate(content) if line.strip().startswith("AWC")), None)
    if header_row is None:
        st.warning(f"Skipping file (no valid header found).")
        return None
    cleaned = "\n".join(content[header_row:])
    return pd.read_csv(io.StringIO(cleaned))

if centres_file and csv_files:
    centres = file_to_list(centres_file)

    all_data = []
    for uploaded in csv_files:
        df = read_clean_csv(uploaded)
        if df is None or 'AWC' not in df.columns:
            st.warning(f"Skipping {uploaded.name} due to missing 'AWC' column or invalid format.")
            continue
        df = df[df['AWC'].isin(centres)]  # Filter to only allowed AWC values
        all_data.append(df)

    if not all_data:
        st.error("No valid CSVs were processed.")
    else:
        merged = pd.concat(all_data, ignore_index=True)

        # Group by AWC and sum numeric columns
        grouped = merged.groupby('AWC', as_index=False).sum(numeric_only=True)

        # Ensure all 35 AWCs are included, even if not present in the input
        full_df = pd.DataFrame({'AWC': centres})
        merged_final = full_df.merge(grouped, on='AWC', how='left')

        # Fill NaNs with 0 or appropriate blank
        for col in merged_final.columns[1:]:
            if pd.api.types.is_numeric_dtype(merged_final[col]):
                merged_final[col] = merged_final[col].fillna(0)
            else:
                merged_final[col] = merged_final[col].fillna("")

        # Add Total row (sum of numeric columns)
        total_row = pd.DataFrame(merged_final.select_dtypes(include='number').sum()).T
        total_row.insert(0, "AWC", "Total")
        final_with_total = pd.concat([merged_final, total_row], ignore_index=True)

        # Show and download
        st.success("Merged data with totals ready.")
        st.dataframe(final_with_total)

        # Create Excel file in memory
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            final_with_total.to_excel(writer, sheet_name='Merged Data', index=False)
            
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Merged Data']
            
            # Add some formatting to the Total row
            bold_format = workbook.add_format({'bold': True})
            last_row = len(final_with_total)
            for col_num, _ in enumerate(final_with_total.columns):
                worksheet.write(last_row, col_num, final_with_total.iloc[-1, col_num], bold_format)

        # Reset buffer position to beginning
        buffer.seek(0)

        # Provide download button for the Excel file
        st.download_button(
            label="Download Merged Excel File",
            data=buffer,
            file_name=f"AWC_Merged_{month_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Also provide CSV download option
        csv_buffer = io.StringIO()
        final_with_total.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download Merged CSV File",
            data=csv_buffer.getvalue().encode(),
            file_name=f"AWC_Merged_{month_name}.csv",
            mime="text/csv"
        )
else:
    st.info("Upload both centres.txt and CSV files to begin.")