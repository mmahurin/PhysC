import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, Loader2, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { getSubmissions, approveSubmission, rejectSubmission, deleteSubmission } from '@/api/client'
import type { Submission, SubmissionStatus } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { StatCard } from '@/components/StatCard'
import { ScoreBreakdown } from '@/components/ScoreBreakdown'
import { ExtractedDataView } from '@/components/ExtractedDataView'
import { cn } from '@/lib/utils'

function statusBadge(status: SubmissionStatus) {
  switch (status) {
    case 'AUTO_APPROVED':
    case 'MANUALLY_APPROVED':
      return <Badge variant="success">{status.replace(/_/g, ' ')}</Badge>
    case 'PENDING_SPECIALIST_REVIEW':
      return <Badge variant="warning">PENDING REVIEW</Badge>
    case 'REJECTED':
      return <Badge variant="secondary">REJECTED</Badge>
    default:
      return <Badge variant="destructive">{status.replace(/_/g, ' ')}</Badge>
  }
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ts.slice(0, 19).replace('T', ' ')
  }
}

export function DashboardPage() {
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Submission | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getSubmissions()
      const sorted = [...data].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
      setSubmissions(sorted)
      // Keep selected in sync with latest data
      setSelected((prev) => {
        if (!prev) return null
        return sorted.find((s) => s.id === prev.id) ?? null
      })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load submissions.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function handleApprove() {
    if (!selected) return
    setActionLoading(true)
    try {
      const updated = await approveSubmission(selected.id)
      toast.success(`${updated.provider_name} has been approved.`)
      setSelected(updated)
      await load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Approval failed.')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleDelete() {
    if (!selected) return
    setActionLoading(true)
    try {
      await deleteSubmission(selected.id)
      toast.success(`Record for ${selected.provider_name} deleted.`)
      setSelected(null)
      setConfirmDelete(false)
      await load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Deletion failed.')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleReject() {
    if (!selected) return
    setActionLoading(true)
    try {
      const updated = await rejectSubmission(selected.id)
      toast.success(`${updated.provider_name}'s submission has been rejected.`)
      setSelected(updated)
      await load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Rejection failed.')
    } finally {
      setActionLoading(false)
    }
  }

  // Stats
  const total = submissions.length
  const approved = submissions.filter((s) =>
    ['AUTO_APPROVED', 'MANUALLY_APPROVED'].includes(s.status)
  ).length
  const pending = submissions.filter((s) => s.status === 'PENDING_SPECIALIST_REVIEW').length
  const retryFailed = submissions.filter((s) =>
    ['RETRY_REQUIRED', 'FAILED', 'REJECTED'].includes(s.status)
  ).length

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Specialist Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Review, approve, or reject pending credentialing submissions.
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total Submissions" value={total} color="blue" />
        <StatCard label="Approved" value={approved} color="green" />
        <StatCard label="Pending Review" value={pending} color="amber" />
        <StatCard label="Retry / Failed" value={retryFailed} color="red" />
      </div>

      {/* Submissions Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Submissions</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void load()}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              )}
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading && submissions.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading submissions&hellip;
            </div>
          ) : submissions.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground text-sm">
              No submissions yet.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Provider</TableHead>
                  <TableHead>Date Submitted</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {submissions.map((s) => (
                  <TableRow
                    key={s.id}
                    className={cn(
                      'cursor-pointer',
                      selected?.id === s.id ? 'bg-primary/5 hover:bg-primary/5' : ''
                    )}
                    onClick={() => { setSelected(selected?.id === s.id ? null : s); setConfirmDelete(false) }}
                  >
                    <TableCell className="font-medium">{s.provider_name}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatTimestamp(s.timestamp)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          'font-semibold',
                          s.confidence_score >= 95
                            ? 'text-green-600'
                            : s.confidence_score >= 80
                              ? 'text-amber-600'
                              : 'text-red-600'
                        )}
                      >
                        {s.confidence_score}%
                      </span>
                    </TableCell>
                    <TableCell>{statusBadge(s.status)}</TableCell>
                    <TableCell>
                      <button
                        className="p-1 rounded text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors"
                        onClick={(e) => { e.stopPropagation(); setSelected(s); setConfirmDelete(true) }}
                        title="Delete record"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Detail Panel */}
      {selected && (
        <Card className="animate-in fade-in-0 slide-in-from-top-4 duration-300">
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-lg">{selected.provider_name}</CardTitle>
              {statusBadge(selected.status)}
              <span className="ml-auto text-sm text-muted-foreground">
                {formatTimestamp(selected.timestamp)}
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <ExtractedDataView data={selected.extracted_data} />
              <ScoreBreakdown
                score={selected.confidence_score}
                deductions={selected.deductions}
              />
            </div>

            {/* Specialist Actions */}
            {selected.status === 'PENDING_SPECIALIST_REVIEW' && (
              <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-amber-900">Specialist Action Required</p>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Review the extracted data and scoring breakdown, then approve or reject.
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-red-300 text-red-700 hover:bg-red-50"
                    onClick={handleReject}
                    disabled={actionLoading}
                  >
                    {actionLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      'Reject'
                    )}
                  </Button>
                  <Button
                    size="sm"
                    className="bg-green-600 hover:bg-green-700 text-white"
                    onClick={handleApprove}
                    disabled={actionLoading}
                  >
                    {actionLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      'Approve'
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Delete */}
            {confirmDelete ? (
              <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-900">Delete this record?</p>
                  <p className="text-xs text-red-700 mt-0.5">This cannot be undone.</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button variant="outline" size="sm" onClick={() => setConfirmDelete(false)} disabled={actionLoading}>
                    Cancel
                  </Button>
                  <Button size="sm" className="bg-red-600 hover:bg-red-700 text-white" onClick={handleDelete} disabled={actionLoading}>
                    {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Delete'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex justify-end">
                <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-red-600 hover:bg-red-50" onClick={() => setConfirmDelete(true)}>
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  Delete Record
                </Button>
              </div>
            )}

            {/* Show specialist action result for completed reviews */}
            {selected.specialist_action && selected.specialist_timestamp && (
              <div className="rounded-lg border bg-muted/30 p-4 text-sm">
                <p className="text-muted-foreground">
                  <span className="font-medium text-foreground capitalize">
                    {selected.specialist_action}
                  </span>{' '}
                  by specialist on {formatTimestamp(selected.specialist_timestamp)}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
