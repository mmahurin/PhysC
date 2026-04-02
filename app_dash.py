# -*- coding: utf-8 -*-
"""Physician Credentialing System with AI and OCR - Dash Version"""

import os
import json
import uuid
import base64
import io
from datetime import datetime

import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc

import sys
sys.path.insert(0, os.path.dirname(__file__))

from physican_core import (
    CredentialSystem,
    extract_text_from_document,
    load_spacy_model,
    save_to_hospital_db,
    log_audit_event,
)

# ==========================================
# APP INITIALIZATION
# ==========================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Physician Credentialing System"

SUBMISSIONS_FILE = os.path.join(os.path.dirname(__file__), "submissions.json")
AUDIT_LOG_FILE = os.path.join(os.path.dirname(__file__), "immutable_audit_log.jsonl")

DEDUCTION_POINTS = {
    "Missing": 10,
    "Invalid DEA": 15,
    "Invalid License": 15,
    "Blurry": 5,
    "Semantic": None,  # variable — computed from score difference
}

UPLOAD_STYLE = {
    "width": "100%",
    "height": "70px",
    "lineHeight": "70px",
    "borderWidth": "2px",
    "borderStyle": "dashed",
    "borderRadius": "8px",
    "textAlign": "center",
    "marginBottom": "8px",
    "cursor": "pointer",
    "backgroundColor": "#f8f9fa",
    "color": "#6c757d",
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_upload_content(contents, filename):
    if not contents:
        return None, None, ""
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    file_type = "pdf" if filename.lower().endswith(".pdf") else "image"
    text = extract_text_from_document(
        type("obj", (object,), {
            "getvalue": lambda self: decoded,
            "name": filename,
        })(),
        file_type,
    )
    return content_string, file_type, text


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


def get_latest_scoring_event():
    """Read the audit log and return the most recent Scoring entry."""
    entries = []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    except FileNotFoundError:
        pass
    for entry in reversed(entries):
        if entry.get("agent") == "Scoring" and "deductions" in entry:
            return entry
    return {}


def build_deductions(raw_deductions, start_score, final_score):
    """Convert raw deduction strings to [{reason, points}] dicts."""
    result = []
    running = start_score
    for reason in raw_deductions:
        pts = 10  # default
        r_lower = reason.lower()
        if "invalid dea" in r_lower:
            pts = 15
        elif "invalid license" in r_lower:
            pts = 15
        elif "missing" in r_lower:
            pts = 10
        elif "blurry" in r_lower:
            pts = 5
        elif "semantic" in r_lower:
            # compute from remainder
            pts = running - final_score - sum(d["points"] for d in result)
            pts = max(0, pts)
        running -= pts
        result.append({"reason": reason, "points": pts})
    return result


def score_color(score):
    if score >= 95:
        return "success"
    if score >= 80:
        return "warning"
    return "danger"


def status_badge(status):
    colors = {
        "AUTO_APPROVED": "success",
        "MANUALLY_APPROVED": "success",
        "PENDING_SPECIALIST_REVIEW": "warning",
        "RETRY_REQUIRED": "danger",
        "REJECTED": "secondary",
        "FAILED": "danger",
    }
    return dbc.Badge(status.replace("_", " "), color=colors.get(status, "secondary"), pill=True)


# ==========================================
# LAYOUT BUILDERS
# ==========================================

def upload_slot(label, upload_id, filename_id, required=False):
    return dbc.Col([
        dbc.Label([label, dbc.Badge(" Required", color="danger", className="ms-2") if required else ""]),
        dcc.Upload(
            id=upload_id,
            children=html.Div([
                html.I(className="bi bi-cloud-upload me-2"),
                "Drag & drop or ",
                html.A("browse"),
            ]),
            style=UPLOAD_STYLE,
            accept=".pdf,.jpg,.png,.jpeg",
        ),
        html.Div(id=filename_id, className="mb-2"),
    ], md=6)


def render_submission_page():
    return dbc.Container([
        # Provider Info
        dbc.Card([
            dbc.CardHeader(html.H5("Provider Information", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label(["Provider Name ", dbc.Badge("Required", color="danger")]),
                        dbc.Input(id="provider-name", type="text", placeholder="Full name"),
                    ], md=12, className="mb-3"),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("SMS Number (optional)"),
                        dbc.Input(id="sms-number", type="tel", placeholder="+1 555 000 0000"),
                    ], md=6, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Email Address (optional)"),
                        dbc.Input(id="email-address", type="email", placeholder="doctor@hospital.com"),
                    ], md=6, className="mb-3"),
                ]),
            ]),
        ], className="mb-4 shadow-sm"),

        # Document Uploads
        dbc.Card([
            dbc.CardHeader(html.H5("Upload Credentialing Documents", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    upload_slot("CV", "upload-cv", "cv-filename"),
                    upload_slot("Medical License", "upload-license", "license-filename", required=True),
                ]),
                dbc.Row([
                    upload_slot("Identity Document", "upload-identity", "identity-filename"),
                    upload_slot("Diploma", "upload-diploma", "diploma-filename"),
                ]),
                dbc.Row([
                    upload_slot("DEA Certificate", "upload-dea", "dea-filename"),
                ]),
            ]),
        ], className="mb-4 shadow-sm"),

        # Submit
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    type="circle",
                    children=[
                        dbc.Button(
                            [html.I(className="bi bi-send me-2"), "Submit Credentials"],
                            id="submit-button",
                            color="primary",
                            size="lg",
                            className="w-100",
                        ),
                        html.Div(id="results-container", className="mt-4"),
                    ],
                ),
            ], md=12),
        ]),
    ], fluid=True, className="py-4")


