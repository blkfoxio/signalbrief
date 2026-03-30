import { useState } from 'react'
import { KeyRound, Globe, Target, ChevronDown, ChevronRight, Copy, Check, ShieldAlert } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { NarrativeOutput, CorrelatedFindings, RemediationItem } from '@/types'

const SEVERITY_BADGE: Record<string, string> = {
  low: 'bg-slate-100 text-slate-700',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
}

const SEVERITY_BORDER: Record<string, string> = {
  low: 'border-l-slate-400',
  medium: 'border-l-yellow-400',
  high: 'border-l-orange-400',
  critical: 'border-l-red-400',
}

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={handleCopy} className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-blue-600 cursor-pointer px-2 py-1 rounded hover:bg-slate-50 min-h-[44px]">
      {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
      {label || 'Copy talk track'}
    </button>
  )
}

interface FindingCardsProps {
  narrative: NarrativeOutput
}

const EMPTY_FINDING = { summary: '', talk_track: '' }

const EMPTY_CRED: CorrelatedFindings['credential_exposure'] = {
  severity: 'low', total_emails_exposed: 0, confirmed_passwords: 0,
  stealer_log_hits: 0, stealer_log_total: 0, market_credentials: 0,
  breach_count: 0, breach_names: [], repeated_exposures: 0,
  days_since_breach: null, total_exposed_credentials: 0, evidence: [], sources: [],
}

const EMPTY_SURFACE: CorrelatedFindings['attack_surface'] = {
  severity: 'low', exposed_ports: [], high_risk_services: {}, cves: [],
  subdomain_count: 0, subdomain_sample: [], dns_issues: [], tech_count: 0,
  security_tools: [], missing_defenses: [], evidence: [], sources: [],
}

export function FindingCards({ narrative }: FindingCardsProps) {
  const findings = narrative.findings || {}
  const correlated = narrative.correlated_data

  return (
    <div className="space-y-4">
      <CredentialCard
        finding={findings.credential_exposure || EMPTY_FINDING}
        data={correlated?.credential_exposure || EMPTY_CRED}
      />
      <AttackSurfaceCard
        finding={findings.attack_surface || EMPTY_FINDING}
        data={correlated?.attack_surface || EMPTY_SURFACE}
      />
      <RemediationCard
        finding={findings.remediation || EMPTY_FINDING}
        items={correlated?.remediation_priorities || []}
      />
    </div>
  )
}


