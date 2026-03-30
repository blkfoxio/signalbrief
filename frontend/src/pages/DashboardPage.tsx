import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, FileText, AlertTriangle, Trash2 } from 'lucide-react'
import { useReport } from '@/hooks/useReport'
import { cn } from '@/lib/utils'

const SEVERITY_DOT: Record<string, string> = {
  low: 'bg-slate-400',
  medium: 'bg-yellow-400',
  high: 'bg-orange-400',
  critical: 'bg-red-400',
}

export function DashboardPage() {
  const { reports, isLoading, fetchReports, removeReport } = useReport()

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault()
    e.stopPropagation()
    if (!window.confirm('Delete this report?')) return
    try {
      await removeReport(id)
    } catch {
      // error handled by hook
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-slate-900">Reports</h1>
        <Link
          to="/new"
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 no-underline"
        >
          <Plus className="w-4 h-4" />
          New Report
        </Link>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-sm text-slate-500">Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg border border-slate-200">
          <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500 mb-4">No reports yet. Generate your first security brief.</p>
          <Link
            to="/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 no-underline"
          >
            <Plus className="w-4 h-4" />
            New Report
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {reports.map((report) => {
            const topSignal = report.signals?.reduce<{ severity: string } | null>(
              (top, s) => {
                const order = ['low', 'medium', 'high', 'critical']
                if (!top || order.indexOf(s.severity) > order.indexOf(top.severity)) return s
                return top
              },
              null
            )

            return (
              <Link
                key={report.id}
                to={`/reports/${report.id}`}
                className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between p-4 bg-white rounded-lg border border-slate-200 hover:border-blue-300 hover:shadow-sm transition-all no-underline"
              >
                <div className="flex items-center gap-3">
                  {topSignal && (
                    <div className={cn('w-2 h-2 rounded-full', SEVERITY_DOT[topSignal.severity])} />
                  )}
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {report.company?.name || report.company?.domain}
                    </p>
                    <p className="text-xs text-slate-400">{report.company?.domain}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 pl-5 sm:pl-0">
                  <div className="flex items-center gap-1 text-xs text-slate-400">
                    <AlertTriangle className="w-3 h-3" />
                    {report.signals?.length || 0} signals
                  </div>
                  <span className="text-xs text-slate-400">
                    {new Date(report.created_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={(e) => handleDelete(e, report.id)}
                    className="text-slate-300 hover:text-red-500 transition-colors cursor-pointer p-2 -mr-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
                    title="Delete report"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
