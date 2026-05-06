import { useEffect, useState } from 'react'
import { AlertTriangle, Users, FileText, Activity, Clock } from 'lucide-react'
import {
  getMetricsOverview,
  getMetricsRecentFailures,
  getMetricsSources,
} from '@/api/endpoints'
import type {
  MetricsOverview,
  MetricsRecentFailures,
  MetricsSources,
} from '@/types'

function Sparkline({ data }: { data: Array<{ date: string; count: number }> }) {
  if (!data.length) return null
  const max = Math.max(1, ...data.map((d) => d.count))
  const w = 240
  const h = 40
  const step = w / Math.max(1, data.length - 1)
  const pts = data
    .map((d, i) => `${(i * step).toFixed(1)},${(h - (d.count / max) * h).toFixed(1)}`)
    .join(' ')
  return (
    <svg width={w} height={h} className="text-blue-500">
      <polyline fill="none" stroke="currentColor" strokeWidth="1.5" points={pts} />
    </svg>
  )
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  return `${(seconds / 60).toFixed(1)}m`
}

function formatPct(rate: number | null): string {
  if (rate == null) return '—'
  return `${(rate * 100).toFixed(1)}%`
}

function rateColor(rate: number | null): string {
  if (rate == null) return 'bg-slate-200'
  if (rate >= 0.95) return 'bg-emerald-500'
  if (rate >= 0.8) return 'bg-yellow-500'
  return 'bg-red-500'
}

export function AdminPage() {
  const [overview, setOverview] = useState<MetricsOverview | null>(null)
  const [sources, setSources] = useState<MetricsSources | null>(null)
  const [failures, setFailures] = useState<MetricsRecentFailures | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    Promise.all([getMetricsOverview(), getMetricsSources(), getMetricsRecentFailures()])
      .then(([o, s, f]) => {
        if (!mounted) return
        setOverview(o)
        setSources(s)
        setFailures(f)
      })
      .catch((e) => mounted && setError(e?.message || 'Failed to load metrics'))
      .finally(() => mounted && setIsLoading(false))
    return () => {
      mounted = false
    }
  }, [])

  if (isLoading) {
    return <div className="text-center py-12 text-sm text-slate-500">Loading metrics…</div>
  }
  if (error) {
    return <div className="text-center py-12 text-sm text-red-600">{error}</div>
  }
  if (!overview || !sources || !failures) return null

  const kpis = [
    {
      label: 'Total users',
      value: overview.users.total.toLocaleString(),
      sub: `+${overview.users.last_7d} in last 7d`,
      icon: Users,
    },
    {
      label: 'Reports (7d)',
      value: overview.reports.last_7d.toLocaleString(),
      sub: `${overview.reports.total.toLocaleString()} all-time`,
      icon: FileText,
    },
    {
      label: 'Pipeline success (30d)',
      value: formatPct(overview.reports.success_rate_30d),
      sub: `${overview.reports.by_status.failed || 0} failed / ${overview.reports.by_status.completed || 0} completed`,
      icon: Activity,
    },
    {
      label: 'Avg duration (30d)',
      value: formatDuration(overview.reports.avg_duration_seconds_30d),
      sub: 'completed analyses',
      icon: Clock,
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">Operator Dashboard</h1>
        <span className="text-xs text-slate-400">
          Updated {new Date(overview.generated_at).toLocaleString()}
        </span>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {kpis.map((k) => {
          const Icon = k.icon
          return (
            <div key={k.label} className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">{k.label}</span>
                <Icon className="w-4 h-4 text-slate-400" />
              </div>
              <div className="text-2xl font-semibold text-slate-900">{k.value}</div>
              <div className="text-xs text-slate-500 mt-1">{k.sub}</div>
            </div>
          )
        })}
      </div>

      {/* Sparklines */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs text-slate-500 mb-2">Reports per day (30d)</div>
          <Sparkline data={overview.daily_reports_30d} />
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs text-slate-500 mb-2">Signups per day (30d)</div>
          <Sparkline data={overview.daily_signups_30d} />
        </div>
      </div>

      {/* Source health */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200">
          <h2 className="text-sm font-semibold text-slate-900">Third-party data source health (30d)</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Source</th>
              <th className="text-right px-4 py-2 font-medium">Calls</th>
              <th className="text-right px-4 py-2 font-medium">Errors</th>
              <th className="text-left px-4 py-2 font-medium">Success rate</th>
              <th className="text-left px-4 py-2 font-medium">Last error</th>
            </tr>
          </thead>
          <tbody>
            {sources.sources.map((row) => (
              <tr key={row.source} className="border-t border-slate-100">
                <td className="px-4 py-2 font-medium text-slate-700">{row.label}</td>
                <td className="px-4 py-2 text-right text-slate-600">{row.total_calls_30d}</td>
                <td className="px-4 py-2 text-right text-slate-600">{row.error_count_30d}</td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${rateColor(row.success_rate)}`}
                        style={{ width: row.success_rate == null ? '0%' : `${row.success_rate * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-600 tabular-nums">{formatPct(row.success_rate)}</span>
                  </div>
                </td>
                <td className="px-4 py-2 text-xs text-slate-500 max-w-xs truncate" title={row.last_error_message || ''}>
                  {row.last_error_message ? (
                    <span>
                      {row.last_error_at && (
                        <span className="text-slate-400 mr-1">{new Date(row.last_error_at).toLocaleDateString()}:</span>
                      )}
                      {row.last_error_message}
                    </span>
                  ) : (
                    <span className="text-slate-300">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Recent failures */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="bg-white rounded-lg border border-slate-200">
          <div className="px-4 py-3 border-b border-slate-200 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <h2 className="text-sm font-semibold text-slate-900">Recent failed analyses</h2>
          </div>
          {failures.analyses.length === 0 ? (
            <div className="px-4 py-6 text-sm text-slate-400">No failures.</div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {failures.analyses.map((a) => (
                <li key={a.id} className="px-4 py-3">
                  <div className="flex justify-between items-baseline gap-2">
                    <span className="text-sm font-medium text-slate-700">{a.domain || '—'}</span>
                    <span className="text-xs text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
                  </div>
                  {a.user_email && <div className="text-xs text-slate-500">{a.user_email}</div>}
                  {a.error_message && <div className="text-xs text-red-600 mt-1">{a.error_message}</div>}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-lg border border-slate-200">
          <div className="px-4 py-3 border-b border-slate-200 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-orange-500" />
            <h2 className="text-sm font-semibold text-slate-900">Recent OSINT call errors</h2>
          </div>
          {failures.osint_calls.length === 0 ? (
            <div className="px-4 py-6 text-sm text-slate-400">No errors.</div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {failures.osint_calls.map((o, i) => (
                <li key={`${o.analysis_id}-${o.source}-${i}`} className="px-4 py-3">
                  <div className="flex justify-between items-baseline gap-2">
                    <span className="text-sm font-medium text-slate-700">
                      {o.source} <span className="text-slate-400 font-normal">· {o.domain || o.query_value}</span>
                    </span>
                    <span className="text-xs text-slate-400">{new Date(o.queried_at).toLocaleString()}</span>
                  </div>
                  <div className="text-xs text-red-600 mt-1">{o.error_message}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