def render_dashboard_page():
    submissions = load_submissions()
    total = len(submissions)
    approved = sum(1 for s in submissions if s.get("status") in ("AUTO_APPROVED", "MANUALLY_APPROVED"))
    pending = sum(1 for s in submissions if s.get("status") == "PENDING_SPECIALIST_REVIEW")
    retry = sum(1 for s in submissions if s.get("status") in ("RETRY_REQUIRED", "FAILED"))

    def stat_card(label, value, color):
        return dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H2(str(value), className="card-title mb-0"),
                    html.P(label, className="text-muted mb-0 small"),
                ], className="text-center"),
                className="shadow-sm",
                color=color,
                outline=True,
            ),
            md=3,
            className="mb-3",
        )

    table_data = [
        {
            "id": s.get("id", ""),
            "Provider Name": s.get("provider_name", ""),
            "Date Submitted": s.get("timestamp", "")[:19].replace("T", " "),
            "Score": f"{s.get('confidence_score', '?')}%",
            "Status": s.get("status", "").replace("_", " "),
        }
        for s in sorted(submissions, key=lambda x: x.get("timestamp", ""), reverse=True)
    ]

    return dbc.Container([
        # Stats
        dbc.Row([
            stat_card("Total Submissions", total, "primary"),
            stat_card("Approved", approved, "success"),
            stat_card("Pending Review", pending, "warning"),
            stat_card("Retry / Failed", retry, "danger"),
        ], className="mb-4"),

        # Table
        dbc.Card([
            dbc.CardHeader(dbc.Row([
                dbc.Col(html.H5("Submissions", className="mb-0"), width="auto"),
                dbc.Col(
                    dbc.Button(
                        [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh"],
                        id="refresh-dashboard",
                        color="secondary",
                        size="sm",
                    ),
                    className="ms-auto",
                    width="auto",
                ),
            ], align="center")),
            dbc.CardBody([
                dash_table.DataTable(
                    id="submissions-table",
                    columns=[
                        {"name": "Provider Name", "id": "Provider Name"},
                        {"name": "Date Submitted", "id": "Date Submitted"},
                        {"name": "Score", "id": "Score"},
                        {"name": "Status", "id": "Status"},
                    ],
                    data=table_data,
                    row_selectable="single",
                    selected_rows=[],
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                    style_cell={"padding": "10px", "fontFamily": "inherit"},
                    style_data_conditional=[
                        {"if": {"filter_query": '{Status} contains "APPROVED"'}, "backgroundColor": "#d1e7dd"},
                        {"if": {"filter_query": '{Status} = "PENDING SPECIALIST REVIEW"'}, "backgroundColor": "#fff3cd"},
                        {"if": {"filter_query": '{Status} contains "RETRY" || {Status} = "FAILED" || {Status} = "REJECTED"'}, "backgroundColor": "#f8d7da"},
                    ],
                    style_as_list_view=True,
                ),
            ]),
        ], className="mb-4 shadow-sm"),

        # Sign-off result (persistent, outside detail panel)
        html.Div(id="signoff-result", className="mb-3"),

        # Detail panel
        html.Div(id="detail-panel", style={"display": "none"}),

    ], fluid=True, className="py-4")


# ==========================================
# APP LAYOUT
# ==========================================

app.layout = html.Div([
    # Navbar + Tabs
    dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand(
                [html.I(className="bi bi-hospital me-2"), "Physician Credentialing System"],
                className="fw-bold",
            ),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("Physician Submission", id="tab-submission-link", href="#", active=True, n_clicks=0)),
                dbc.NavItem(dbc.NavLink("Specialist Dashboard", id="tab-dashboard-link", href="#", n_clicks=0)),
            ], navbar=True, className="ms-auto"),
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-0 shadow",
    ),

    # Page content
    html.Div(id="page-content"),

    # Global stores
    dcc.Store(id="cv-data"),
    dcc.Store(id="license-data"),
    dcc.Store(id="identity-data"),
    dcc.Store(id="diploma-data"),
    dcc.Store(id="dea-data"),
    dcc.Store(id="active-tab", data="submission"),
    dcc.Store(id="selected-submission-id"),
    dcc.Store(id="dashboard-trigger", data=0),
])

