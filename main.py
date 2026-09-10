import os
import json
import time
from datetime import datetime
from enum import Enum
import functions_framework
from google import genai
from google.cloud import bigquery
from google.cloud import storage
from google.genai import types
from google.genai.errors import ServerError
from pydantic import BaseModel, Field

RECEIPTS_TABLE = "ecochain-trace-d56fa.ecochain_data.receipts"
PRODUCTION_TABLE = "ecochain-trace-d56fa.ecochain_data.vendor_production_volume"
STAGING_BUCKET = "ecochain-trace-d56fa-staging" 

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12
}

PROCESSED_EVENTS = {}
EVENT_TTL_SECONDS = 300

class UtilityCategory(str, Enum):
    ELECTRICITY_GRID = "electricity_grid"
    DIESEL_FUEL = "diesel_fuel"
    PETROL_GASOLINE = "petrol_gasoline"
    NATURAL_GAS = "natural_gas"
    SOLID_WASTE = "solid_waste"
    WATER_SUPPLY = "water_supply"
    PROPANE = "propane"

class UnitOfMeasure(str, Enum):
    ML = "mL"
    LITERS = "Liters"
    KL = "kL"
    GRAMS = "grams"
    KG = "kg"
    TONNES = "tonnes"
    WH = "Wh"
    KWH = "kWh"
    MWH = "MWh"
    THERMS = "Therms"
    MMBTU = "MMBtu"
    CUBIC_METERS = "Cubic Meters"

class InvoiceExtraction(BaseModel):
    utility_category: UtilityCategory = Field(description="The utility category.")
    consumption_amount: float = Field(description="The numeric consumption amount.")
    unit_of_measure: UnitOfMeasure = Field(description="The standardized unit of measurement.")
    billing_date: str = Field(description="The bill issue date (YYYY-MM-DD).")

SYSTEM_INSTRUCTION = """You are an expert environmental auditor extracting consumption data.
Guidelines for unit_of_measure (DO NOT convert mathematically, just classify):
- 'ml', 'milliliter' -> 'mL'
- 'l', 'L', 'litre', 'litres' -> 'Liters'
- 'kl', 'kiloliter' -> 'kL'
- 'g', 'gram' -> 'grams'
- 'kg', 'kilogram' -> 'kg'
- 't', 'tonne', 'metric ton' -> 'tonnes'
- 'wh' -> 'Wh'
- 'kwh', 'kilowatt hour' -> 'kWh'
- 'mwh', 'megawatt hour' -> 'MWh'
- 'therm', 'therms' -> 'Therms'
- 'mmbtu' -> 'MMBtu'
- 'm3', 'cubic meter' -> 'Cubic Meters'
Extract the physical consumption amount (NOT financial total) and the billing date.
"""

@functions_framework.cloud_event
def process_storage_upload(cloud_event):
    global PROCESSED_EVENTS
    event_id = cloud_event.get("id") if hasattr(cloud_event, "get") else getattr(cloud_event, "id", None)
    
    if event_id:
        current_time = time.time()
        PROCESSED_EVENTS = {eid: ts for eid, ts in PROCESSED_EVENTS.items() if current_time - ts < EVENT_TTL_SECONDS}
        
        if event_id in PROCESSED_EVENTS:
            print(f"Skipping duplicate CloudEvent delivery for ID: {event_id}")
            return
        
        PROCESSED_EVENTS[event_id] = current_time

    try:
        data = cloud_event.data
        file_path = data["name"]

        if file_path.startswith("raw_receipts/") and not file_path.endswith("/"):
            _process_receipt_logic(cloud_event)
        elif file_path.startswith("vendor_production_volume/") and not file_path.endswith("/"):
            _process_production_logic(cloud_event)
            
    except Exception as e:
        if event_id and event_id in PROCESSED_EVENTS:
            del PROCESSED_EVENTS[event_id]
        raise e

def _stage_and_load_to_bq(bq_client, storage_client, bucket_name, row_data, table_id, file_name):
    staging_blob_name = f"staging/{file_name}_{int(time.time())}.json"
    bucket = storage_client.bucket(bucket_name)
    staging_blob = bucket.blob(staging_blob_name)
    
    ndjson_data = json.dumps(row_data) + "\n"
    staging_blob.upload_from_string(ndjson_data, content_type="application/json")
    
    gcs_uri = f"gs://{bucket_name}/{staging_blob_name}"
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        ignore_unknown_values=True,
    )
    
    load_job = bq_client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    load_job.result()  
    
    try:
        staging_blob.delete()
    except Exception:
        pass

def _parse_month(raw_month):
    if not raw_month:
        return 1
    if isinstance(raw_month, int):
        return raw_month
    cleaned = str(raw_month).strip().lower()
    if cleaned.isdigit():
        return int(cleaned)
    return MONTH_MAP.get(cleaned, 1)

