import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, ChevronLeft, ChevronRight, ShieldCheck } from 'lucide-react'
import { getAdminUsers } from '@/api/endpoints'
import type { AdminUsersPage as Page } from '@/types'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

export function AdminUsersPage() {
  const [page, setPage] = useState(1)
  const [data, setData] = useState<Page | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    setIsLoading(true)
    getAdminUsers(page)
      .then((res) => mounted && setData(res))
      .catch((e) => mounted && setError(e?.message || 'Failed to load users'))
      .finally(() => mounted && setIsLoading(false))
    return () => {
      mounted = false
    }
  }, [page])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/admin" className="text-sm text-slate-500 hover:text-blue-600 inline-flex items-center gap-1 no-underline">
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <h1 className="text-xl font-bold text-slate-900">Users</h1>
        </div>
        {data && <span className="text-xs text-slate-500">{data.total.toLocaleString()} total</span>}
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
                  <th className="text-left px-4 py-2 font-medium">Email</th>
                  <th className="text-left px-4 py-2 font-medium">Name</th>
                  <th className="text-left px-4 py-2 font-medium">Signed up</th>
                  <th className="text-left px-4 py-2 font-medium">Last login</th>
                  <th className="text-right px-4 py-2 font-medium">Reports</th>
                  <th className="text-left px-4 py-2 font-medium">Role</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-sm text-slate-400" colSpan={6}>No users.</td>
                  </tr>
                ) : (
                  data.results.map((u) => (
                    <tr key={u.id} className="border-t border-slate-100">
                      <td className="px-4 py-2 font-medium text-slate-700">{u.email}</td>
                      <td className="px-4 py-2 text-slate-600">{u.full_name || '—'}</td>
                      <td className="px-4 py-2 text-slate-500 text-xs">{formatDate(u.date_joined)}</td>
                      <td className="px-4 py-2 text-slate-500 text-xs">{formatDate(u.last_login)}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-slate-700">{u.report_count}</td>
                      <td className="px-4 py-2">
                        {u.is_staff ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                            <ShieldCheck className="w-3 h-3" />
                            Staff
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400">User</span>
                        )}
                      </td>
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
