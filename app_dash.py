# -*- coding: utf-8 -*-
"""Physician Credentialing System with AI and OCR - Dash Version"""

import os
import json
import base64
import io
from datetime import datetime

import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc

# Import the credential system from the core module
import sys
sys.path.insert(0, os.path.dirname(__file__))

from physican_core import (
    CredentialSystem,
    extract_text_from_document,
    load_spacy_model
)

# ==========================================
# DASH APP INITIALIZATION
# ==========================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Physician Credentialing System"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_upload_content(contents, filename):
    """Parse uploaded file content."""
    if not contents:
        return None, None, ""
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    file_type = 'pdf' if filename.lower().endswith('.pdf') else 'image'
    text = extract_text_from_document(
        type('obj', (object,), {
            'getvalue': lambda: decoded,
            'name': filename
        })(),
        file_type
    )
    
    return decoded, file_type, text

# ==========================================
# LAYOUT
# ==========================================

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Physician Credentialing System", className="mb-4 mt-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Provider Information", className="card-title"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Provider Name *"),
                            dbc.Input(
                                id="provider-name",
                                type="text",
                                placeholder="Enter provider name",
                                className="mb-3"
                            )
                        ], md=12)
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("SMS Number (optional)"),
                            dbc.Input(
                                id="sms-number",
                                type="tel",
                                placeholder="Enter SMS number",
                                className="mb-3"
                            )
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Email (optional)"),
                            dbc.Input(
                                id="email-address",
                                type="email",
                                placeholder="Enter email",
                                className="mb-3"
                            )
                        ], md=6)
                    ])
                ])
            ], className="mb-4")
        ], md=8)
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Upload Documents", className="card-title"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("CV (PDF/Image)"),
                            dcc.Upload(
                                id="upload-cv",
                                children=html.Div([
                                    "Drag and drop or ",
                                    html.A("select a file")
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'marginBottom': '10px'
                                },
                                accept='.pdf,.jpg,.png,.jpeg'
                            ),
                            html.Div(id="cv-filename", style={"fontSize": "12px", "color": "green"})
                        ], md=6),
                        dbc.Col([
                            dbc.Label("License *"),
                            dcc.Upload(
                                id="upload-license",
                                children=html.Div([
                                    "Drag and drop or ",
                                    html.A("select a file")
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'marginBottom': '10px'
                                },
                                accept='.pdf,.jpg,.png,.jpeg'
                            ),
                            html.Div(id="license-filename", style={"fontSize": "12px", "color": "green"})
                        ], md=6)
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Identity Document"),
                            dcc.Upload(
                                id="upload-identity",
                                children=html.Div([
                                    "Drag and drop or ",
                                    html.A("select a file")
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'marginBottom': '10px'
                                },
                                accept='.pdf,.jpg,.png,.jpeg'
                            ),
                            html.Div(id="identity-filename", style={"fontSize": "12px", "color": "green"})
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Diploma"),
                            dcc.Upload(
                                id="upload-diploma",
                                children=html.Div([
                                    "Drag and drop or ",
                                    html.A("select a file")
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'marginBottom': '10px'
                                },
                                accept='.pdf,.jpg,.png,.jpeg'
                            ),
                            html.Div(id="diploma-filename", style={"fontSize": "12px", "color": "green"})
                        ], md=6)
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("DEA Certificate"),
                            dcc.Upload(
                                id="upload-dea",
                                children=html.Div([
                                    "Drag and drop or ",
                                    html.A("select a file")
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'marginBottom': '10px'
                                },
                                accept='.pdf,.jpg,.png,.jpeg'
                            ),
                            html.Div(id="dea-filename", style={"fontSize": "12px", "color": "green"})
                        ], md=6)
                    ])
                ])
            ], className="mb-4")
        ], md=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Button(
                "Run Simulation",
                id="submit-button",
                color="primary",
                size="lg",
                className="w-100"
            )
        ], md=12)
    ]),
    
    # Hidden divs to store uploaded files
    dcc.Store(id="cv-data"),
    dcc.Store(id="license-data"),
    dcc.Store(id="identity-data"),
    dcc.Store(id="diploma-data"),
    dcc.Store(id="dea-data"),
    
    # Results section
    dbc.Row([
        dbc.Col([
            html.Div(id="results-container", className="mt-4")
        ], md=12)
    ], className="mt-4"),
    
    # Loading spinner
    dcc.Loading(id="loading", type="default", children=[]),
    
], fluid=True, className="bg-light", style={"minHeight": "100vh", "paddingBottom": "50px"})

# ==========================================
# CALLBACKS
# ==========================================

