# 🌍 EcoChain: AI Carbon Accounting & Green Digital Passport

Serverless carbon accounting platform automating Scope 3 emissions, vendor utility tracking, and audit-ready **Green Digital Passports** for MSMEs and enterprises.

---

## 🚀 Live Application
- **App URL:** [https://ecochain-portal-574068444020.us-central1.run.app/](https://ecochain-portal-574068444020.us-central1.run.app/)

---

## ✨ Key Features & Functionality

1. **Theme & Navigation:** Dynamic light/dark/system theme toggle with intuitive sidebar filters.
2. **Metadata Mapping:** 
   - **Vendor Name:** Represents the MSME supplier.
   - **Enterprise Name:** Represents the primary firm.
   - **Billing Period:** Dropdowns for **Bill Year** and **Bill Month**.
3. **Multimodal Receipt Ingestion:**
   - *Mobile:* Upload files/photos or use the native phone camera.
   - *Laptop:* Upload files (PDF, PNG, JPG) or check **📸 Use Live Camera to Capture Receipt** to use the webcam.
   - *File Management:* Quick-remove cross (`×`) buttons on previews.
4. **AI Extraction Pipeline:** Event-driven Google Cloud Storage (`raw_receipts/`) and Eventarc triggers powered by Vertex AI (**Gemini Flash**) + **Pydantic** (`temperature=0.0`).
5. **Data Warehouse & Passport:** Google BigQuery tables/views (`calculated_emissions`, `product_carbon_footprint`) generating tamper-proof **Green Digital Passports**.

---

## 🛠️ Tech Stack
- **AI:** Google Cloud Vertex AI (Gemini Flash)
- **Backend:** Cloud Run functions, Functions Framework, Eventarc, Cloud Storage
- **Database:** Google BigQuery
- **Frontend:** Streamlit (Cloud Run)
- **Stack:** Python, Pandas, Pydantic

---

## 📂 Repository Structure

```text
ecochain/
├── main.py
├── app.py
├── Procfile
├── requirements.txt
├── README.md
└── sql/
    ├── tables/
    │   ├── receipts.sql
    │   ├── vendor_production_volume.sql
    │   └── emission_factors.sql
    └── views/
        ├── calculated_emissions.sql
        └── product_carbon_footprint.sql