def _process_receipt_logic(cloud_event):
    try:
        bq_client = bigquery.Client()
        storage_client = storage.Client()
        
        # Vertex AI client configuration to utilize GCP promotional credits
        genai_client = genai.Client(
            vertexai=True,
            project="ecochain-trace-d56fa",
            location="us-central1"
        )

        data = cloud_event.data
        bucket_name = data["bucket"]
        file_path = data["name"]
        file_name = os.path.basename(file_path)

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.get_blob(file_path)
        if not blob: return

        parts = file_name.split("_")
        timestamp = None
        for part in parts:
            if part.isdigit() and len(part) >= 9:
                timestamp = part
                break

        metadata = {}
        if timestamp:
            blobs = list(bucket.list_blobs(prefix="vendor_production_volume/"))
            for b in blobs:
                if timestamp in b.name:
                    content = b.download_as_text()
                    try:
                        metadata = json.loads(content.replace("'", "\""))
                    except Exception:
                        metadata = eval(content)
                    break

        enterprise_name = str(metadata.get("enterprise_name", "unknown enterprise")).strip().lower()
        vendor_name = str(metadata.get("vendor_name", "unknown vendor")).strip().lower()

        file_bytes = blob.download_as_bytes()
        
        file_ext = os.path.splitext(file_name)[1].lower()
        if file_ext in ['.jpg', '.jpeg', '.jfif', '.jpe']:
            mime_type = "image/jpeg"
        elif file_ext == '.png':
            mime_type = "image/png"
        elif file_ext == '.webp':
            mime_type = "image/webp"
        elif file_ext in ['.heic', '.heif']:
            mime_type = "image/heic"
        elif file_ext == '.pdf':
            mime_type = "application/pdf"
        else:
            mime_type = blob.content_type or "image/jpeg"

        models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash"]
        response = None

        for model_name in models_to_try:
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                try:
                    response = genai_client.models.generate_content(
                        model=model_name,
                        contents=[
                            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                            "Extract the activity consumption and utility category from this document."
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            response_schema=InvoiceExtraction,
                            temperature=0.0,
                            tools=[],
                        ),
                    )
                    success = True
                    break
                except ServerError as e:
                    if e.code == 503 and attempt < max_retries - 1:
                        time.sleep((2 ** attempt) + (0.1 * attempt))
                        continue
                    if model_name == models_to_try[-1]:
                        raise e
                    break
            if success:
                break

        if not response or not response.parsed:
            print(f"Failed to parse response from Gemini for file: {file_name}")
            return

        extracted = response.parsed

        try:
            parsed_date = datetime.strptime(extracted.billing_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            parsed_date = datetime.utcnow().date()

        bill_year = metadata.get("bill_year") or parsed_date.year
        raw_bill_month = metadata.get("bill_month")
        prod_month_num = _parse_month(raw_bill_month)
        production_month = str(prod_month_num).zfill(2)
        production_year = int(bill_year)

        row_to_insert = {
            "enterprise_name": enterprise_name,
            "vendor_name": vendor_name,
            "utility_category": extracted.utility_category.value,
            "consumption_amount": float(extracted.consumption_amount),
            "unit_of_measure": extracted.unit_of_measure.value,
            "billing_date": parsed_date.isoformat(),
            "billing_year": parsed_date.year,
            "billing_month": parsed_date.month,
            "billing_day": parsed_date.day,
            "production_year": production_year,
            "production_month": production_month,
            "file_name": file_name,
            "submission_timestamp": datetime.utcnow().isoformat(),
        }

        _stage_and_load_to_bq(bq_client, storage_client, bucket_name, row_to_insert, RECEIPTS_TABLE, file_name)
        print(f"Successfully staged and loaded receipt for file: {file_name}")

    except Exception as e:
        print(f"CRITICAL ERROR in _process_receipt_logic: {str(e)}", flush=True)
        raise e

def _process_production_logic(cloud_event):
    try:
        bq_client = bigquery.Client()
        storage_client = storage.Client()

        data = cloud_event.data
        bucket_name = data["bucket"]
        file_path = data["name"]
        file_name = os.path.basename(file_path)

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.get_blob(file_path)
        if not blob: return

        file_content = blob.download_as_text()
        try:
            prod_data = json.loads(file_content)
        except Exception:
            prod_data = eval(file_content)

        enterprise_name = str(prod_data.get("enterprise_name", "")).strip().lower()
        vendor_name = str(prod_data.get("vendor_name", "")).strip().lower()

        raw_year = prod_data.get("bill_year") or prod_data.get("production_year")
        raw_month = prod_data.get("bill_month") or prod_data.get("production_month")
        
        prod_month_num = _parse_month(raw_month)
        production_month = str(prod_month_num).zfill(2)
        production_year = int(raw_year) if raw_year else None

        raw_units = prod_data.get("units_manufactured") or prod_data.get("total_units_manufactured", 0)
        total_units = int(raw_units) if str(raw_units).isdigit() else 0

        row_to_insert = {
            "enterprise_name": enterprise_name,
            "vendor_name": vendor_name,
            "production_year": production_year,
            "production_month": production_month,
            "total_units_manufactured": total_units,
            "file_name": file_name,
            "submission_timestamp": datetime.utcnow().isoformat(),
        }

        _stage_other = _stage_and_load_to_bq(bq_client, storage_client, bucket_name, row_to_insert, PRODUCTION_TABLE, file_name)
        print(f"Successfully staged and loaded production volume for file: {file_name}")

    except Exception as e:
        print(f"CRITICAL ERROR in _process_production_logic: {str(e)}", flush=True)
        raise e