export interface Deduction {
  reason: string
  points: number
}

export interface ExtractedLicense {
  license_no: string
  expiration_date: string
  status: string
}

export interface ExtractedIdentity {
  full_name: string
  dob: string
  ssn: string
  photo_id_match: string
}

export interface ExtractedDiploma {
  degree_type: string
  institution: string
  graduation_date: string
}

export interface ExtractedDEA {
  dea_number: string
  schedules: string[]
  expiration_date: string
}

export interface ExtractedCV {
  employment_history: Array<{
    job_title: string
    employer: string
    start_date: string
    end_date: string
  }>
  education: Array<{
    degree_type: string
    institution: string
    graduation_date: string
  }>
}

export interface ExtractedData {
  provider_name?: string
  license?: ExtractedLicense
  identity_document?: ExtractedIdentity
  medical_diploma?: ExtractedDiploma
  dea_certificate?: ExtractedDEA
  cv?: ExtractedCV
}

export type SubmissionStatus =
  | 'AUTO_APPROVED'
  | 'PENDING_SPECIALIST_REVIEW'
  | 'MANUALLY_APPROVED'
  | 'REJECTED'
  | 'RETRY_REQUIRED'
  | 'FAILED'

export interface Submission {
  id: string
  provider_name: string
  timestamp: string
  sms_number: string | null
  email_address: string | null
  confidence_score: number
  deductions: Deduction[]
  extracted_data: ExtractedData
  visual_fidelity_metrics: Record<string, number>
  status: SubmissionStatus
  notification_channel: string
  notification_message: string
  specialist_action: string | null
  specialist_timestamp: string | null
}
