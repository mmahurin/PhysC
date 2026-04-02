import type { Submission } from '../types'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed with status ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) message = body.detail
      else if (typeof body === 'string') message = body
    } catch {
      // ignore parse error
    }
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export async function submitCredentials(formData: FormData): Promise<Submission> {
  const res = await fetch('/api/submit', {
    method: 'POST',
    body: formData,
  })
  return handleResponse<Submission>(res)
}

export async function getSubmissions(): Promise<Submission[]> {
  const res = await fetch('/api/submissions')
  return handleResponse<Submission[]>(res)
}

export async function approveSubmission(id: string): Promise<Submission> {
  const res = await fetch(`/api/submissions/${id}/approve`, {
    method: 'POST',
  })
  return handleResponse<Submission>(res)
}

export async function rejectSubmission(id: string): Promise<Submission> {
  const res = await fetch(`/api/submissions/${id}/reject`, {
    method: 'POST',
  })
  return handleResponse<Submission>(res)
}
