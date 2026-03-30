import { useState } from 'react'
import { ShieldAlert, Copy, Check } from 'lucide-react'
import type { NarrativeOutput, OsintSource } from '@/types'

const SOURCE_DISPLAY: Record<string, string> = {
  dehashed: 'DeHashed',
  hibp: 'HIBP',
  leakcheck: 'LeakCheck',
  shodan: 'Shodan',
  censys: 'Censys',
  securitytrails: 'SecurityTrails',
  builtwith: 'BuiltWith',
}

interface RiskOverviewProps {
  narrative: NarrativeOutput
  osintSources: OsintSource[]
}

export function RiskOverview({ narrative, osintSources }: RiskOverviewProps) {
  const [copied, setCopied] = useState(false)
  const activeSources = osintSources.filter(s => !s.error_message)

  const handleCopyBrief = async () => {
    await navigator.clipboard.writeText(narrative.executive_brief)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5">
      <div className="flex items-start gap-3 mb-3">
        <ShieldAlert className="w-6 h-6 text-slate-600 mt-0.5 shrink-0" />
        <div className="flex-1">
          <h2 className="text-base font-semibold text-slate-900">{narrative.headline}</h2>
        </div>
      </div>

      {narrative.executive_brief && (
        <div className="bg-slate-50 rounded-lg p-3 sm:p-4 mb-3">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm text-slate-700 leading-relaxed">{narrative.executive_brief}</p>
            <button onClick={handleCopyBrief} className="text-slate-400 hover:text-blue-600 cursor-pointer p-2 shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center" title="Copy executive brief">
              {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      )}

      {activeSources.length > 0 && (
        <div className="flex items-center gap-2">
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
