import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react'
import { getAdminReports } from '@/api/endpoints'
import type { AdminReportsPage as Page } from '@/types'

const STATUS_FILTERS: Array<{ value: string; label: string }> = [
  { value: '', label: 'All' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'processing', label: 'Processing' },
  { value: 'pending', label: 'Pending' },
]

const STATUS_BADGE: Record<string, string> = {
  completed: 'bg-emerald-50 text-emerald-700',
  failed: 'bg-red-50 text-red-700',
  processing: 'bg-blue-50 text-blue-700',
  pending: 'bg-slate-100 text-slate-600',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  return `${(seconds / 60).toFixed(1)}m`
}

export function AdminReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') || ''
  const page = parseInt(searchParams.get('page') || '1', 10) || 1

  const [data, setData] = useState<Page | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    setIsLoading(true)
    getAdminReports(page, status || undefined)
      .then((res) => mounted && setData(res))
      .catch((e) => mounted && setError(e?.message || 'Failed to load reports'))
      .finally(() => mounted && setIsLoading(false))
    return () => {
      mounted = false
    }
  }, [page, status])

  const setStatus = (next: string) => {
    const params: Record<string, string> = {}
    if (next) params.status = next
    setSearchParams(params)
  }

  const setPage = (next: number) => {
    const params: Record<string, string> = { page: String(next) }
    if (status) params.status = status
    setSearchParams(params)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/admin" className="text-sm text-slate-500 hover:text-blue-600 inline-flex items-center gap-1 no-underline">
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <h1 className="text-xl font-bold text-slate-900">Reports</h1>
        </div>
        {data && <span className="text-xs text-slate-500">{data.total.toLocaleString()} total</span>}
      </div>

      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((f) => {
          const active = (f.value || '') === status
          return (
            <button
              key={f.value || 'all'}
              onClick={() => setStatus(f.value)}
              className={`text-xs px-3 py-1 rounded-full border ${
                active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {f.label}
            </button>
          )
        })}
      </div>

      {isLoading && !data ? (
        <div className="text-center py-12 text-sm text-slate-500">Loading…</div>
      ) : error ? (
        <div className="text-center py-12 text-sm text-red-600">{error}</div>
      ) : !data ? null : (
        <>
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Domain</th>
                  <th className="text-left px-4 py-2 font-medium">Status</th>
                  <th className="text-left px-4 py-2 font-medium">User</th>
                  <th className="text-right px-4 py-2 font-medium">Duration</th>
                  <th className="text-left px-4 py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-sm text-slate-400" colSpan={5}>No reports.</td>
                  </tr>
                ) : (
                  data.results.map((r) => (
                    <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2 font-medium">
                        <Link to={`/reports/${r.id}`} className="text-blue-600 hover:underline">
                          {r.domain || '—'}
                        </Link>
                      </td>
                      <td className="px-4 py-2">
                        <span className={`text-xs px-2 py-0.5 rounded ${STATUS_BADGE[r.status] || 'bg-slate-100 text-slate-600'}`}>
                          {r.status}
                        </span>
                        {r.status === 'failed' && r.error_message && (
                          <span className="ml-2 text-xs text-red-600 truncate inline-block max-w-xs align-middle" title={r.error_message}>
                            {r.error_message}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-slate-600">{r.user_email || '—'}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-slate-600">{formatDuration(r.duration_seconds)}</td>
                      <td className="px-4 py-2 text-slate-500 text-xs">{formatDate(r.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <Pagination page={data.page} totalPages={data.total_pages} onChange={setPage} />
        </>
      )}
    </div>
  )
}

function Pagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (p: number) => void }) {
  if (totalPages <= 1) return null
  return (
    <div className="flex items-center justify-end gap-2 text-sm">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="px-2 py-1 border border-slate-200 rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 inline-flex items-center gap-1"
      >
        <ChevronLeft className="w-4 h-4" />
        Prev
      </button>
      <span className="text-slate-500">
        Page {page} of {totalPages}
      </span>
      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="px-2 py-1 border border-slate-200 rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 inline-flex items-center gap-1"
      >
        Next
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  )
}
