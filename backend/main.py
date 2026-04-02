# -*- coding: utf-8 -*-
"""FastAPI backend for Physician Credentialing System."""

import os
import sys
import json
import uuid
import io
from datetime import datetime
from typing import Optional

# Insert parent directory so we can import physican_core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from physican_core import (
    CredentialSystem,
    extract_text_from_document,
    save_to_hospital_db,
    log_audit_event,
)

# ==========================================
# APP INITIALIZATION
# ==========================================

app = FastAPI(title="Physician Credentialing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to submissions.json in project root (parent of backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBMISSIONS_FILE = os.path.join(PROJECT_ROOT, "submissions.json")
AUDIT_LOG_FILE = os.path.join(PROJECT_ROOT, "immutable_audit_log.jsonl")


# ==========================================
# HELPER FUNCTIONS (ported from app_dash.py)
# ==========================================

def load_submissions():
    try:
        with open(SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_submissions(records):
    with open(SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)


def upsert_submission(record):
    records = load_submissions()
    for i, r in enumerate(records):
        if r.get("id") == record.get("id"):
            records[i] = record
            save_submissions(records)
            return
    records.append(record)
    save_submissions(records)


def get_scoring_event_after(after_ts: str) -> dict:
    """Return the first Scoring audit event logged at or after after_ts."""
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if (entry.get("agent") == "Scoring"
                            and "deductions" in entry
                            and entry.get("timestamp", "") >= after_ts):
                        return entry
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return {}


def build_deductions(raw_deductions: list) -> list:
    """Convert raw deduction strings from the audit log to [{reason, points}] dicts."""
    result = []
    for reason in raw_deductions:
        r_lower = reason.lower()
        if "invalid dea" in r_lower:
            pts = 15
        elif "invalid license" in r_lower:
            pts = 15
        elif "blurry" in r_lower:
            pts = 5
        else:
            pts = 10  # Missing docs, semantic, and anything else
        result.append({"reason": reason, "points": pts})
    return result


def verify_deductions(deductions: list, extracted_data: dict, uploaded_status: dict) -> tuple[list, int]:
    """Remove deductions that are contradicted by the actual extracted data.
    Returns (corrected_deductions, points_restored)."""
    dea_data = (extracted_data.get('dea_certificate')
                or extracted_data.get('DEA')
                or extracted_data.get('dea')
                or {})
    dea_no = str(dea_data.get('dea_number') or dea_data.get('number') or 'N/A').strip()

    lic_data = extracted_data.get('license') or extracted_data.get('License') or {}
    lic_no = str(lic_data.get('license_no') or lic_data.get('number') or 'N/A').strip()

    corrected = []
    restored = 0
    for d in deductions:
        r = d['reason'].lower()
        # "Missing DEA Number" — remove if DEA number is actually present
        if 'missing dea number' in r and dea_no and dea_no.upper() != 'N/A':
            restored += d['points']
            continue
        # "Missing DEA" (document) — remove if DEA file was uploaded
        if r == 'missing dea' and uploaded_status.get('DEA', False):
            restored += d['points']
            continue
        # "Missing License Number" — remove if license number is actually present
        if 'missing license number' in r and lic_no and lic_no.upper() != 'N/A':
            restored += d['points']
            continue
        corrected.append(d)
    return corrected, restored


def make_fake_file(content_bytes: bytes, filename: str):
    """Build a fake file object compatible with physican_core's extract_text_from_document."""
    buf = io.BytesIO(content_bytes)
    buf.name = filename

    class FakeFile:
        def __init__(self, data: bytes, name: str):
            self._data = data
            self.name = name

        def getvalue(self):
            return self._data

    return FakeFile(content_bytes, filename)


def get_file_type(filename: str) -> str:
    return "pdf" if filename.lower().endswith(".pdf") else "image"


# ==========================================
# ENDPOINTS
# ==========================================

@app.post("/api/submit")
async def submit_credentials(
    provider_name: str = Form(...),
    sms_number: Optional[str] = Form(None),
    email_address: Optional[str] = Form(None),
    cv: Optional[UploadFile] = File(None),
    license: UploadFile = File(...),
    identity: Optional[UploadFile] = File(None),
    diploma: Optional[UploadFile] = File(None),
    dea: Optional[UploadFile] = File(None),
):
    """Run full credentialing pipeline and persist result."""

    if not provider_name or not provider_name.strip():
        raise HTTPException(status_code=400, detail="provider_name is required")

    # Read file bytes
    license_bytes = await license.read()

    cv_bytes = await cv.read() if cv else None
    identity_bytes = await identity.read() if identity else None
    diploma_bytes = await diploma.read() if diploma else None
    dea_bytes = await dea.read() if dea else None

    # Build fake file objects and extract text
    def extract(raw_bytes, filename):
        if not raw_bytes or not filename:
            return None, None, ""
        fobj = make_fake_file(raw_bytes, filename)
        ftype = get_file_type(filename)
        text = extract_text_from_document(fobj, ftype)
        return raw_bytes, ftype, text

    cv_bin, cv_type, cv_txt = extract(cv_bytes, cv.filename if cv else None)
    lic_bin, lic_type, lic_txt = extract(license_bytes, license.filename)
    id_bin, _id_type, id_txt = extract(identity_bytes, identity.filename if identity else None)
    dip_bin, _dip_type, dip_txt = extract(diploma_bytes, diploma.filename if diploma else None)
    dea_bin, _dea_type, dea_txt = extract(dea_bytes, dea.filename if dea else None)

    uploaded_status = {
        "CV": cv is not None,
        "License": True,
        "Identity": identity is not None,
        "Diploma": diploma is not None,
        "DEA": dea is not None,
    }

    def save_failed(status: str, reason: str):
        record = {
            "id": str(uuid.uuid4()),
            "provider_name": provider_name,
            "timestamp": datetime.now().isoformat(),
            "sms_number": sms_number,
            "email_address": email_address,
            "confidence_score": 0,
            "deductions": [{"reason": str(reason), "points": 0}],
            "extracted_data": {},
            "visual_fidelity_metrics": {},
            "status": status,
            "notification_channel": "SMS" if sms_number else ("Email" if email_address else "None"),
            "notification_message": str(reason),
            "specialist_action": None,
            "specialist_timestamp": None,
        }
        upsert_submission(record)
        return record

    try:
        pipeline_start_ts = datetime.now().isoformat()

        system = CredentialSystem(
            provider_name,
            sms_number,
            email_address,
            uploaded_documents=uploaded_status,
        )

        # Step 1: Preprocessing
        pp_status = system.preprocessing_agent(
            cv_bin, cv_type,
            lic_bin, lic_type,
            cv_txt, lic_txt,
        )
        if pp_status != "SUCCESS":
            record = save_failed("FAILED", pp_status)
            return record

        # Step 2: Extraction
        extracted = system.extraction_agent(
            cv_txt, lic_txt,
            provider_name,
            id_txt, dip_txt, dea_txt,
        )
        if not isinstance(extracted, dict):
            record = save_failed("FAILED", extracted)
            return record

        # Step 3: Verification
        v_status = system.verification_flow()
        if v_status != "SUCCESS":
            record = save_failed("RETRY_REQUIRED", v_status)
            return record

        # Step 4: Scoring
        system.scoring_agent()
        score = system.confidence_score

        # Determine persisted status from score band
        if score >= 95:
            persist_status = "AUTO_APPROVED"
        elif score >= 80:
            persist_status = "PENDING_SPECIALIST_REVIEW"
        else:
            persist_status = "RETRY_REQUIRED"

        # Capture deductions from this run's audit log entry
        scoring_event = get_scoring_event_after(pipeline_start_ts)
        raw_deductions = scoring_event.get("deductions", [])
        deductions = build_deductions(raw_deductions)

        # Remove any deductions contradicted by the actual extracted data
        deductions, restored = verify_deductions(deductions, system.extracted_data, uploaded_status)
        score = min(100, score + restored)

        # Re-derive status from corrected score
        if score >= 95:
            persist_status = "AUTO_APPROVED"
        elif score >= 80:
            persist_status = "PENDING_SPECIALIST_REVIEW"
        else:
            persist_status = "RETRY_REQUIRED"

        notif_channel = "SMS" if sms_number else ("Email" if email_address else "None")
        notif_contact = sms_number or email_address or ""

        submission_id = str(uuid.uuid4())
        record = {
            "id": submission_id,
            "provider_name": provider_name,
            "timestamp": datetime.now().isoformat(),
            "sms_number": sms_number,
            "email_address": email_address,
            "confidence_score": score,
            "deductions": deductions,
            "extracted_data": system.extracted_data,
            "visual_fidelity_metrics": system.visual_fidelity_metrics,
            "status": persist_status,
            "notification_channel": notif_channel,
            "notification_message": notif_contact,
            "specialist_action": None,
            "specialist_timestamp": None,
        }
        upsert_submission(record)

        if persist_status == "AUTO_APPROVED":
            try:
                save_to_hospital_db({
                    "provider_name": provider_name,
                    "extracted_data": system.extracted_data,
                })
            except Exception:
                pass

        return record

    except Exception as e:
        record = save_failed("FAILED", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/submissions")
def get_submissions():
    """Return all submissions."""
    return load_submissions()


@app.post("/api/submissions/{submission_id}/approve")
def approve_submission(submission_id: str):
    """Mark submission as MANUALLY_APPROVED and save to hospital DB."""
    submissions = load_submissions()
    for record in submissions:
        if record.get("id") == submission_id:
            record["status"] = "MANUALLY_APPROVED"
            record["specialist_action"] = "approved"
            record["specialist_timestamp"] = datetime.now().isoformat()
            save_submissions(submissions)
            try:
                save_to_hospital_db({
                    "provider_name": record["provider_name"],
                    "extracted_data": record.get("extracted_data", {}),
                })
            except Exception:
                pass
            log_audit_event({
                "action": "Specialist Approval",
                "provider": record["provider_name"],
                "submission_id": submission_id,
            })
            return record
    raise HTTPException(status_code=404, detail="Submission not found")


@app.delete("/api/submissions/{submission_id}")
def delete_submission(submission_id: str):
    """Permanently delete a submission record."""
    submissions = load_submissions()
    updated = [r for r in submissions if r.get("id") != submission_id]
    if len(updated) == len(submissions):
        raise HTTPException(status_code=404, detail="Submission not found")
    save_submissions(updated)
    log_audit_event({"action": "Specialist Deletion", "submission_id": submission_id})
    return {"deleted": submission_id}


@app.post("/api/submissions/{submission_id}/reject")
def reject_submission(submission_id: str):
    """Mark submission as REJECTED."""
    submissions = load_submissions()
    for record in submissions:
        if record.get("id") == submission_id:
            record["status"] = "REJECTED"
            record["specialist_action"] = "rejected"
            record["specialist_timestamp"] = datetime.now().isoformat()
            save_submissions(submissions)
            log_audit_event({
                "action": "Specialist Rejection",
                "provider": record["provider_name"],
                "submission_id": submission_id,
            })
            return record
    raise HTTPException(status_code=404, detail="Submission not found")


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
