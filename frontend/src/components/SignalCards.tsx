import { AlertTriangle, Mail, Shield, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SecuritySignal } from '@/types'

const SEVERITY_COLORS = {
  low: 'border-l-slate-400 bg-slate-50',
  medium: 'border-l-yellow-400 bg-yellow-50',
  high: 'border-l-orange-400 bg-orange-50',
  critical: 'border-l-red-400 bg-red-50',
}

const SIGNAL_ICONS: Record<string, typeof Mail> = {
  employee_emails_exposed: Mail,
  breach_events: AlertTriangle,
  password_exposure: Shield,
  repeated_identity_exposure: RefreshCw,
}

export function SignalCards({ signals }: { signals: SecuritySignal[] }) {
  if (!signals.length) return null

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-900">Key Findings</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {signals.map((signal, i) => {
          const Icon = SIGNAL_ICONS[signal.signal_type] || AlertTriangle
          return (
            <div
              key={i}
              className={cn(
                'border-l-4 rounded-lg p-4',
                SEVERITY_COLORS[signal.severity]
              )}
            >
              <div className="flex items-start gap-3">
                <Icon className="w-5 h-5 text-slate-600 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-slate-900">{signal.title}</p>
                  <p className="text-xs text-slate-600 mt-1">{signal.description}</p>
                  <span className="inline-block mt-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                    {signal.severity}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
