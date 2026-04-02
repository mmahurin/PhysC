# PhysC

**An API key is needed, the template for an OPENAI api is locate in .env.example just add your key.**

This AI system automates physician credentialing. It uses OCR and LLMs to extract data from documents like licenses and diplomas. It verifies information, checks for sanctions, scores confidence, and handles approvals or requests for corrections. The goal is to streamline credentialing and maintain a hospital database.

Automate and streamline the process of verifying physician qualifications. It leverages a suite of technologies including pytesseract for Optical Character Recognition (OCR) to extract text from various document types (PDFs, images), PyPDF2 and pdf2image for document handling, and spaCy for natural language processing.

The core of the system is the CredentialSystem class, which orchestrates a multi-agent workflow. This includes a preprocessing_agent that assesses document quality and readability, flagging issues like blurriness. An extraction_agent then utilizes an OpenAI Large Language Model (specifically gpt-4o-mini) to parse structured data such as license numbers, DEA certificates, medical diplomas, and identity information, based on predefined JSON schemas. A verification_agent performs critical sanction checks against databases like the publicly accesbile NPDB.

A scoring_agent calculates a comprehensive confidence score, deducting points for missing documents, visual quality issues, and semantic inconsistencies identified by another LLM-powered validation step. If the score is below a certain threshold, a nudge_agent generates personalized messages to the physician, prompting them to address discrepancies. For higher scores, a Human-In-The-Loop (HITL) dashboard determines final approval, with a manual override option for specialists. Successfully credentialed physicians are notified, and their 'golden record' is saved to hospital_db for future reference, ensuring an auditable and efficient credentialing process.
