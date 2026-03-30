import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Trash2, Loader2 } from 'lucide-react'
import { useReport } from '@/hooks/useReport'
import { CompanySnapshot } from '@/components/CompanySnapshot'
import { RiskOverview } from '@/components/RiskOverview'
import { FindingCards } from '@/components/FindingCards'
import { AuditPanel } from '@/components/AuditPanel'
import { LoadingState } from '@/components/LoadingState'

export function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentReport, auditData, isLoading, fetchReport, fetchAuditData, rerunReport, removeReport } = useReport()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    if (id) fetchReport(id)
  }, [id, fetchReport])

  const handleRerun = async () => {
    if (!id) return
    setActionLoading(true)
    try {
      const newReport = await rerunReport(id)
      navigate(`/reports/${newReport.id}`)
    } catch {
      // error handled by hook
    } finally {
      setActionLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!id) return
    setActionLoading(true)
    try {
      await removeReport(id)
      navigate('/')
    } catch {
      // error handled by hook
    } finally {
      setActionLoading(false)
      setConfirmDelete(false)
    }
  }

  if (isLoading || !currentReport) {
    return <LoadingState />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-blue-600 no-underline">
          <ArrowLeft className="w-4 h-4" />
          Back to reports
        </Link>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRerun}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 cursor-pointer"
            title="Rerun analysis"
          >
            {actionLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Rerun
          </button>
          {confirmDelete ? (
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleDelete}
                disabled={actionLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 cursor-pointer"
              >
                Confirm
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-3 py-1.5 text-sm text-slate-500 border border-slate-300 rounded-lg hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 cursor-pointer"
              title="Delete report"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete
            </button>
          )}
        </div>
      </div>

      <CompanySnapshot company={currentReport.company} />

      {/* Headline + Executive Brief */}
      {currentReport.narrative && (
        <RiskOverview
          narrative={currentReport.narrative}
          osintSources={currentReport.osint_sources || []}
        />
      )}

      {/* 3 Correlated Finding Cards */}
      {currentReport.narrative && (
        <FindingCards narrative={currentReport.narrative} />
      )}

      {/* Transition to solution */}
      {currentReport.narrative?.transition && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800 italic">{currentReport.narrative.transition}</p>
        </div>
      )}

      {currentReport.status === 'failed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-700">
            Analysis failed. The structured findings above may still be useful.
          </p>
        </div>
      )}

      <AuditPanel
        reportId={currentReport.id}
        auditData={auditData}
        osintSources={currentReport.osint_sources || []}
        onLoadAuditData={fetchAuditData}
      />
    </div>
  )
}
