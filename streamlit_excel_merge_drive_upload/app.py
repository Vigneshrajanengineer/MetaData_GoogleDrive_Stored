import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import os

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

st.set_page_config(page_title="Excel Merger with Google Drive", layout="centered")
st.title("Multi-User Excel Merger with Admin & Google Drive Upload")

DATA_DIR = "merged_versions"
os.makedirs(DATA_DIR, exist_ok=True)
MASTER_FILE = os.path.join(DATA_DIR, "master_merged_data.xlsx")
ADMIN_PASSWORD = "admin123"

# Authenticate and create PyDrive client
@st.cache_resource
def init_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)

uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx", "xls"], accept_multiple_files=True)
user_name = st.text_input("Enter your name or identifier:")
sheet_name = st.text_input("Sheet name to merge (optional)", value="")

# Load existing data
if os.path.exists(MASTER_FILE):
    master_df = pd.read_excel(MASTER_FILE)
else:
    master_df = pd.DataFrame()

if st.button("Merge Files"):
    if not uploaded_files or not user_name:
        st.warning("Please upload files and enter your name.")
    else:
        dfs = []
        for file in uploaded_files:
            try:
                df = pd.read_excel(file, sheet_name=sheet_name if sheet_name else 0)
                df["UploadedBy"] = user_name
                df["FileName"] = file.name
                df["UploadTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                dfs.append(df)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if dfs:
            new_data = pd.concat(dfs, ignore_index=True)
            master_df = pd.concat([master_df, new_data], ignore_index=True)

            master_df.to_excel(MASTER_FILE, index=False)

            # Save versioned copy
            version_filename = f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            version_path = os.path.join(DATA_DIR, version_filename)
            master_df.to_excel(version_path, index=False)

            st.success(f"Data merged and saved as {version_filename}!")

            # Upload to Google Drive
            drive = init_drive()
            file_drive = drive.CreateFile({'title': version_filename})
            file_drive.SetContentFile(version_path)
            file_drive.Upload()
            st.success("Uploaded latest version to your Google Drive!")

st.subheader("Admin Access: Download Merged Data")
admin_pass = st.text_input("Enter admin password:", type="password")

if admin_pass == ADMIN_PASSWORD:
    if not master_df.empty:
        buffer = BytesIO()
        master_df.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button("Download Master Merged File", buffer, "master_merged_data.xlsx")

        st.markdown("### Previous Versions")
        versions = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("merged_")], reverse=True)
        for file in versions:
            with open(os.path.join(DATA_DIR, file), "rb") as f:
                st.download_button(f"Download {file}", f, file)
    else:
        st.info("No merged data available.")
elif admin_pass and admin_pass != ADMIN_PASSWORD:
    st.error("Incorrect admin password.")