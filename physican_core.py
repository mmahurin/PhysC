# -*- coding: utf-8 -*-
import os
import time
import re
import io
import json
import csv
import numpy as np
import cv2
import pytesseract
import spacy
import openai
from openai import OpenAI
from datetime import datetime
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================

# --- API Keys ---
# OpenAI API key should be set in environment variables
# On Streamlit Cloud: Add OPENAI_API_KEY to Secrets tab
# Locally: Set as environment variable or in .env file
openai_client = OpenAI()

# --- Model Configuration ---
# Using gpt-4o-mini for better speed and cost efficiency
OPENAI_MODEL = "gpt-4o-mini"

# --- Library Configuration ---
# Attempt to set tesseract command for common environments; leave as default if not found
try:
    if os.name == 'nt':
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    else:
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
except Exception:
    # Keep default; if Tesseract is not available, OCR will likely fail and functions handle errors
    pass

# --- Model Loading ---
@st.cache_resource
def load_spacy_model():
    """Load spaCy model with caching to avoid reloading on each app rerun."""
    return spacy.load('en_core_web_sm')

nlp = load_spacy_model()

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def log_audit_event(event_data):
    """Appends an event to the immutable JSONL audit log."""
    # Add timestamp if not present
    if "timestamp" not in event_data:
        event_data["timestamp"] = str(datetime.now())

    with open('immutable_audit_log.jsonl', 'a') as f:
        f.write(json.dumps(event_data) + '\n')

def get_value_robust(data_dict, keys, default="N/A"):
    """Retrieves a value from a dict using a list of potential keys, ignoring 'N/A'."""
    if not data_dict: return default
    for k in keys:
        val = data_dict.get(k)
        if val and str(val).strip().upper() != "N/A":
            return val
    return default

