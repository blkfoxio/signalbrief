import { useState } from 'react'
import { ChevronDown, ChevronRight, Database, Server, Layers, Shield } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getOsintRawData } from '@/api/endpoints'
import type { AuditData, AuditEntry, OsintRawData, OsintSource } from '@/types'

interface AuditPanelProps {
  reportId: string
  auditData: AuditData | null
  osintSources: OsintSource[]
  onLoadAuditData: (id: string) => void
}

type SourceTab = 'dehashed' | string

const SOURCE_META: Record<string, { label: string; icon: typeof Database }> = {
  dehashed: { label: 'DeHashed', icon: Database },
  shodan: { label: 'Shodan', icon: Server },
  builtwith: { label: 'BuiltWith', icon: Layers },
  censys: { label: 'Censys', icon: Shield },
  hibp: { label: 'HIBP', icon: Database },
  leakcheck: { label: 'LeakCheck', icon: Database },
  securitytrails: { label: 'SecurityTrails', icon: Server },
}

export function AuditPanel({ reportId, auditData, osintSources, onLoadAuditData }: AuditPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<SourceTab>('dehashed')
  const [osintRawCache, setOsintRawCache] = useState<Record<string, OsintRawData>>({})
  const [loadingSource, setLoadingSource] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const pageSize = 25

  const activeSources = osintSources.filter(s => s.result_count > 0)
  const availableTabs: SourceTab[] = ['dehashed', ...activeSources.map(s => s.source)]

  const handleToggle = () => {
    if (!isOpen && !auditData) {
      onLoadAuditData(reportId)
    }
    setIsOpen(!isOpen)
  }

  const handleTabChange = async (tab: SourceTab) => {
    setActiveTab(tab)
    setPage(0)
    if (tab !== 'dehashed' && !osintRawCache[tab]) {
      setLoadingSource(tab)
      try {
        const data = await getOsintRawData(reportId, tab)
        setOsintRawCache(prev => ({ ...prev, [tab]: data }))
      } catch {
        // silently fail
      } finally {
        setLoadingSource(null)
      }
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200">
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-50 cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-700">View Underlying Data</span>
          {activeSources.length > 0 && (
            <span className="text-xs text-slate-400">
              ({activeSources.length + 1} sources)
            </span>
          )}
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
      </button>

      {isOpen && (
        <div className="border-t border-slate-200">
          {/* Source tabs */}
          {availableTabs.length > 1 && (
            <div className="flex border-b border-slate-200 overflow-x-auto">
              {availableTabs.map(tab => {
                const meta = SOURCE_META[tab] || { label: tab, icon: Database }
                const Icon = meta.icon
                const isActive = activeTab === tab
                return (
                  <button
                    key={tab}
                    onClick={() => handleTabChange(tab)}
                    className={cn(
                      'flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 cursor-pointer transition-colors',
                      isActive
                        ? 'border-b-blue-500 text-blue-700'
                        : 'border-b-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                    )}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {meta.label}
                  </button>
                )
              })}
            </div>
          )}

          {/* Tab content */}
          <div className="p-4">
            {activeTab === 'dehashed' && auditData && (
              <DehashedTable auditData={auditData} page={page} pageSize={pageSize} onPageChange={setPage} />
            )}
            {activeTab !== 'dehashed' && loadingSource === activeTab && (
              <p className="text-sm text-slate-500 py-4 text-center">Loading {SOURCE_META[activeTab]?.label || activeTab} data...</p>
            )}
            {activeTab !== 'dehashed' && osintRawCache[activeTab] && (
              <OsintDataView source={activeTab} data={osintRawCache[activeTab]} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}


function DehashedTable({ auditData, page, pageSize, onPageChange }: {
  auditData: AuditData
  page: number
  pageSize: number
  onPageChange: (p: number) => void
}) {
  const entries = [...(auditData.entries ?? [])].sort((a, b) => {
    const aExposed = a.password_exposed ? 1 : 0
    const bExposed = b.password_exposed ? 1 : 0
    return bExposed - aExposed
  })
  const totalPages = Math.ceil(entries.length / pageSize)
  const pageEntries = entries.slice(page * pageSize, (page + 1) * pageSize)

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatBox label="Total Records" value={auditData.result_count} />
        <StatBox label="Unique Emails" value={auditData.unique_emails} />
        <StatBox label="Breach Sources" value={auditData.breach_sources} />
        <StatBox label="Queried At" value={new Date(auditData.queried_at).toLocaleString()} small />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Email</th>
              <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Source</th>
              <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Username</th>
              <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Password</th>
            </tr>
          </thead>
          <tbody>
            {pageEntries.map((entry: AuditEntry, i: number) => (
              <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 px-3 text-slate-700 font-mono text-xs">{(entry.email ?? []).join(', ') || '-'}</td>
                <td className="py-2 px-3 text-slate-700 text-xs">{entry.database_name || '-'}</td>
                <td className="py-2 px-3 text-slate-700 font-mono text-xs">{(entry.username ?? []).join(', ') || '-'}</td>
                <td className="py-2 px-3 text-xs">
                  {entry.password_exposed
                    ? <span className="text-red-600 font-medium">Exposed</span>
                    : <span className="text-slate-400">No</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
          <span className="text-xs text-slate-500">Page {page + 1} of {totalPages}</span>
          <div className="flex gap-2">
            <button onClick={() => onPageChange(Math.max(0, page - 1))} disabled={page === 0}
              className="px-3 py-1 text-xs border border-slate-300 rounded disabled:opacity-50 cursor-pointer">Previous</button>
            <button onClick={() => onPageChange(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
              className="px-3 py-1 text-xs border border-slate-300 rounded disabled:opacity-50 cursor-pointer">Next</button>
          </div>
        </div>
      )}
    </>
  )
}


function OsintDataView({ source, data }: { source: string; data: OsintRawData }) {
  const raw = data.data as Record<string, unknown>

  if (source === 'shodan') return <ShodanView data={raw} queriedAt={data.queried_at} />
  if (source === 'builtwith') return <BuiltWithView data={raw} queriedAt={data.queried_at} />
  if (source === 'censys') return <CensysView data={raw} queriedAt={data.queried_at} />
  if (source === 'hibp') return <HibpView data={raw} queriedAt={data.queried_at} />
  if (source === 'securitytrails') return <SecurityTrailsView data={raw} queriedAt={data.queried_at} />
  if (source === 'leakcheck') return <GenericJsonView data={raw} queriedAt={data.queried_at} />

  return <GenericJsonView data={raw} queriedAt={data.queried_at} />
}


function ShodanView({ data, queriedAt }: { data: Record<string, unknown>; queriedAt: string }) {
  const hosts = (data.hosts as Array<Record<string, unknown>>) || []
  const host = hosts[0] || {}
  const ports = (host.ports as number[]) || []
  const vulns = (host.vulns as string[]) || []
  const cpes = (host.cpes as string[]) || []

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatBox label="IP Address" value={data.ip as string || '-'} small />
        <StatBox label="Open Ports" value={ports.length} />
        <StatBox label="Known CVEs" value={vulns.length} />
        <StatBox label="Queried At" value={new Date(queriedAt).toLocaleString()} small />
      </div>

      {ports.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Open Ports</h4>
          <div className="flex flex-wrap gap-1.5">
            {ports.map(port => (
              <span key={port} className="px-2 py-0.5 text-xs font-mono bg-slate-100 text-slate-700 rounded">{port}</span>
            ))}
          </div>
        </div>
      )}

      {vulns.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Vulnerabilities</h4>
          <div className="flex flex-wrap gap-1.5">
            {vulns.map(cve => (
              <span key={cve} className="px-2 py-0.5 text-xs font-mono bg-red-50 text-red-700 rounded">{cve}</span>
            ))}
          </div>
        </div>
      )}

      {cpes.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Software (CPEs)</h4>
          <div className="flex flex-wrap gap-1.5">
            {cpes.map(cpe => (
              <span key={cpe} className="px-2 py-0.5 text-xs font-mono bg-slate-100 text-slate-600 rounded">{cpe}</span>
            ))}
          </div>
        </div>
      )}
    </>
  )
}


function BuiltWithView({ data, queriedAt }: { data: Record<string, unknown>; queriedAt: string }) {
  const groups = (data.groups as Array<{ name: string; live: number }>) || []
  const technologies = (data.technologies as Array<{ name: string; group: string; live_count: number }>) || []
  const totalLive = data.total as number || 0

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatBox label="Total Technologies" value={totalLive} />
        <StatBox label="Security Tools" value={data.total_security as number || 0} />
        <StatBox label="Tech Groups" value={groups.length} />
        <StatBox label="Queried At" value={new Date(queriedAt).toLocaleString()} small />
      </div>

      {groups.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Group</th>
                <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Live Count</th>
                <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Categories</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group, i) => {
                const cats = technologies.filter(t => t.group === group.name)
                return (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 px-3 text-slate-700 text-xs font-medium">{group.name}</td>
                    <td className="py-2 px-3 text-slate-700 text-xs">{group.live}</td>
                    <td className="py-2 px-3 text-xs text-slate-500">
                      {cats.map(c => c.name).join(', ') || '-'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}


function CensysView({ data, queriedAt }: { data: Record<string, unknown>; queriedAt: string }) {
  const hosts = (data.hosts as Array<Record<string, unknown>>) || []
  const certs = (data.certificates as Array<Record<string, unknown>>) || []

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatBox label="Hosts Found" value={data.total_hosts as number || hosts.length} />
        <StatBox label="Certificates" value={data.total_certificates as number || certs.length} />
        <StatBox label="Queried At" value={new Date(queriedAt).toLocaleString()} small />
      </div>
      {hosts.length === 0 && certs.length === 0 && (
        <p className="text-sm text-slate-500 py-2">No hosts or certificates found for this domain.</p>
      )}
      {hosts.length > 0 && <GenericJsonView data={{ hosts }} queriedAt={queriedAt} />}
    </>
  )
}


function HibpView({ data, queriedAt }: { data: Record<string, unknown>; queriedAt: string }) {
  const breaches = (data.breaches as Array<Record<string, unknown>>) || []

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatBox label="Known Breaches" value={breaches.length} />
        <StatBox label="Queried At" value={new Date(queriedAt).toLocaleString()} small />
      </div>
      {breaches.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Breach</th>
                <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Date</th>
                <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Records</th>
                <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Data Types</th>
              </tr>
            </thead>
            <tbody>
              {breaches.map((b, i) => (
                <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-2 px-3 text-slate-700 text-xs font-medium">{b.Name as string || '-'}</td>
                  <td className="py-2 px-3 text-slate-700 text-xs">{b.BreachDate as string || '-'}</td>
                  <td className="py-2 px-3 text-slate-700 text-xs">{(b.PwnCount as number)?.toLocaleString() || '-'}</td>
                  <td className="py-2 px-3 text-xs text-slate-500">{((b.DataClasses as string[]) || []).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}


function SecurityTrailsView({ data, queriedAt }: { data: Record<string, unknown>; queriedAt: string }) {
  const subdomains = (data.subdomains as string[]) || []

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatBox label="Subdomains" value={subdomains.length} />
        <StatBox label="Queried At" value={new Date(queriedAt).toLocaleString()} small />
      </div>
      {subdomains.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Subdomains</h4>
          <div className="flex flex-wrap gap-1.5 max-h-60 overflow-y-auto">
            {subdomains.map(sub => (
              <span key={sub} className="px-2 py-0.5 text-xs font-mono bg-slate-100 text-slate-700 rounded">{sub}</span>
            ))}
          </div>
        </div>
      )}
    </>
  )
}


function GenericJsonView({ data, queriedAt }: { data: Record<string, unknown>; queriedAt: string }) {
  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatBox label="Queried At" value={new Date(queriedAt).toLocaleString()} small />
      </div>
      <pre className="bg-slate-50 rounded p-3 text-xs text-slate-700 overflow-x-auto max-h-80 overflow-y-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}


function StatBox({ label, value, small }: { label: string; value: string | number; small?: boolean }) {
  return (
    <div className="bg-slate-50 rounded p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={cn(small ? 'text-sm font-medium' : 'text-lg font-semibold', 'text-slate-900')}>
        {value}
      </p>
    </div>
  )
}
