import { useState } from 'react'
import { Hospital, Loader2, CheckCircle, AlertTriangle, XCircle, Bell } from 'lucide-react'
import { toast } from 'sonner'
import { submitCredentials } from '@/api/client'
import type { Submission } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { FileUploadZone } from '@/components/FileUploadZone'
import { cn } from '@/lib/utils'

type FileKey = 'cv' | 'license' | 'identity' | 'diploma' | 'dea'

const FILE_LABELS: Record<FileKey, { label: string; required?: boolean }> = {
  cv: { label: 'Curriculum Vitae (CV)' },
  license: { label: 'Medical License', required: true },
  identity: { label: 'Identity Document' },
  diploma: { label: 'Medical Diploma' },
  dea: { label: 'DEA Certificate' },
}

function statusConfig(status: Submission['status']) {
  switch (status) {
    case 'AUTO_APPROVED':
      return {
        icon: <CheckCircle className="h-6 w-6 text-green-600" />,
        badge: <Badge variant="success">AUTO APPROVED</Badge>,
        message: 'Your credentials have been automatically approved.',
        bg: 'bg-green-50 border-green-200',
      }
    case 'PENDING_SPECIALIST_REVIEW':
      return {
        icon: <AlertTriangle className="h-6 w-6 text-amber-600" />,
        badge: <Badge variant="warning">PENDING REVIEW</Badge>,
        message: 'Your submission is under specialist review. You will be notified of the outcome.',
        bg: 'bg-amber-50 border-amber-200',
      }
    default:
      return {
        icon: <XCircle className="h-6 w-6 text-red-600" />,
        badge: <Badge variant="destructive">RESUBMISSION REQUIRED</Badge>,
        message: 'Issues were found with your submission. Please review the notification sent to you.',
        bg: 'bg-red-50 border-red-200',
      }
  }
}

function scoreProgressClass(score: number) {
  if (score >= 95) return '[&>div]:bg-green-500'
  if (score >= 80) return '[&>div]:bg-amber-500'
  return '[&>div]:bg-red-500'
}

export function SubmissionPage() {
  const [providerName, setProviderName] = useState('')
  const [smsNumber, setSmsNumber] = useState('')
  const [emailAddress, setEmailAddress] = useState('')
  const [files, setFiles] = useState<Partial<Record<FileKey, File>>>({})
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Submission | null>(null)

  function setFile(key: FileKey, file: File) {
    setFiles((prev) => ({ ...prev, [key]: file }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!providerName.trim()) {
      toast.error('Provider name is required.')
      return
    }
    if (!files.license) {
      toast.error('Medical License document is required.')
      return
    }

    const formData = new FormData()
    formData.append('provider_name', providerName.trim())
    if (smsNumber.trim()) formData.append('sms_number', smsNumber.trim())
    if (emailAddress.trim()) formData.append('email_address', emailAddress.trim())

    if (files.cv) formData.append('cv', files.cv)
    formData.append('license', files.license)
    if (files.identity) formData.append('identity', files.identity)
    if (files.diploma) formData.append('diploma', files.diploma)
    if (files.dea) formData.append('dea', files.dea)

    setLoading(true)
    setResult(null)
    try {
      const submission = await submitCredentials(formData)
      setResult(submission)
      toast.success('Submission processed successfully.')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Submission failed.'
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  const cfg = result ? statusConfig(result.status) : null
  const licData = result?.extracted_data?.license

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary p-2.5">
          <Hospital className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Physician Credential Submission</h1>
          <p className="text-sm text-muted-foreground">
            Submit your credentialing documents for review and verification.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Provider Info */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Provider Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="provider-name">
                Provider Name{' '}
                <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 ml-1">
                  Required
                </span>
              </Label>
              <Input
                id="provider-name"
                type="text"
                placeholder="Dr. Jane Smith"
                value={providerName}
                onChange={(e) => setProviderName(e.target.value)}
                required
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="sms-number">SMS Number (optional)</Label>
                <Input
                  id="sms-number"
                  type="tel"
                  placeholder="+1 555 000 0000"
                  value={smsNumber}
                  onChange={(e) => setSmsNumber(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email-address">Email Address (optional)</Label>
                <Input
                  id="email-address"
                  type="email"
                  placeholder="doctor@hospital.com"
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Document Uploads */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Upload Credentialing Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              {(Object.entries(FILE_LABELS) as [FileKey, { label: string; required?: boolean }][]).map(
                ([key, { label, required }]) => (
                  <FileUploadZone
                    key={key}
                    id={`file-${key}`}
                    label={label}
                    required={required}
                    file={files[key] ?? null}
                    onFile={(f) => setFile(key, f)}
                  />
                )
              )}
            </div>
          </CardContent>
        </Card>

        {/* Submit */}
        <Button type="submit" size="lg" className="w-full" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing Credentials&hellip;
            </>
          ) : (
            'Submit Credentials'
          )}
        </Button>
      </form>

      {/* Result */}
      {result && cfg && (
        <div className="space-y-4 animate-in fade-in-0 slide-in-from-bottom-4 duration-500">
          {/* Status Card */}
          <Card className={cn('border', cfg.bg)}>
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                {cfg.icon}
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="font-semibold text-foreground">Credentialing Result</span>
                    {cfg.badge}
                  </div>
                  <p className="text-sm text-muted-foreground">{cfg.message}</p>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Confidence Score</span>
                  <span
                    className={cn(
                      'font-bold',
                      result.confidence_score >= 95
                        ? 'text-green-600'
                        : result.confidence_score >= 80
                          ? 'text-amber-600'
                          : 'text-red-600'
                    )}
                  >
                    {result.confidence_score}%
                  </span>
                </div>
                <Progress
                  value={result.confidence_score}
                  className={cn('h-2.5', scoreProgressClass(result.confidence_score))}
                />
              </div>
            </CardContent>
          </Card>

          {/* Notification */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Bell className="h-4 w-4" />
                Notification Sent
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground text-xs mb-0.5">Channel</p>
                  <p className="font-medium">{result.notification_channel}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs mb-0.5">Contact</p>
                  <p className="font-medium">{result.sms_number ?? result.email_address ?? '—'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick summary if approved/pending */}
          {(result.status === 'AUTO_APPROVED' || result.status === 'PENDING_SPECIALIST_REVIEW') &&
            licData && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">License Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
                    <div>
                      <p className="text-muted-foreground text-xs mb-0.5">Provider</p>
                      <p className="font-medium">{result.provider_name}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs mb-0.5">License Number</p>
                      <p className="font-medium">{licData.license_no ?? 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs mb-0.5">Expiration Date</p>
                      <p className="font-medium">{licData.expiration_date ?? 'N/A'}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
        </div>
      )}
    </div>
  )
}