# ==========================================
# CALLBACKS
# ==========================================

# CB-1: Tab navigation
@callback(
    Output("page-content", "children"),
    Output("tab-submission-link", "active"),
    Output("tab-dashboard-link", "active"),
    Output("dashboard-trigger", "data"),
    Input("tab-submission-link", "n_clicks"),
    Input("tab-dashboard-link", "n_clicks"),
    State("dashboard-trigger", "data"),
    prevent_initial_call=False,
)
def switch_tab(sub_clicks, dash_clicks, trigger):
    from dash import ctx
    triggered = ctx.triggered_id
    if triggered == "tab-dashboard-link":
        return render_dashboard_page(), False, True, (trigger or 0) + 1
    return render_submission_page(), True, False, trigger or 0


# CB-2: Upload stores
@callback(
    Output("cv-data", "data"), Output("cv-filename", "children"),
    Input("upload-cv", "contents"), State("upload-cv", "filename"),
)
def store_cv(contents, filename):
    if not contents:
        return None, ""
    b64, ftype, text = parse_upload_content(contents, filename)
    return {"binary": b64, "type": ftype, "text": text, "filename": filename}, dbc.Badge(f"✓ {filename}", color="success", pill=True)


@callback(
    Output("license-data", "data"), Output("license-filename", "children"),
    Input("upload-license", "contents"), State("upload-license", "filename"),
)
def store_license(contents, filename):
    if not contents:
        return None, ""
    b64, ftype, text = parse_upload_content(contents, filename)
    return {"binary": b64, "type": ftype, "text": text, "filename": filename}, dbc.Badge(f"✓ {filename}", color="success", pill=True)


