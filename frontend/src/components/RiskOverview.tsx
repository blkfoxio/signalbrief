import { useState } from 'react'
import { ShieldAlert, Copy, Check, AlertTriangle, TrendingUp, ListChecks } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { NarrativeOutput, OsintSource, Posture } from '@/types'

const SOURCE_DISPLAY: Record<string, string> = {
  dehashed: 'DeHashed',
  hibp: 'HIBP',
  leakcheck: 'LeakCheck',
  shodan: 'Shodan',
  censys: 'Censys',
  securitytrails: 'SecurityTrails',
  builtwith: 'BuiltWith',
}

const POSTURE_BADGE: Record<Posture, string> = {
  low: 'bg-green-100 text-green-800',
  moderate: 'bg-yellow-100 text-yellow-800',
  elevated: 'bg-orange-100 text-orange-800',
  high: 'bg-red-100 text-red-800',
}

interface RiskOverviewProps {
  narrative: NarrativeOutput
  osintSources: OsintSource[]
}

export function RiskOverview({ narrative, osintSources }: RiskOverviewProps) {
  const [copied, setCopied] = useState(false)
  const activeSources = osintSources.filter(s => !s.error_message)
  const posture = narrative.correlated_data?.posture
  const summary = narrative.executive_summary
  const hasStructuredSummary = !!(
    summary && (
      (summary.key_risks && summary.key_risks.length > 0) ||
      summary.business_impact ||
      (summary.top_actions && summary.top_actions.length > 0)
    )
  )

  const copyText = hasStructuredSummary && summary
    ? [
        summary.key_risks?.length ? `Key risks:\n- ${summary.key_risks.join('\n- ')}` : '',
        summary.business_impact ? `\nWhat this means:\n${summary.business_impact}` : '',
        summary.top_actions?.length ? `\nTop actions:\n- ${summary.top_actions.join('\n- ')}` : '',
      ].filter(Boolean).join('\n')
    : narrative.executive_brief

  const handleCopy = async () => {
    await navigator.clipboard.writeText(copyText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5">
      <div className="flex items-start gap-3 mb-3">
        <ShieldAlert className="w-6 h-6 text-slate-600 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-base font-semibold text-slate-900">{narrative.headline}</h2>
            {posture && (
              <span className={cn(
                'px-2.5 py-0.5 text-xs font-semibold uppercase rounded-full shrink-0',
                POSTURE_BADGE[posture] || POSTURE_BADGE.low,
              )}>
                {posture} posture
              </span>
            )}
          </div>
        </div>
        {(hasStructuredSummary || narrative.executive_brief) && (
          <button
            onClick={handleCopy}
            className="text-slate-400 hover:text-blue-600 cursor-pointer p-2 shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center"
            title="Copy executive summary"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      {hasStructuredSummary && summary ? (
        <div className="space-y-3">
          {summary.key_risks && summary.key_risks.length > 0 && (
            <div className="bg-slate-50 rounded-md p-3">
              <div className="flex items-center gap-1.5 mb-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-slate-500" />
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Key risks</p>
              </div>
              <ul className="space-y-1">
                {summary.key_risks.map((risk, i) => (
                  <li key={i} className="text-sm text-slate-700 flex gap-1.5">
                    <span className="text-slate-400">•</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.business_impact && (
            <div className="bg-slate-50 rounded-md p-3">
              <div className="flex items-center gap-1.5 mb-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-slate-500" />
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">What this means</p>
              </div>
              <p className="text-sm text-slate-700 leading-relaxed">{summary.business_impact}</p>
            </div>
          )}

          {summary.top_actions && summary.top_actions.length > 0 && (
            <div className="bg-slate-50 rounded-md p-3">
              <div className="flex items-center gap-1.5 mb-1.5">
                <ListChecks className="w-3.5 h-3.5 text-slate-500" />
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Top actions</p>
              </div>
              <ul className="space-y-1">
                {summary.top_actions.map((action, i) => (
                  <li key={i} className="text-sm text-slate-700 flex gap-1.5">
                    <span className="text-slate-400">•</span>
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : narrative.executive_brief ? (
        <div className="bg-slate-50 rounded-lg p-3 sm:p-4">
          <p className="text-sm text-slate-700 leading-relaxed">{narrative.executive_brief}</p>
        </div>
      ) : null}

      {activeSources.length > 0 && (
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <span className="text-xs text-slate-400">Sources:</span>
          {activeSources.map(source => (
            <span
              key={source.source}
              className="inline-flex items-center px-2 py-0.5 text-xs text-slate-600 bg-slate-100 rounded"
            >
              {SOURCE_DISPLAY[source.source] || source.source}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
