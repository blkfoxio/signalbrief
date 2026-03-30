export interface User {
  id: string
  email: string
  username: string
  first_name: string
  last_name: string
  avatar_url: string
}

export interface AuthResponse {
  access_token: string
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
  source: string
  signal_type: string
  value: Record<string, unknown>
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
}

// 3-finding correlated report structure

export interface FindingSummary {
  summary: string
  talk_track: string
}

export interface RemediationItem {
  priority: number
  title: string
  category: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  evidence: string[]
  sources: string[]
}

export interface CorrelatedFindings {
  credential_exposure: {
    severity: string
    total_emails_exposed: number
    confirmed_passwords: number
    stealer_log_hits: number
    stealer_log_total: number
    market_credentials: number
    breach_count: number
    breach_names: string[]
    repeated_exposures: number
    days_since_breach: number | null
    total_exposed_credentials: number
    evidence: string[]
    sources: string[]
  }
  attack_surface: {
    severity: string
    exposed_ports: number[]
    high_risk_services: Record<string, string>
    cves: string[]
    subdomain_count: number
    subdomain_sample: string[]
    dns_issues: string[]
    tech_count: number
    security_tools: string[]
    missing_defenses: string[]
    evidence: string[]
    sources: string[]
  }
  remediation_priorities: RemediationItem[]
}

export interface NarrativeOutput {
  headline: string
  executive_brief: string
  findings: {
    credential_exposure: FindingSummary
    attack_surface: FindingSummary
    remediation: FindingSummary
  }
  correlated_data: CorrelatedFindings
  transition: string
}

export interface OsintSource {
  source: string
  result_count: number
  query_value: string
  queried_at: string
  error_message: string
}

export interface OsintRawData {
  source: string
  result_count: number
  query_value: string
  queried_at: string
  data: Record<string, unknown>
}

export interface Report {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  company: CompanySnapshot
  signals: SecuritySignal[]
  narrative: NarrativeOutput | null
  osint_sources: OsintSource[]
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