@callback(
    Output("identity-data", "data"), Output("identity-filename", "children"),
    Input("upload-identity", "contents"), State("upload-identity", "filename"),
)
def store_identity(contents, filename):
    if not contents:
        return None, ""
    b64, ftype, text = parse_upload_content(contents, filename)
    return {"binary": b64, "type": ftype, "text": text, "filename": filename}, dbc.Badge(f"✓ {filename}", color="success", pill=True)


@callback(
    Output("diploma-data", "data"), Output("diploma-filename", "children"),
    Input("upload-diploma", "contents"), State("upload-diploma", "filename"),
)
def store_diploma(contents, filename):
    if not contents:
        return None, ""
    b64, ftype, text = parse_upload_content(contents, filename)
    return {"binary": b64, "type": ftype, "text": text, "filename": filename}, dbc.Badge(f"✓ {filename}", color="success", pill=True)


@callback(
    Output("dea-data", "data"), Output("dea-filename", "children"),
    Input("upload-dea", "contents"), State("upload-dea", "filename"),
)
def store_dea(contents, filename):
    if not contents:
        return None, ""
    b64, ftype, text = parse_upload_content(contents, filename)
    return {"binary": b64, "type": ftype, "text": text, "filename": filename}, dbc.Badge(f"✓ {filename}", color="success", pill=True)


# CB-3: Main processing
@callback(
    Output("results-container", "children"),
    Input("submit-button", "n_clicks"),
    State("provider-name", "value"),
    State("sms-number", "value"),
    State("email-address", "value"),
    State("cv-data", "data"),
    State("license-data", "data"),
    State("identity-data", "data"),
    State("diploma-data", "data"),
    State("dea-data", "data"),
    prevent_initial_call=True,
)
def run_submission(n_clicks, provider_name, sms_number, email_address,
                   cv_data, license_data, identity_data, diploma_data, dea_data):
    if not provider_name:
        return dbc.Alert("Provider name is required.", color="danger")
    if not license_data:
        return dbc.Alert("License document is required.", color="danger")

    files = {
        "CV": cv_data or {"binary": None, "type": None, "text": ""},
        "License": license_data,
        "Identity": identity_data or {"binary": None, "type": None, "text": ""},
        "Diploma": diploma_data or {"binary": None, "type": None, "text": ""},
        "DEA": dea_data or {"binary": None, "type": None, "text": ""},
    }
    uploaded_status = {name: bool(data and data.get("binary")) for name, data in files.items()}

    def to_bytes(b64):
        return base64.b64decode(b64) if b64 else None

    try:
        system = CredentialSystem(provider_name, sms_number, email_address, uploaded_documents=uploaded_status)

        status = system.preprocessing_agent(
            to_bytes(files["CV"]["binary"]), files["CV"]["type"],
            to_bytes(files["License"]["binary"]), files["License"]["type"],
            files["CV"]["text"], files["License"]["text"],
        )
        if status != "SUCCESS":
            _save_failed_submission(provider_name, sms_number, email_address, "FAILED", status)
            return _result_alert("danger", "Preprocessing Failed", status, None, sms_number, email_address)

        extracted = system.extraction_agent(
            files["CV"]["text"], files["License"]["text"],
            provider_name, files["Identity"]["text"],
            files["Diploma"]["text"], files["DEA"]["text"],
        )
        if not isinstance(extracted, dict):
            _save_failed_submission(provider_name, sms_number, email_address, "FAILED", extracted)
            return _result_alert("danger", "Extraction Failed", extracted, None, sms_number, email_address)

        v_status = system.verification_flow()
        if v_status != "SUCCESS":
            _save_failed_submission(provider_name, sms_number, email_address, "RETRY_REQUIRED", v_status)
            return _result_alert("warning", "Verification Issue", v_status, None, sms_number, email_address)

        final_status = system.scoring_agent()
        score = system.confidence_score

        # Determine persisted status from score band
        if score >= 95:
            persist_status = "AUTO_APPROVED"
        elif score >= 80:
            persist_status = "PENDING_SPECIALIST_REVIEW"
        else:
            persist_status = "RETRY_REQUIRED"

        # Capture deductions from audit log
        scoring_event = get_latest_scoring_event()
        raw_deductions = scoring_event.get("deductions", [])
        deductions = build_deductions(raw_deductions, 100, score)

        # Notification info
        notif_channel = "SMS" if sms_number else ("Email" if email_address else "None")
        notif_contact = sms_number or email_address or "—"

        # Persist submission
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
            "notification_message": "",
            "specialist_action": None,
            "specialist_timestamp": None,
        }
        upsert_submission(record)

        # Save to hospital DB if approved
        if persist_status in ("AUTO_APPROVED",):
            try:
                save_to_hospital_db({"provider_name": provider_name, "extracted_data": system.extracted_data})
            except Exception:
                pass

        # Build result UI
        if persist_status == "AUTO_APPROVED":
            alert_color, badge_text, badge_color, msg = "success", "AUTO-APPROVED", "success", "Your credentials have been automatically approved."
        elif persist_status == "PENDING_SPECIALIST_REVIEW":
            alert_color, badge_text, badge_color, msg = "warning", "PENDING SPECIALIST REVIEW", "warning", "Your submission is under specialist review. You will be notified of the outcome."
        else:
            alert_color, badge_text, badge_color, msg = "danger", "RESUBMISSION REQUIRED", "danger", "Issues were found with your submission. Please review the notification sent to you."

        return [
            # Notification card
            dbc.Card([
                dbc.CardHeader([html.I(className="bi bi-bell me-2"), "Notification Sent"]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([html.Small("Channel", className="text-muted d-block"), html.Strong(notif_channel)], md=4),
                        dbc.Col([html.Small("Contact", className="text-muted d-block"), html.Strong(notif_contact)], md=8),
                    ]),
                ]),
            ], color="info", outline=True, className="mb-3"),

            # Result alert
            dbc.Alert([
                dbc.Row([
                    dbc.Col(html.H5(msg, className="mb-0"), width=True),
                    dbc.Col(dbc.Badge(badge_text, color=badge_color, pill=True, className="fs-6"), width="auto"),
                ], align="center", className="mb-2"),
                html.Hr(),
                dbc.Row([
                    dbc.Col([html.Small("Confidence Score", className="d-block text-muted"), html.Strong(f"{score}%")], md=3),
                    dbc.Col([html.Small("Status", className="d-block text-muted"), html.Strong(persist_status.replace("_", " "))], md=5),
                ]),
            ], color=alert_color),
        ]

    except Exception as e:
        return dbc.Alert(f"Unexpected error: {str(e)}", color="danger")


