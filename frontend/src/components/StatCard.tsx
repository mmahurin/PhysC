import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: number
  color: 'blue' | 'green' | 'amber' | 'red'
}

const colorMap = {
  blue: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    value: 'text-blue-700',
    label: 'text-blue-600',
  },
  green: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    value: 'text-green-700',
    label: 'text-green-600',
  },
  amber: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    value: 'text-amber-700',
    label: 'text-amber-600',
  },
  red: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    value: 'text-red-700',
    label: 'text-red-600',
  },
}

export function StatCard({ label, value, color }: StatCardProps) {
  const c = colorMap[color]
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border p-6 shadow-sm',
        c.bg,
        c.border
      )}
    >
      <span className={cn('text-4xl font-bold tabular-nums', c.value)}>{value}</span>
      <span className={cn('mt-1 text-sm font-medium', c.label)}>{label}</span>
    </div>
  )
}
