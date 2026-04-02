import type { ReactNode } from 'react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ExtractedData, ExtractedCV } from '@/types'

interface ExtractedDataViewProps {
  data: ExtractedData
}

function KVTable({ entries }: { entries: [string, string][] }) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {entries.map(([key, val]) => (
          <tr key={key} className="border-b last:border-0">
            <td className="py-1.5 pr-4 font-medium text-muted-foreground capitalize w-2/5">
              {key.replace(/_/g, ' ')}
            </td>
            <td className="py-1.5 text-foreground break-words">{val}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function CVSection({ cv }: { cv: ExtractedCV }) {
  return (
    <div className="space-y-4">
      {cv.employment_history && cv.employment_history.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Employment History
          </p>
          <div className="space-y-2">
            {cv.employment_history.map((job, i) => (
              <div key={i} className="rounded-md border p-3 text-sm">
                <p className="font-medium">{job.job_title}</p>
                <p className="text-muted-foreground">{job.employer}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {job.start_date} — {job.end_date}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
      {cv.education && cv.education.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Education
          </p>
          <div className="space-y-2">
            {cv.education.map((edu, i) => (
              <div key={i} className="rounded-md border p-3 text-sm">
                <p className="font-medium">{edu.degree_type}</p>
                <p className="text-muted-foreground">{edu.institution}</p>
                <p className="text-xs text-muted-foreground mt-1">{edu.graduation_date}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function ExtractedDataView({ data }: ExtractedDataViewProps) {
  const sections: { key: string; label: string; content: ReactNode }[] = []

  if (data.license && Object.keys(data.license).length > 0) {
    const entries = Object.entries(data.license).map(([k, v]) => [k, String(v)] as [string, string])
    sections.push({ key: 'license', label: 'Medical License', content: <KVTable entries={entries} /> })
  }

  if (data.identity_document && Object.keys(data.identity_document).length > 0) {
    const entries = Object.entries(data.identity_document).map(
      ([k, v]) => [k, String(v)] as [string, string]
    )
    sections.push({
      key: 'identity',
      label: 'Identity Document',
      content: <KVTable entries={entries} />,
    })
  }

  if (data.medical_diploma && Object.keys(data.medical_diploma).length > 0) {
    const entries = Object.entries(data.medical_diploma).map(
      ([k, v]) => [k, String(v)] as [string, string]
    )
    sections.push({ key: 'diploma', label: 'Medical Diploma', content: <KVTable entries={entries} /> })
  }

  if (data.dea_certificate && Object.keys(data.dea_certificate).length > 0) {
    const entries = Object.entries(data.dea_certificate).map(([k, v]) => {
      const display = Array.isArray(v) ? v.join(', ') : String(v)
      return [k, display] as [string, string]
    })
    sections.push({
      key: 'dea',
      label: 'DEA Certificate',
      content: <KVTable entries={entries} />,
    })
  }

  if (data.cv && (data.cv.employment_history?.length || data.cv.education?.length)) {
    sections.push({ key: 'cv', label: 'Curriculum Vitae', content: <CVSection cv={data.cv} /> })
  }

  if (sections.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Extracted Data</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No extracted data available.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Extracted Data</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <Accordion type="multiple" className="w-full">
          {sections.map((section) => (
            <AccordionItem key={section.key} value={section.key}>
              <AccordionTrigger className="text-sm font-medium">{section.label}</AccordionTrigger>
              <AccordionContent>{section.content}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </CardContent>
    </Card>
  )
}