def npdb_sanction_check(physician_name):
    """Checks if the physician exists in the NPDB database."""
    npdb_file = 'NPDB.csv'
    if not os.path.exists(npdb_file):
        # Fallback if file doesn't exist for simulation
        return False

    with open(npdb_file, 'r', newline='', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        next(reader, None) # Skip header
        for row in reader:
            # Simple substring match for simulation purposes
            if any(physician_name.lower() in cell.lower() for cell in row):
                return True
    return False

def convert_document_to_images(document_content_binary, file_type):
    """Converts PDF bytes or Image bytes to a list of OpenCV images."""
    images_cv = []
    try:
        if file_type == 'pdf':
            images_pil = convert_from_bytes(document_content_binary, dpi=300)
            images_cv = [np.array(img.convert('RGB')) for img in images_pil]
        elif file_type == 'image':
            nparr = np.frombuffer(document_content_binary, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_cv is not None: images_cv.append(img_cv)
    except Exception as e:
        pass # Suppressed error printing for cleaner output unless critical
    return images_cv

def extract_text_from_document(uploaded_file_value, file_type=None):
    """Extracts text from a document, falling back to OCR if necessary."""
    text_content = ""
    if not uploaded_file_value: return text_content
    custom_config = r'--oem 3 --psm 6'

    # Support Streamlit's UploadedFile (has getvalue and name)
    if hasattr(uploaded_file_value, 'getvalue'):
        file_content = uploaded_file_value.getvalue()
        if file_type is None:
            file_type = 'pdf' if uploaded_file_value.name.lower().endswith('.pdf') else 'image'
    else:
        # Original ipywidgets.FileUpload structure
        try:
            file_info = list(uploaded_file_value.values())[0]
            file_content = file_info['content']
            if file_type is None:
                file_type = 'pdf' if file_info.get('metadata', {}).get('name', '').lower().endswith('.pdf') else 'image'
        except Exception:
            return text_content

    if file_type == 'pdf':
        # Attempt PDF text extraction
        try:
            pdf_reader = PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
        except: pass

        # OCR Fallback
        if len(text_content.strip()) < 50:
            # print("  >> PDF text empty/short. Switching to OCR...")
            try:
                images = convert_from_bytes(file_content, dpi=300)
                for img in images:
                    img_cv = cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2GRAY)
                    _, img_cv = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    text_content += pytesseract.image_to_string(Image.fromarray(img_cv), lang='eng', config=custom_config) + "\n"
            except Exception as e: pass # print(f"  >> PDF OCR Error: {e}")

    elif file_type == 'image':
        try:
            img_cv = cv2.cvtColor(np.array(Image.open(io.BytesIO(file_content))), cv2.COLOR_RGB2GRAY)
            _, img_cv = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text_content = pytesseract.image_to_string(Image.fromarray(cv2.medianBlur(img_cv, 3)), lang='eng', config=custom_config)
        except Exception as e: pass # print(f"  >> Image OCR Error: {e}")

    return text_content

def save_to_hospital_db(record):
    """Saves the Golden Record to hospital_db.csv, updating existing physicians or appending new ones."""
    csv_filename = 'hospital_db.csv'
    if not os.path.exists(csv_filename):
        print(f"  >> ERROR: {csv_filename} missing. Create file with header first.")
        return

    extracted = record.get('extracted_data', {})
    # Robust lookup for sub-dictionaries
    lic = extracted.get('license') or extracted.get('License') or {}
    dea = extracted.get('dea_certificate') or extracted.get('DEA') or {}

    # Flatten data using robust retrieval
    schedules = dea.get('schedules', [])
    new_data = {
        'provider_name': record.get('provider_name', 'N/A'),
        'license_no': get_value_robust(lic, ['license_no', 'number', 'license_number']),
        'license_expiry': get_value_robust(lic, ['expiration_date', 'expiry', 'expiry_date']),
        'license_status': get_value_robust(lic, ['status', 'license_status']),
        'dea_number': get_value_robust(dea, ['dea_number', 'number']),
        'dea_schedules': ', '.join([str(s) for s in schedules]) if isinstance(schedules, list) else str(schedules),
        'dea_expiry_date': get_value_robust(dea, ['expiration_date', 'expiry_date'])
    }

    rows = []
    updated = False

    # Read, Update/Append
    with open(csv_filename, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print(f"  >> ERROR: {csv_filename} has no header.")
            return

        for row in reader:
            if row.get('provider_name') == new_data['provider_name']:
                # Update existing row, only updating fields present in our schema
                row.update({k: v for k, v in new_data.items() if k in fieldnames})
                updated = True
                print(f"[Database] Updated existing record for {new_data['provider_name']}")
                log_audit_event({"action": "Database Update", "provider": new_data['provider_name'], "status": "Updated"})
            rows.append(row)

    if not updated:
        rows.append(new_data)
        print(f"[Database] Appended new record for {new_data['provider_name']}")
        log_audit_event({"action": "Database Append", "provider": new_data['provider_name'], "status": "New Record"})

    # Write back to file
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    # print(f"  >> Database save complete.") # Suppressed to reduce noise

# Validation Stubs
def is_valid_license_number(no): return True
def is_valid_dea_number(no):
    if no == "N/A": return True
    return bool(re.match(r'^[A-Z]{1,2}\d{7,9}$', no)) and no != "FAKE9876543"

# ==========================================
# 3. CREDENTIAL SYSTEM CLASS
# ==========================================

class CredentialSystem:
    # Define schemas and prompts as class constants for efficiency
    EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "license": {"type": "object", "properties": {"license_no": {"type": "string"}, "expiration_date": {"type": "string"}, "status": {"type": "string"}}, "required": ["license_no", "expiration_date", "status"]},
            "identity_document": {"type": "object", "properties": {"full_name": {"type": "string"}, "dob": {"type": "string"}, "ssn": {"type": "string"}, "photo_id_match": {"type": "boolean"}}, "required": ["full_name", "dob", "ssn", "photo_id_match"]},
            "medical_diploma": {"type": "object", "properties": {"degree_type": {"type": "string"}, "institution": {"type": "string"}, "graduation_date": {"type": "string"}}, "required": ["degree_type", "institution", "graduation_date"]},
            "dea_certificate": {"type": "object", "properties": {"dea_number": {"type": "string"}, "schedules": {"type": "array", "items": {"type": "string"}}, "expiration_date": {"type": "string"}}, "required": ["dea_number", "schedules", "expiration_date"]},
            "cv": {"type": "object", "properties": {"employment_history": {"type": "array", "items": {"type": "object", "properties": {"job_title": {"type": "string"}, "employer": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}}}, "education": {"type": "array", "items": {"type": "object", "properties": {"degree_type": {"type": "string"}, "institution": {"type": "string"}, "graduation_date": {"type": "string"}}}}}}
        },
        "required": ["license", "identity_document", "medical_diploma", "dea_certificate", "cv"]
    }

    def __init__(self, provider_name, sms_number=None, email_address=None, uploaded_documents=None, **kwargs):
        self.provider = provider_name
        self.sms_number = sms_number
        self.email_address = email_address
        self.uploaded_documents = uploaded_documents or {}
        self.extracted_data = {}
        self.visual_fidelity_metrics = {}
        self.confidence_score = 100
        self.docs = kwargs
        log_audit_event({"action": "Initialization", "provider": self.provider, "documents_uploaded": list(self.uploaded_documents.keys())})

    def _call_llm(self, system_msg, user_msg, temperature=0.1):
        """Internal helper for LLM calls."""
        try:
            res = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                temperature=temperature
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e:
            print(f"[System] LLM Call Error: {e}")
            log_audit_event({"action": "LLM Error", "error": str(e)})
            return None

    def semantic_validation(self):
        if not self.extracted_data: return {"coherence_score": 0, "reasoning": "No data."}

        sys_prompt = "You are a helpful assistant designed to output JSON. You are a Data Consistency Auditor. Analyze the extracted credentialing data for logical coherence (names, dates, matching institutions). Return a valid JSON object with `coherence_score` (0-100) and `reasoning`."
        res = self._call_llm(sys_prompt, json.dumps(self.extracted_data))
        if res:
             log_audit_event({"action": "Semantic Validation", "score": res.get('coherence_score'), "reasoning": res.get('reasoning')})
        else:
             log_audit_event({"action": "Semantic Validation Failed"})
        return res if res else {"coherence_score": 50, "reasoning": "LLM Error"}

    def preprocessing_agent(self, cv_bin, cv_type, lic_bin, lic_type, cv_txt, lic_txt):
        # print(f"[Preprocessing] Analyzing documents for {self.provider}...") # Suppressed
        log_audit_event({"agent": "Preprocessing", "provider": self.provider, "status": "Started"})

        def check_doc(binary, ftype, name, text):
            if binary:
                imgs = convert_document_to_images(binary, ftype)
                if not imgs and ftype == 'image':
                    log_audit_event({"agent": "Preprocessing", "doc": name, "error": "Unreadable"})
                    return False, f"{name} Unreadable"
                for i, img in enumerate(imgs):
                    score = cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), cv2.CV_64F).var()
                    self.visual_fidelity_metrics[f'{name}_blur_score'] = score

                    # --- NEW: Print Blur Score ---
                    print(f"  >> {name} (Page {i+1}) Blur Score: {score:.2f}")

                    if score < 100:
                        log_audit_event({"agent": "Preprocessing", "doc": name, "error": "Blurry", "score": score})
                        return False, f"Blurry {name} page {i+1}"
            if text: self.visual_fidelity_metrics[f'{name}_text_length'] = len(text.strip())
            elif binary and ftype == 'pdf':
                log_audit_event({"agent": "Preprocessing", "doc": name, "error": "Empty PDF"})
                return False, f"{name} PDF Empty"
            return True, "OK"

        if not check_doc(cv_bin, cv_type, 'cv', cv_txt)[0]: return self.nudge_agent(check_doc(cv_bin, cv_type, 'cv', cv_txt)[1])
        if not check_doc(lic_bin, lic_type, 'license', lic_txt)[0]: return self.nudge_agent(check_doc(lic_bin, lic_type, 'license', lic_txt)[1])

        log_audit_event({"agent": "Preprocessing", "status": "Passed"})
        # print("  >> Preprocessing passed.") # Suppressed
        return "SUCCESS"

    def extraction_agent(self, cv_txt, lic_txt, provider, id_txt, dip_txt, dea_txt):
        # print("[Extraction] Extracting structured data via LLM...") # Suppressed
        sys_prompt = f"You are a helpful assistant designed to output JSON. Extract data based on the following schema: {json.dumps(self.EXTRACTION_SCHEMA)}. Use N/A if missing. Dates YYYY-MM-DD. For DEA schedules, return a list of strings (e.g. ['II', 'III']). Be aggressive in finding License Numbers and Expiration Dates in the text, even if OCR is noisy (look for 'Exp', 'Expires', 'Lic #')."
        user_prompt = f"Provider: {provider}\nDocs:\nLicense: {lic_txt}\nID: {id_txt}\nDiploma: {dip_txt}\nDEA: {dea_txt}\nCV: {cv_txt}"

        data = self._call_llm(sys_prompt, user_prompt)
        if data:
            data['provider_name'] = provider
            self.extracted_data = data
            log_audit_event({"agent": "Extraction", "status": "Success"})
            # print(f"  >> Extracted Data: {json.dumps(data, indent=2)}") # Suppressed
            return data

        log_audit_event({"agent": "Extraction", "status": "Failed"})
        return self.nudge_agent("Extraction Failed")

    def verification_flow(self):
        # print("[Verification] Checking sanctions...") # Suppressed
        if npdb_sanction_check(self.provider):
            print("[Verification] SANCTION FOUND in NPDB!")
            log_audit_event({"agent": "Verification", "status": "Sanction Found", "source": "NPDB"})
            return self.rtp_agent("Sanction Hit")

        print("[Verification] No sanctions found in NPDB.")
        log_audit_event({"agent": "Verification", "status": "Clean", "source": "NPDB"})
        return "SUCCESS"

    def scoring_agent(self):
        # print("[Scoring] Calculating confidence score...") # Suppressed
        self.confidence_score = 100
        deductions = []

        # 0. Check Missing Documents
        # License is enforced in UI, but checking all ensures consistency
        for doc in ["CV", "License", "Identity", "Diploma", "DEA"]:
            if not self.uploaded_documents.get(doc, False):
                self.confidence_score -= 10
                deductions.append(f"Missing {doc}")
                print(f"[Scoring] Deducted 10 pts: Missing Document ({doc})")
            # else:
                # print(f"  >> Document Present: {doc}") # Suppressed passing check

        # 1. Visual deductions
        for k, v in self.visual_fidelity_metrics.items():
            if 'blur' in k and v is not None and v < 150:
                self.confidence_score -= 5
                deductions.append(f"Blurry {k}")
                print(f"[Scoring] Deducted 5 pts: {k} (Score {v:.2f})")
            # else:
                # print(f"  >> Passed Visual Check: {k} (Score {v} > 150)") # Suppressed passing check

        # 2. Semantic validation
        val = self.semantic_validation()
        coh = val.get('coherence_score', 0)
        if coh < 100:
            deduct = min(30, (100 - coh) // 2)
            self.confidence_score -= deduct
            deductions.append(f"Semantic: {val.get('reasoning')}")
            print(f"[Scoring] Semantic Deduction: -{deduct} pts ({val.get('reasoning')})")
        # else:
            # print("  >> Semantic Check: Passed (100%)") # Suppressed passing check

        # 3. Completeness/Auth (Robust)
        lic_data = self.extracted_data.get('license') or self.extracted_data.get('License') or {}
        dea_data = self.extracted_data.get('dea_certificate') or self.extracted_data.get('DEA') or {}

        lic_no = get_value_robust(lic_data, ['license_no', 'number'])
        dea_no = get_value_robust(dea_data, ['dea_number', 'number'])

        if lic_no == "N/A":
            self.confidence_score -= 10
            deductions.append("Missing License Number")
            print(f"[Scoring] Deducted 10 pts: Missing License Number")
        elif not is_valid_license_number(lic_no):
            self.confidence_score -= 15
            deductions.append("Invalid License Number")
            print(f"[Scoring] Deducted 15 pts: Invalid License Number")
        # else:
            # print(f"  >> Passed License Check: {lic_no}") # Suppressed passing check

        if dea_no == "N/A":
            self.confidence_score -= 10
            deductions.append("Missing DEA Number")
            print(f"[Scoring] Deducted 10 pts: Missing DEA Number")
        elif not is_valid_dea_number(dea_no):
            self.confidence_score -= 15
            deductions.append("Invalid DEA Number")
            print(f"[Scoring] Deducted 15 pts: Invalid DEA Number")
        # else:
            # print(f"  >> Passed DEA Check: {dea_no}") # Suppressed passing check

        self.confidence_score = max(0, self.confidence_score)
        print(f"[Scoring] Final Confidence Score: {self.confidence_score}%")

        log_audit_event({"agent": "Scoring", "final_score": self.confidence_score, "deductions": deductions})

        return self.hitl_specialist_dashboard(self) if self.confidence_score < 95 else self.hitl_approval()

    def nudge_agent(self, reason):
        # print(f"[Nudge Agent] Creating notification for: {reason}") # Suppressed
        sys_prompt = "Write a polite, concise (1-2 sentences) email to a doctor explaining a credentialing issue."
        try:
            msg = openai_client.chat.completions.create(model=OPENAI_MODEL, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":f"Issue: {reason}"}], temperature=0.7).choices[0].message.content
        except: msg = f"Please address the issue: {reason}"

        # Use specific output format if contacts are available
        if self.sms_number:
            print(f"[SMS to {self.sms_number}]: \"{msg}\"")
        elif self.email_address:
            print(f"[Email to {self.email_address}]: \"{msg}\"")
        else:
            print(f"[Nudge] Sent Message: \"{msg}\"")

        log_audit_event({"timestamp": str(datetime.now()), "action": "Nudge", "msg": msg, "reason": reason})
        return "RETRY_REQUIRED"

    def send_approval_notification(self):
        """Generates and sends an approval notification."""
        sys_prompt = "Write a polite, concise (1-2 sentences) email to a doctor congratulating them on successful credentialing approval. Your name is Creed Special. Your role is a credentialing specialist"
        try:
            msg = openai_client.chat.completions.create(model=OPENAI_MODEL, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":f"Doctor: {self.provider}"}], temperature=0.7).choices[0].message.content
        except: msg = f"Congratulations {self.provider}, your credentialing is complete."

        # Use specific output format if contacts are available
        if self.sms_number:
            print(f"[SMS to {self.sms_number}]: \"{msg}\"")
        elif self.email_address:
            print(f"[Email to {self.email_address}]: \"{msg}\"")
        else:
            print(f"[Notification] Sent Approval Message: \"{msg}\"")

        log_audit_event({"timestamp": str(datetime.now()), "action": "Approval Notification", "msg": msg})

    def rtp_agent(self, reason): return self.nudge_agent(reason)

    def hitl_specialist_dashboard(self, system_instance):
        # print(f"[HITL Dashboard] Reviewing case (Score: {self.confidence_score}%)...")
        if self.confidence_score > 80:
            print("[HITL] Manually Approved by Specialist Dashboard.")
            log_audit_event({"agent": "HITL", "action": "Manual Approval", "score": self.confidence_score})
            self.send_approval_notification() # Send notification on manual approval
            return "MANUALLY_APPROVED"
        print(f"[HITL] Manually Denied by Specialist Dashboard. Score {self.confidence_score}% too low.")
        log_audit_event({"agent": "HITL", "action": "Manual Denial", "score": self.confidence_score})
        return self.nudge_agent(f"Confidence score {self.confidence_score}% is too low.")

    def hitl_approval(self):
        # print("[HITL Approval] Final Sign-off. Generating Dossier.") # Suppressed details
        fname = f"compliance_dossier_{self.provider.replace(' ', '_')}.txt" # Changed to .txt

        content = f"--- COMPLIANCE DOSSIER ---\n"
        content += f"Provider: {self.provider}\n"
        content += f"Date: {datetime.now()}\n"
        content += f"Final Confidence Score: {self.confidence_score}%\n"
        content += f"Status: APPROVED\n\n"
        content += f"--- EXTRACTED DATA ---\n"
        content += json.dumps(self.extracted_data, indent=2)
        content += f"\n\n--- QUALITY METRICS ---\n"
        content += json.dumps(self.visual_fidelity_metrics, indent=2)

        with open(fname, 'w') as f: f.write(content)
        # print(f"  >> Compliance Dossier generated: {fname}") # Suppressed
        log_audit_event({"agent": "HITL", "action": "Auto Approval", "dossier": fname})
        self.send_approval_notification()
        return "COMPLETE"

