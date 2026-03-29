import { ShieldAlert } from 'lucide-react'
import type { NarrativeOutput, SecuritySignal, OsintSource } from '@/types'

const SEVERITY_ORDER = { critical: 4, high: 3, medium: 2, low: 1 }

function getOverallSeverity(signals: SecuritySignal[]): 'critical' | 'high' | 'medium' | 'low' {
  let maxSeverity: 'critical' | 'high' | 'medium' | 'low' = 'low'
  for (const signal of signals) {
    if (SEVERITY_ORDER[signal.severity] > SEVERITY_ORDER[maxSeverity]) {
      maxSeverity = signal.severity
    }
  }
  return maxSeverity
}

const SEVERITY_BADGE = {
  low: 'bg-slate-100 text-slate-700',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
}

interface RiskOverviewProps {
  narrative: NarrativeOutput
  signals: SecuritySignal[]
  osintSources: OsintSource[]
}

export function RiskOverview({ narrative, signals, osintSources }: RiskOverviewProps) {
  const overallSeverity = getOverallSeverity(signals)
  const activeSources = osintSources.filter(s => s.result_count > 0)

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-start gap-3">
          <ShieldAlert className="w-6 h-6 text-slate-600 mt-0.5 shrink-0" />
          <div>
            <h2 className="text-base font-semibold text-slate-900">{narrative.headline}</h2>
            {narrative.risk_summary && (
              <p className="text-sm text-slate-600 mt-1 leading-relaxed">{narrative.risk_summary}</p>
            )}
          </div>
        </div>
        <span className={`inline-flex items-center px-2.5 py-1 text-xs font-semibold uppercase tracking-wide rounded-full shrink-0 ${SEVERITY_BADGE[overallSeverity]}`}>
          {overallSeverity} risk
        </span>
      </div>

      {/* Source badges */}
      {activeSources.length > 0 && (
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100">
          <span className="text-xs text-slate-400">Sources:</span>
          {activeSources.map(source => (
            <span
              key={source.source}
              className="inline-flex items-center px-2 py-0.5 text-xs text-slate-600 bg-slate-100 rounded"
            >
              {SOURCE_DISPLAY[source.source] || source.source}
              <span className="ml-1 text-slate-400">({source.result_count})</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

const SOURCE_DISPLAY: Record<string, string> = {
  dehashed: 'DeHashed',
  hibp: 'HIBP',
  leakcheck: 'LeakCheck',
  shodan: 'Shodan',
  censys: 'Censys',
  securitytrails: 'SecurityTrails',
  builtwith: 'BuiltWith',
}
