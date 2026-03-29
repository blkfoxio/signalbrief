import { useNavigate } from 'react-router-dom'
import { InputForm } from '@/components/InputForm'
import { LoadingState } from '@/components/LoadingState'
import { useReport } from '@/hooks/useReport'
import type { ReportInput } from '@/types'

export function NewReportPage() {
  const { isLoading, error, submitReport, setError } = useReport()
  const navigate = useNavigate()

  const handleSubmit = async (input: ReportInput) => {
    try {
      const report = await submitReport(input)
      navigate(`/reports/${report.id}`)
    } catch {
      // Error is already set by the hook
    }
  }

  if (isLoading) {
    return <LoadingState />
  }

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-900">New Security Brief</h1>
        <p className="text-sm text-slate-500 mt-1">
          Enter what you know about the prospect. Domain gives the best results.
        </p>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <InputForm onSubmit={handleSubmit} isLoading={isLoading} />
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-xs text-red-500 hover:underline mt-1 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
