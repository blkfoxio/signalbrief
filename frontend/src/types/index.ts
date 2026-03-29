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
  source: string
  signal_type: string
  value: Record<string, unknown>
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
}

export interface CategoryFindings {
  breach_intelligence?: string
  infrastructure_exposure?: string
  attack_surface?: string
  technology_footprint?: string
}

export interface NarrativeOutput {
  headline: string
  risk_summary: string
  category_findings: CategoryFindings
  executive_narrative: string
  talk_track: string
  business_impact: string
  transition: string
}

export interface OsintSource {
  source: string
  result_count: number
  query_value: string
  queried_at: string
  error_message: string
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

export interface OsintRawData {
  source: string
  result_count: number
  query_value: string
  queried_at: string
  data: Record<string, unknown>
}

// Signal category mapping
export type SignalCategory = 'breach_intelligence' | 'infrastructure_exposure' | 'attack_surface' | 'technology_footprint'

export const SIGNAL_CATEGORIES: Record<SignalCategory, string[]> = {
  breach_intelligence: [
    'employee_emails_exposed', 'breach_events', 'password_exposure',
    'repeated_identity_exposure', 'stealer_log_exposure',
    'credential_market_presence', 'known_breaches', 'breach_recency',
    'sensitive_breach_exposure',
  ],
  infrastructure_exposure: [
    'exposed_services', 'known_vulnerabilities', 'outdated_software',
    'expired_certificates', 'weak_encryption', 'certificate_transparency',
  ],
  attack_surface: [
    'subdomain_count', 'dns_misconfigurations', 'historical_dns_changes',
  ],
  technology_footprint: [
    'technology_footprint', 'security_tools_detected', 'outdated_technologies',
  ],
}

export const CATEGORY_LABELS: Record<SignalCategory, string> = {
  breach_intelligence: 'Breach Intelligence',
  infrastructure_exposure: 'Infrastructure Exposure',
  attack_surface: 'Attack Surface',
  technology_footprint: 'Technology Footprint',
}