def _save_failed_submission(provider_name, sms, email, status, reason):
    record = {
        "id": str(uuid.uuid4()),
        "provider_name": provider_name,
        "timestamp": datetime.now().isoformat(),
        "sms_number": sms,
        "email_address": email,
        "confidence_score": 0,
        "deductions": [{"reason": str(reason), "points": 0}],
        "extracted_data": {},
        "visual_fidelity_metrics": {},
        "status": status,
        "notification_channel": "SMS" if sms else ("Email" if email else "None"),
        "notification_message": str(reason),
        "specialist_action": None,
        "specialist_timestamp": None,
    }
    upsert_submission(record)


def _result_alert(color, title, detail, score, sms, email):
    notif_channel = "SMS" if sms else ("Email" if email else "None")
    return [
        dbc.Card([
            dbc.CardHeader([html.I(className="bi bi-bell me-2"), "Notification Sent"]),
            dbc.CardBody(dbc.Row([
                dbc.Col([html.Small("Channel", className="text-muted d-block"), html.Strong(notif_channel)], md=4),
                dbc.Col([html.Small("Contact", className="text-muted d-block"), html.Strong(sms or email or "—")], md=8),
            ])),
        ], color="info", outline=True, className="mb-3"),
        dbc.Alert(f"{title}: {detail}", color=color),
    ]


