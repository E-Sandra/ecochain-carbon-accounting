import streamlit as st
from google.cloud import storage
import json
import time

BUCKET_NAME = "ecochain-trace-d56fa"

st.set_page_config(page_title="EcoChain Portal", layout="centered")

st.title("🌱 EcoChain Trace Portal")
st.markdown("Upload vendor utility receipts or capture them live alongside production volume metadata.")

enterprise_name = st.text_input("Enterprise Name", value="Global Eco Corp")
vendor_name = st.text_input("Vendor Name", value="EcoPower Ltd")

col1, col2 = st.columns(2)
with col1:
    bill_year = st.selectbox("Bill Year", [2024, 2025, 2026], index=2)
with col2:
    bill_month = st.selectbox(
        "Bill Month", 
        ["January", "February", "March", "April", "May", "June", 
         "July", "August", "September", "October", "November", "December"]
    )

units_manufactured = st.number_input("Units Manufactured", min_value=0, value=5000)

st.subheader("Receipt Input Options")
uploaded_files = st.file_uploader(
    "Upload Utility Receipts (PDF, Images)", 
    type=["pdf", "png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

camera_image = None
if st.checkbox("📸 Use Live Camera to Capture Receipt"):
    camera_image = st.camera_input("Take a photo")

if st.button("Process & Upload Data"):
    files_to_process = []
    if uploaded_files:
        files_to_process.extend(uploaded_files)
    if camera_image:
        camera_image.name = f"live_capture_{int(time.time())}.jpg"
        files_to_process.append(camera_image)

    if not files_to_process:
        st.warning("Please upload at least one receipt file or capture a photo.")
    else:
        with st.spinner("Uploading files and metadata to Cloud Storage..."):
            try:
                storage_client = storage.Client()
                bucket = storage_client.bucket(BUCKET_NAME)
                
                timestamp = int(time.time())
                
                clean_ent = enterprise_name.strip().lower().replace(" ", "_")
                clean_vend = vendor_name.strip().lower().replace(" ", "_")
                
                metadata_payload = {
                    "enterprise_name": enterprise_name,
                    "vendor_name": vendor_name,
                    "bill_year": bill_year,
                    "bill_month": bill_month,
                    "units_manufactured": units_manufactured,
                    "submission_timestamp": timestamp
                }
                
                meta_blob_name = f"vendor_production_volume/{clean_ent}_{clean_vend}_{bill_year}_{bill_month}_{timestamp}.json"
                meta_blob = bucket.blob(meta_blob_name)
                meta_blob.upload_from_string(json.dumps(metadata_payload), content_type="application/json")
                
                for file_obj in files_to_process:
                    file_name = file_obj.name
                    receipt_blob_name = f"raw_receipts/{clean_ent}_{clean_vend}_{bill_year}_{bill_month}_{timestamp}_{file_name}"
                    receipt_blob = bucket.blob(receipt_blob_name)
                    receipt_blob.upload_from_file(file_obj, content_type=getattr(file_obj, 'type', 'image/jpeg'))
                
                st.success(f"Successfully processed and uploaded metadata along with {len(files_to_process)} receipt(s)!")
            except Exception as e:
                st.error(f"Upload failed: {str(e)}")
