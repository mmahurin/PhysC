import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import type { Deduction } from '@/types'
import { cn } from '@/lib/utils'

interface ScoreBreakdownProps {
  score: number
  deductions: Deduction[]
}

function scoreColor(score: number): string {
  if (score >= 95) return 'bg-green-500'
  if (score >= 80) return 'bg-amber-500'
  return 'bg-red-500'
}

function scoreProgressClass(score: number): string {
  if (score >= 95) return '[&>div]:bg-green-500'
  if (score >= 80) return '[&>div]:bg-amber-500'
  return '[&>div]:bg-red-500'
}

export function ScoreBreakdown({ score, deductions }: ScoreBreakdownProps) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Scoring Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Confidence Score</span>
            <span
              className={cn(
                'font-bold text-lg',
                score >= 95 ? 'text-green-600' : score >= 80 ? 'text-amber-600' : 'text-red-600'
              )}
            >
              {score}%
            </span>
          </div>
          <Progress value={score} className={cn('h-3', scoreProgressClass(score))} />
        </div>

        <div className="space-y-1">
          {/* Starting row */}
          <div className="flex items-center justify-between rounded-md px-3 py-2 bg-muted/50 text-sm text-muted-foreground">
            <span>Starting Score</span>
            <Badge variant="secondary">100</Badge>
          </div>

          {/* Deductions */}
          {deductions.map((d, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-md px-3 py-2 bg-red-50 text-sm"
            >
              <span className="text-red-800 flex-1 mr-2">{d.reason}</span>
              <Badge variant="destructive">-{d.points}</Badge>
            </div>
          ))}

          {/* Final score */}
          <div className="flex items-center justify-between rounded-md px-3 py-2 bg-muted text-sm font-bold">
            <span>Final Score</span>
            <div
              className={cn(
                'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold text-white',
                scoreColor(score)
              )}
            >
              {score}%
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