# CB-4: Dashboard table loader
@callback(
    Output("submissions-table", "data"),
    Input("dashboard-trigger", "data"),
    prevent_initial_call=True,
)
def reload_table(trigger):
    submissions = load_submissions()
    return [
        {
            "id": s.get("id", ""),
            "Provider Name": s.get("provider_name", ""),
            "Date Submitted": s.get("timestamp", "")[:19].replace("T", " "),
            "Score": f"{s.get('confidence_score', '?')}%",
            "Status": s.get("status", "").replace("_", " "),
        }
        for s in sorted(submissions, key=lambda x: x.get("timestamp", ""), reverse=True)
    ]


# CB-5: Detail panel on row selection
@callback(
    Output("detail-panel", "children"),
    Output("detail-panel", "style"),
    Output("selected-submission-id", "data"),
    Input("submissions-table", "selected_rows"),
    State("submissions-table", "data"),
    prevent_initial_call=True,
)
def show_detail(selected_rows, table_data):
    if not selected_rows or not table_data:
        return None, {"display": "none"}, None

    row = table_data[selected_rows[0]]
    submission_id = row.get("id")

    # Load full record
    submissions = load_submissions()
    record = next((s for s in submissions if s.get("id") == submission_id), None)
    if not record:
        return dbc.Alert("Record not found.", color="warning"), {"display": "block"}, submission_id

    score = record.get("confidence_score", 0)
    deductions = record.get("deductions", [])
    extracted = record.get("extracted_data", {})
    status = record.get("status", "")

    # Extracted data accordion
    doc_labels = {
        "license": "Medical License",
        "identity_document": "Identity Document",
        "medical_diploma": "Diploma",
        "dea_certificate": "DEA Certificate",
        "cv": "Curriculum Vitae",
    }
    accordion_items = []
    for key, label in doc_labels.items():
        doc_data = extracted.get(key, {})
        if not doc_data:
            continue
        if isinstance(doc_data, dict):
            rows = [html.Tr([html.Td(html.Strong(k.replace("_", " ").title())), html.Td(str(v))]) for k, v in doc_data.items()]
            table = dbc.Table(html.Tbody(rows), striped=True, hover=True, size="sm", className="mb-0")
        elif isinstance(doc_data, list):
            table = html.Ul([html.Li(str(item)) for item in doc_data])
        else:
            table = html.P(str(doc_data))
        accordion_items.append(dbc.AccordionItem(table, title=label))

    extracted_panel = dbc.Card([
        dbc.CardHeader(html.Strong("Extracted Data")),
        dbc.CardBody(
            dbc.Accordion(accordion_items, start_collapsed=True) if accordion_items
            else html.P("No extracted data available.", className="text-muted")
        ),
    ], className="h-100")

    # Scoring breakdown
    deduction_items = [
        dbc.ListGroupItem(
            dbc.Row([
                dbc.Col("Starting Score"),
                dbc.Col(dbc.Badge("100", color="secondary"), className="text-end"),
            ]),
            className="text-muted",
        )
    ]
    for d in deductions:
        deduction_items.append(
            dbc.ListGroupItem(
                dbc.Row([
                    dbc.Col(d["reason"]),
                    dbc.Col(dbc.Badge(f"-{d['points']}", color="danger"), className="text-end"),
                ]),
                color="danger",
            )
        )
    deduction_items.append(
        dbc.ListGroupItem(
            dbc.Row([
                dbc.Col(html.Strong("Final Score")),
                dbc.Col(dbc.Badge(f"{score}%", color=score_color(score)), className="text-end"),
            ]),
        )
    )

    scoring_panel = dbc.Card([
        dbc.CardHeader(html.Strong("Scoring Breakdown")),
        dbc.CardBody([
            dbc.Progress(
                value=score,
                label=f"{score}%",
                color=score_color(score),
                style={"height": "28px"},
                className="mb-3",
            ),
            dbc.ListGroup(deduction_items, flush=True),
        ]),
    ], className="h-100")

    # Approve/Reject panel
    signoff_panel = None
    if status == "PENDING_SPECIALIST_REVIEW":
        signoff_panel = dbc.Card([
            dbc.CardHeader([html.I(className="bi bi-pen me-2"), html.Strong("Specialist Sign-off Required")]),
            dbc.CardBody(
                dbc.ButtonGroup([
                    dbc.Button([html.I(className="bi bi-check-circle me-1"), "Approve"], id="approve-btn", color="success"),
                    dbc.Button([html.I(className="bi bi-x-circle me-1"), "Reject"], id="reject-btn", color="danger"),
                ])
            ),
        ], color="warning", outline=True, className="mt-3")
    else:
        # Render disabled buttons so their IDs always exist in the layout
        signoff_panel = html.Div([
            dbc.Button(id="approve-btn", style={"display": "none"}),
            dbc.Button(id="reject-btn", style={"display": "none"}),
        ])

    panel = dbc.Card([
        dbc.CardHeader([
            html.Strong(record.get("provider_name", "")),
            html.Span(f" — {record.get('timestamp', '')[:19].replace('T', ' ')}", className="text-muted ms-2 small"),
            status_badge(status),
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(extracted_panel, md=6, className="mb-3"),
                dbc.Col(scoring_panel, md=6, className="mb-3"),
            ]),
            signoff_panel,
        ]),
    ], className="shadow-sm")

    return panel, {"display": "block"}, submission_id


