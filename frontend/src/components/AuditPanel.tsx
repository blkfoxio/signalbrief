import { useState } from 'react'
import { ChevronDown, ChevronRight, Database } from 'lucide-react'
import type { AuditData, AuditEntry } from '@/types'

interface AuditPanelProps {
  reportId: string
  auditData: AuditData | null
  onLoadAuditData: (id: string) => void
}

export function AuditPanel({ reportId, auditData, onLoadAuditData }: AuditPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [page, setPage] = useState(0)
  const pageSize = 25

  const handleToggle = () => {
    if (!isOpen && !auditData) {
      onLoadAuditData(reportId)
    }
    setIsOpen(!isOpen)
  }

  const entries = auditData?.entries ?? []
  const totalPages = Math.ceil(entries.length / pageSize)
  const pageEntries = entries.slice(page * pageSize, (page + 1) * pageSize)

  return (
    <div className="bg-white rounded-lg border border-slate-200">
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-50 cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-700">View Underlying Data</span>
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
      </button>

      {isOpen && auditData && (
        <div className="border-t border-slate-200 p-4">
          {/* Summary header */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="bg-slate-50 rounded p-3">
              <p className="text-xs text-slate-500">Total Records</p>
              <p className="text-lg font-semibold text-slate-900">{auditData.result_count}</p>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <p className="text-xs text-slate-500">Unique Emails</p>
              <p className="text-lg font-semibold text-slate-900">{auditData.unique_emails}</p>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <p className="text-xs text-slate-500">Breach Sources</p>
              <p className="text-lg font-semibold text-slate-900">{auditData.breach_sources}</p>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <p className="text-xs text-slate-500">Queried At</p>
              <p className="text-sm font-medium text-slate-900">
                {new Date(auditData.queried_at).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Data table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Email</th>
                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Source</th>
                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Username</th>
                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Password</th>
                </tr>
              </thead>
              <tbody>
                {pageEntries.map((entry: AuditEntry, i: number) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 px-3 text-slate-700 font-mono text-xs">
                      {(entry.email ?? []).join(', ') || '-'}
                    </td>
                    <td className="py-2 px-3 text-slate-700 text-xs">
                      {entry.database_name || '-'}
                    </td>
                    <td className="py-2 px-3 text-slate-700 font-mono text-xs">
                      {(entry.username ?? []).join(', ') || '-'}
                    </td>
                    <td className="py-2 px-3 text-xs">
                      {entry.password_exposed ? (
                        <span className="text-red-600 font-medium">Exposed</span>
                      ) : (
                        <span className="text-slate-400">No</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
              <span className="text-xs text-slate-500">
                Page {page + 1} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="px-3 py-1 text-xs border border-slate-300 rounded disabled:opacity-50 cursor-pointer"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-3 py-1 text-xs border border-slate-300 rounded disabled:opacity-50 cursor-pointer"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