@callback(
    [Output("cv-data", "data"), Output("cv-filename", "children")],
    Input("upload-cv", "contents"),
    State("upload-cv", "filename")
)
def store_cv(contents, filename):
    if not contents:
        return None, ""
    decoded, ftype, text = parse_upload_content(contents, filename)
    return {"binary": decoded, "type": ftype, "text": text, "filename": filename}, f"✓ {filename}"

@callback(
    [Output("license-data", "data"), Output("license-filename", "children")],
    Input("upload-license", "contents"),
    State("upload-license", "filename")
)
def store_license(contents, filename):
    if not contents:
        return None, ""
    decoded, ftype, text = parse_upload_content(contents, filename)
    return {"binary": decoded, "type": ftype, "text": text, "filename": filename}, f"✓ {filename}"

@callback(
    [Output("identity-data", "data"), Output("identity-filename", "children")],
    Input("upload-identity", "contents"),
    State("upload-identity", "filename")
)
def store_identity(contents, filename):
    if not contents:
        return None, ""
    decoded, ftype, text = parse_upload_content(contents, filename)
    return {"binary": decoded, "type": ftype, "text": text, "filename": filename}, f"✓ {filename}"

@callback(
    [Output("diploma-data", "data"), Output("diploma-filename", "children")],
    Input("upload-diploma", "contents"),
    State("upload-diploma", "filename")
)
def store_diploma(contents, filename):
    if not contents:
        return None, ""
    decoded, ftype, text = parse_upload_content(contents, filename)
    return {"binary": decoded, "type": ftype, "text": text, "filename": filename}, f"✓ {filename}"

@callback(
    [Output("dea-data", "data"), Output("dea-filename", "children")],
    Input("upload-dea", "contents"),
    State("upload-dea", "filename")
)
def store_dea(contents, filename):
    if not contents:
        return None, ""
    decoded, ftype, text = parse_upload_content(contents, filename)
    return {"binary": decoded, "type": ftype, "text": text, "filename": filename}, f"✓ {filename}"

@callback(
    Output("results-container", "children"),
    Input("submit-button", "n_clicks"),
    [
        State("provider-name", "value"),
        State("sms-number", "value"),
        State("email-address", "value"),
        State("cv-data", "data"),
        State("license-data", "data"),
        State("identity-data", "data"),
        State("diploma-data", "data"),
        State("dea-data", "data")
    ],
    prevent_initial_call=True
)
def run_simulation(n_clicks, provider_name, sms_number, email_address, cv_data, license_data, identity_data, diploma_data, dea_data):
    if not provider_name:
        return dbc.Alert("Provider name is required.", color="danger")
    
    if not license_data:
        return dbc.Alert("License document is required.", color="danger")
    
    # Prepare file data
    files = {
        "CV": cv_data or {"binary": None, "type": None, "text": ""},
        "License": license_data,
        "Identity": identity_data or {"binary": None, "type": None, "text": ""},
        "Diploma": diploma_data or {"binary": None, "type": None, "text": ""},
        "DEA": dea_data or {"binary": None, "type": None, "text": ""}
    }
    
    uploaded_status = {name: bool(data) for name, data in files.items()}
    
    try:
        # Run the credential system
        system = CredentialSystem(
            provider_name,
            sms_number,
            email_address,
            uploaded_documents=uploaded_status
        )
        
        status = system.preprocessing_agent(
            files['CV']['binary'], files['CV']['type'],
            files['License']['binary'], files['License']['type'],
            files['CV']['text'], files['License']['text']
        )
        
        if status != "SUCCESS":
            return dbc.Alert(f"Preprocessing failed: {status}", color="warning")
        
        extracted = system.extraction_agent(
            files['CV']['text'], files['License']['text'],
            provider_name, files['Identity']['text'],
            files['Diploma']['text'], files['DEA']['text']
        )
        
        if not isinstance(extracted, dict):
            return dbc.Alert(f"Extraction failed: {extracted}", color="warning")
        
        v_status = system.verification_flow()
        
        if v_status != "SUCCESS":
            return dbc.Alert(f"Verification failed: {v_status}", color="warning")
        
        final_status = system.scoring_agent()
        
        # Generate results display
        results_cards = [
            dbc.Alert("✅ Simulation Completed Successfully!", color="success", className="mb-3")
        ]
        
        results_cards.append(
            dbc.Card([
                dbc.CardBody([
                    html.H5("Final Results", className="card-title"),
                    html.P(f"Status: {final_status}"),
                    html.P(f"Confidence Score: {system.confidence_score}%"),
                    html.Hr(),
                    html.H6("Extracted Data:"),
                    html.Pre(json.dumps(system.extracted_data, indent=2), style={"fontSize": "12px"})
                ])
            ], className="mb-3")
        )
        
        return results_cards
        
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")

# ==========================================
# RUN APP
# ==========================================

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