# CB-6: Approve
@callback(
    Output("signoff-result", "children"),
    Output("dashboard-trigger", "data", allow_duplicate=True),
    Input("approve-btn", "n_clicks"),
    State("selected-submission-id", "data"),
    State("dashboard-trigger", "data"),
    prevent_initial_call=True,
)
def approve_submission(n_clicks, submission_id, trigger):
    if not n_clicks or not submission_id:
        return None, trigger
    submissions = load_submissions()
    for record in submissions:
        if record.get("id") == submission_id:
            record["status"] = "MANUALLY_APPROVED"
            record["specialist_action"] = "approved"
            record["specialist_timestamp"] = datetime.now().isoformat()
            save_submissions(submissions)
            try:
                save_to_hospital_db({"provider_name": record["provider_name"], "extracted_data": record.get("extracted_data", {})})
            except Exception:
                pass
            log_audit_event({"action": "Specialist Approval", "provider": record["provider_name"], "submission_id": submission_id})
            return dbc.Alert([html.I(className="bi bi-check-circle me-2"), f"Approved and saved to hospital database."], color="success"), (trigger or 0) + 1
    return dbc.Alert("Submission not found.", color="warning"), trigger


# CB-7: Reject
@callback(
    Output("signoff-result", "children", allow_duplicate=True),
    Output("dashboard-trigger", "data", allow_duplicate=True),
    Input("reject-btn", "n_clicks"),
    State("selected-submission-id", "data"),
    State("dashboard-trigger", "data"),
    prevent_initial_call=True,
)
def reject_submission(n_clicks, submission_id, trigger):
    if not n_clicks or not submission_id:
        return None, trigger
    submissions = load_submissions()
    for record in submissions:
        if record.get("id") == submission_id:
            record["status"] = "REJECTED"
            record["specialist_action"] = "rejected"
            record["specialist_timestamp"] = datetime.now().isoformat()
            save_submissions(submissions)
            log_audit_event({"action": "Specialist Rejection", "provider": record["provider_name"], "submission_id": submission_id})
            return dbc.Alert([html.I(className="bi bi-x-circle me-2"), "Submission rejected."], color="danger"), (trigger or 0) + 1
    return dbc.Alert("Submission not found.", color="warning"), trigger


# ==========================================
# RUN APP
# ==========================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)
