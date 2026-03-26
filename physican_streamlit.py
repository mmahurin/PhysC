# -*- coding: utf-8 -*-
"""Physician Credentialing System with AI and OCR - Streamlit Version"""

import json
import streamlit as st

from physican_core import (
    CredentialSystem,
    extract_text_from_document,
    load_spacy_model
)

# ==========================================
# STREAMLIT UI & EXECUTION
# ==========================================

st.title("Physician Credentialing Simulation")

with st.form(key='simulation_form'):
    provider_name = st.text_input("Provider Name")
    sms_input = st.text_input("SMS Number (optional)")
    email_input = st.text_input("Email (optional)")

    cols = st.columns(3)
    cv_file = cols[0].file_uploader("Upload CV", type=['pdf','jpg','png'])
    license_file = cols[1].file_uploader("Upload License", type=['pdf','jpg','png'])
    identity_file = cols[2].file_uploader("Upload ID", type=['pdf','jpg','png'])

    cols2 = st.columns(2)
    diploma_file = cols2[0].file_uploader("Upload Diploma", type=['pdf','jpg','png'])
    dea_file = cols2[1].file_uploader("Upload DEA", type=['pdf','jpg','png'])

    run = st.form_submit_button("Run Simulation")

if run:
    if not license_file:
        st.error("License document required.")
    else:
        with st.spinner("Running simulation..."):
            # Process files
            files = {}
            uploaded_status = {}
            for name, fobj in [("CV", cv_file), ("License", license_file), ("Identity", identity_file), ("Diploma", diploma_file), ("DEA", dea_file)]:
                if fobj:
                    content = fobj.getvalue()
                    ftype = 'pdf' if fobj.name.lower().endswith('.pdf') else 'image'
                    txt = extract_text_from_document(fobj, ftype)
                    files[name] = {'bin': content, 'type': ftype, 'txt': txt}
                    uploaded_status[name] = True
                else:
                    files[name] = {'bin': None, 'type': None, 'txt': ""}
                    uploaded_status[name] = False

            system = CredentialSystem(provider_name, sms_input, email_input, uploaded_documents=uploaded_status)

            status = system.preprocessing_agent(files['CV']['bin'], files['CV']['type'], files['License']['bin'], files['License']['type'], files['CV']['txt'], files['License']['txt'])
            if status == "SUCCESS":
                extracted = system.extraction_agent(files['CV']['txt'], files['License']['txt'], provider_name, files['Identity']['txt'], files['Diploma']['txt'], files['DEA']['txt'])
                if isinstance(extracted, dict):
                    v_status = system.verification_flow()
                    if v_status == "SUCCESS":
                        final_status = system.scoring_agent()
                        record = {"provider_name": provider_name, "final_status": final_status, "extracted_data": system.extracted_data}

                        fname = f"golden_record_{provider_name.replace(' ', '_')}.json"
                        with open(fname, 'w') as f: json.dump(record, f, indent=2)

                        if final_status in ["COMPLETE", "MANUALLY_APPROVED", "AUTOMATICALLY_APPROVED"]:
                            # Attempt to append to hospital DB if present
                            try:
                                from physican_core import save_to_hospital_db
                                save_to_hospital_db(record)
                            except Exception:
                                st.warning("Could not update hospital_db.csv (file missing or write permission).")
                            st.success("✅ SIMULATION COMPLETE: SUCCESS")
                        else:
                            st.error(f"❌ SIMULATION ENDED: {final_status}")
                    else:
                        st.error(f"❌ Verification Failed: {v_status}")
                else:
                    st.error(f"❌ Extraction Failed: {extracted}")
            else:
                st.error(f"❌ Preprocessing Failed: {status}")
