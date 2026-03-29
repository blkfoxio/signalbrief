import { useCallback, useState } from 'react'
import { createReport, deleteReport as deleteReportApi, rerunReport as rerunReportApi, getAuditData, getReport, listReports } from '@/api/endpoints'
import type { AuditData, Report, ReportInput } from '@/types'

export function useReport() {
  const [reports, setReports] = useState<Report[]>([])
  const [currentReport, setCurrentReport] = useState<Report | null>(null)
  const [auditData, setAuditData] = useState<AuditData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submitReport = useCallback(async (input: ReportInput) => {
    setIsLoading(true)
    setError(null)
    try {
      const report = await createReport(input)
      setCurrentReport(report)
      return report
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create report'
      setError(message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const fetchReports = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await listReports()
      setReports(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch reports'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const fetchReport = useCallback(async (id: string) => {
    setIsLoading(true)
    try {
      const data = await getReport(id)
      setCurrentReport(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch report'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const fetchAuditData = useCallback(async (id: string) => {
    try {
      const data = await getAuditData(id)
      setAuditData(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch audit data'
      setError(message)
    }
  }, [])

  const removeReport = useCallback(async (id: string) => {
    try {
      await deleteReportApi(id)
      setReports((prev) => prev.filter((r) => r.id !== id))
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete report'
      setError(message)
      throw err
    }
  }, [])

  const rerunReport = useCallback(async (id: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const report = await rerunReportApi(id)
      setCurrentReport(report)
      return report
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to rerun report'
      setError(message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    reports,
    currentReport,
    auditData,
    isLoading,
    error,
    submitReport,
    fetchReports,
    fetchReport,
    fetchAuditData,
    removeReport,
    rerunReport,
    setError,
  }
}
