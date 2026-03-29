import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useReport } from '@/hooks/useReport'
import { CompanySnapshot } from '@/components/CompanySnapshot'
import { SignalCards } from '@/components/SignalCards'
import { NarrativeView } from '@/components/NarrativeView'
import { AuditPanel } from '@/components/AuditPanel'
import { LoadingState } from '@/components/LoadingState'

export function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const { currentReport, auditData, isLoading, fetchReport, fetchAuditData } = useReport()

  useEffect(() => {
    if (id) fetchReport(id)
  }, [id, fetchReport])

  if (isLoading || !currentReport) {
    return <LoadingState />
  }

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-blue-600 no-underline">
        <ArrowLeft className="w-4 h-4" />
        Back to reports
      </Link>

      <CompanySnapshot company={currentReport.company} />

      <SignalCards signals={currentReport.signals} />

      {currentReport.narrative && (
        <NarrativeView narrative={currentReport.narrative} />
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
        onLoadAuditData={fetchAuditData}
      />
    </div>
  )
}