function CredentialCard({ finding, data }: {
  finding: { summary: string; talk_track: string }
  data: CorrelatedFindings['credential_exposure']
}) {
  const [expanded, setExpanded] = useState(false)
  const severity = data.severity || 'low'
  const hasFindings = data.total_exposed_credentials > 0 || data.total_emails_exposed > 0
  if (!finding.summary && !hasFindings) return null

  return (
    <div className={cn('bg-white rounded-lg border border-slate-200 border-l-4 overflow-hidden', SEVERITY_BORDER[severity])}>
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">Credential Exposure</h3>
          </div>
          <span className={cn('px-2.5 py-0.5 text-xs font-semibold uppercase rounded-full', SEVERITY_BADGE[severity])}>
            {severity}
          </span>
        </div>

        <p className="text-sm text-slate-700 leading-relaxed mb-3">{finding.summary}</p>

        {/* Evidence tags */}
        {data?.evidence?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {data.evidence.map((e, i) => (
              <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{e}</span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2">
          <CopyButton text={finding.talk_track} />
          {hasFindings && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-blue-600 cursor-pointer px-2 py-1 rounded hover:bg-slate-50 min-h-[44px]"
            >
              {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {expanded ? 'Hide details' : 'Show details'}
            </button>
          )}
        </div>
      </div>

      {expanded && hasFindings && (
        <div className="border-t border-slate-100 bg-slate-50 p-3 sm:p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
            <div>
              <p className="text-lg font-bold text-slate-900">{data.total_emails_exposed}</p>
              <p className="text-xs text-slate-500">Emails exposed</p>
            </div>
            <div>
              <p className="text-lg font-bold text-red-600">{data.confirmed_passwords}</p>
              <p className="text-xs text-slate-500">Passwords exposed</p>
            </div>
            <div>
              <p className="text-lg font-bold text-slate-900">{data.stealer_log_hits}</p>
              <p className="text-xs text-slate-500">Stealer log hits</p>
            </div>
            <div>
              <p className="text-lg font-bold text-slate-900">{data.breach_count}</p>
              <p className="text-xs text-slate-500">Known breaches</p>
            </div>
          </div>
          {data.breach_names?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-200">
              <p className="text-xs text-slate-500 mb-1">Breach sources:</p>
              <div className="flex flex-wrap gap-1">
                {data.breach_names.map(name => (
                  <span key={name} className="text-xs bg-white text-slate-600 px-2 py-0.5 rounded border border-slate-200">{name}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


function AttackSurfaceCard({ finding, data }: {
  finding: { summary: string; talk_track: string }
  data: CorrelatedFindings['attack_surface']
}) {
  const [expanded, setExpanded] = useState(false)
  const severity = data.severity || 'low'
  const hasFindings = data.exposed_ports.length > 0 || data.subdomain_count > 0 || data.missing_defenses.length > 0
  if (!finding.summary && !hasFindings) return null

  return (
    <div className={cn('bg-white rounded-lg border border-slate-200 border-l-4 overflow-hidden', SEVERITY_BORDER[severity])}>
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">Attack Surface</h3>
          </div>
          <span className={cn('px-2.5 py-0.5 text-xs font-semibold uppercase rounded-full', SEVERITY_BADGE[severity])}>
            {severity}
          </span>
        </div>

        <p className="text-sm text-slate-700 leading-relaxed mb-3">{finding.summary}</p>

        {data?.evidence?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {data.evidence.map((e, i) => (
              <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{e}</span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2">
          <CopyButton text={finding.talk_track} />
          {hasFindings && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-blue-600 cursor-pointer px-2 py-1 rounded hover:bg-slate-50 min-h-[44px]"
            >
              {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {expanded ? 'Hide details' : 'Show details'}
            </button>
          )}
        </div>
      </div>

      {expanded && hasFindings && (
        <div className="border-t border-slate-100 bg-slate-50 p-3 sm:p-4 space-y-3">
          {data.exposed_ports?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Open ports</p>
              <div className="flex flex-wrap gap-1.5">
                {data.exposed_ports.map(port => {
                  const isHighRisk = data.high_risk_services && String(port) in data.high_risk_services
                  return (
                    <span key={port} className={cn(
                      'px-2 py-0.5 text-xs font-mono rounded',
                      isHighRisk ? 'bg-red-100 text-red-700' : 'bg-white text-slate-700 border border-slate-200'
                    )}>
                      {port}{isHighRisk ? ` (${data.high_risk_services[String(port)]})` : ''}
                    </span>
                  )
                })}
              </div>
            </div>
          )}

          {data.cves?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Vulnerabilities</p>
              <div className="flex flex-wrap gap-1.5">
                {data.cves.map(cve => (
                  <span key={cve} className="px-2 py-0.5 text-xs font-mono bg-red-50 text-red-700 rounded">{cve}</span>
                ))}
              </div>
            </div>
          )}

          {data.subdomain_count > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">{data.subdomain_count} subdomains</p>
              <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                {data.subdomain_sample?.map(sub => (
                  <span key={sub} className="px-2 py-0.5 text-xs font-mono bg-white text-slate-600 rounded border border-slate-200">{sub}</span>
                ))}
                {data.subdomain_count > (data.subdomain_sample?.length || 0) && (
                  <span className="text-xs text-slate-400">+{data.subdomain_count - (data.subdomain_sample?.length || 0)} more</span>
                )}
              </div>
            </div>
          )}

          {data.missing_defenses?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Missing defenses</p>
              {data.missing_defenses.map(d => (
                <div key={d} className="flex items-center gap-1.5 text-xs text-orange-700">
                  <ShieldAlert className="w-3 h-3" /> {d}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}


function RemediationCard({ finding, items }: {
  finding: { summary: string; talk_track: string }
  items: RemediationItem[]
}) {
  const topSeverity = items[0]?.severity || 'low'

  return (
    <div className={cn('bg-white rounded-lg border border-slate-200 border-l-4 overflow-hidden', SEVERITY_BORDER[topSeverity])}>
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">Remediation Priorities</h3>
          </div>
          <span className="text-xs text-slate-400">{items.length} items</span>
        </div>

        <p className="text-sm text-slate-700 leading-relaxed mb-3">{finding.summary}</p>

        {/* Priority list */}
        <div className="space-y-2 mb-3">
          {items.map((item) => (
            <div key={item.priority} className="flex items-start gap-3 py-2 border-b border-slate-100 last:border-b-0">
              <span className="text-xs font-bold text-slate-400 mt-0.5 w-4 shrink-0">{item.priority}.</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-slate-800">{item.title}</p>
                {item.evidence.length > 0 && (
                  <p className="text-xs text-slate-500 mt-0.5">{item.evidence.join(' | ')}</p>
                )}
              </div>
              <span className={cn('px-2 py-0.5 text-xs font-semibold uppercase rounded-full shrink-0', SEVERITY_BADGE[item.severity])}>
                {item.severity}
              </span>
            </div>
          ))}
        </div>

        <CopyButton text={finding.talk_track} />
      </div>
    </div>
  )
}
