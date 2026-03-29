export interface User {
  id: string
  email: string
  username: string
  first_name: string
  last_name: string
  avatar_url: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
}

export interface AuthResponse extends AuthTokens {
  user: User
}

export interface CompanySnapshot {
  domain: string
  name: string
  industry: string
  employee_range: string
  description: string
}

export interface SecuritySignal {
  signal_type: string
  value: Record<string, unknown>
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
}

export interface NarrativeOutput {
  headline: string
  executive_narrative: string
  talk_track: string
  business_impact: string
  transition: string
}

export interface Report {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  company: CompanySnapshot
  signals: SecuritySignal[]
  narrative: NarrativeOutput | null
  created_at: string
}

export interface ReportInput {
  domain: string
  company_name: string
  linkedin_url: string
  contact_email: string
}

export interface AuditEntry {
  email?: string[]
  username?: string[]
  password?: string[]
  password_exposed?: boolean
  hashed_password?: string[]
  ip_address?: string[]
  database_name?: string
  name?: string[]
  [key: string]: unknown
}

export interface AuditData {
  query_domain: string
  query_email: string
  result_count: number
  unique_emails: number
  breach_sources: number
  queried_at: string
  entries: AuditEntry[]
}
