import type { AuthResponse, AuditData, Report, ReportInput } from '@/types'
import client from './client'

// Auth
export async function getLoginUrl(): Promise<string> {
  const res = await client.get<{ auth_url: string }>('/auth/login/')
  return res.data.auth_url
}

export async function exchangeOAuthCode(code: string, state: string): Promise<AuthResponse> {
  const res = await client.post<AuthResponse>('/auth/callback/', { code, state })
  return res.data
}

export async function devRegister(email: string, password: string): Promise<AuthResponse> {
  const res = await client.post<AuthResponse>('/auth/dev/register/', { email, password })
  return res.data
}

export async function devLogin(email: string, password: string): Promise<AuthResponse> {
  const res = await client.post<AuthResponse>('/auth/dev/login/', { email, password })
  return res.data
}

export async function getMe() {
  const res = await client.get('/auth/me/')
  return res.data
}

// Reports
export async function createReport(input: ReportInput): Promise<Report> {
  const res = await client.post<Report>('/reports/', input)
  return res.data
}

export async function listReports(): Promise<Report[]> {
  const res = await client.get<Report[]>('/reports/')
  return res.data
}

export async function getReport(id: string): Promise<Report> {
  const res = await client.get<Report>(`/reports/${id}/`)
  return res.data
}

export async function getAuditData(id: string): Promise<AuditData> {
  const res = await client.get<AuditData>(`/reports/${id}/raw/`)
  return res.data
}

export async function deleteReport(id: string): Promise<void> {
  await client.delete(`/reports/${id}/`)
}

export async function rerunReport(id: string): Promise<Report> {
  const res = await client.post<Report>(`/reports/${id}/rerun/`)
  return res.data
}
