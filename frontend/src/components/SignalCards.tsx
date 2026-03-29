import {
  AlertTriangle, Mail, Shield, RefreshCw,
  Bug, Database, Clock, AlertOctagon,
  Server, ShieldAlert, Package, FileWarning, Lock,
  Network, Wifi,
  Layers, ShieldCheck, Archive
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SecuritySignal } from '@/types'

const SEVERITY_COLORS = {
  low: 'border-l-slate-400 bg-slate-50',
  medium: 'border-l-yellow-400 bg-yellow-50',
  high: 'border-l-orange-400 bg-orange-50',
  critical: 'border-l-red-400 bg-red-50',
}

const SIGNAL_ICONS: Record<string, typeof Mail> = {
  // Breach Intelligence (DeHashed, HIBP, LeakCheck)
  employee_emails_exposed: Mail,
  breach_events: AlertTriangle,
  password_exposure: Shield,
  repeated_identity_exposure: RefreshCw,
  stealer_log_exposure: Bug,
  credential_market_presence: AlertOctagon,
  known_breaches: Database,
  breach_recency: Clock,
  sensitive_breach_exposure: AlertOctagon,
  // Infrastructure (Shodan, Censys)
  exposed_services: Server,
  known_vulnerabilities: ShieldAlert,
  outdated_software: Package,
  expired_certificates: FileWarning,
  weak_encryption: Lock,
  // Attack Surface (SecurityTrails)
  subdomain_count: Network,
  dns_misconfigurations: Wifi,
  historical_dns_changes: RefreshCw,
  // Tech Footprint (BuiltWith)
  technology_footprint: Layers,
  security_tools_detected: ShieldCheck,
  outdated_technologies: Archive,
}

const SOURCE_LABELS: Record<string, string> = {
  dehashed: 'DeHashed',
  hibp: 'HIBP',
  leakcheck: 'LeakCheck',
  shodan: 'Shodan',
  censys: 'Censys',
  securitytrails: 'SecurityTrails',
  builtwith: 'BuiltWith',
}

export function SignalCards({ signals, showSource = false }: { signals: SecuritySignal[], showSource?: boolean }) {
  if (!signals.length) return null

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {signals.map((signal, i) => {
        const Icon = SIGNAL_ICONS[signal.signal_type] || AlertTriangle
        return (
          <div
            key={i}
            className={cn(
              'border-l-4 rounded-lg p-4',
              SEVERITY_COLORS[signal.severity]
            )}
          >
            <div className="flex items-start gap-3">
              <Icon className="w-5 h-5 text-slate-600 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900">{signal.title}</p>
                <p className="text-xs text-slate-600 mt-1">{signal.description}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="inline-block text-xs font-medium uppercase tracking-wide text-slate-500">
                    {signal.severity}
                  </span>
                  {showSource && signal.source && (
                    <span className="inline-block text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                      {SOURCE_LABELS[signal.source] || signal.source}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
