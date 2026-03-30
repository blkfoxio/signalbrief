import { Building2, Globe, Users, Briefcase } from 'lucide-react'
import type { CompanySnapshot as CompanySnapshotType } from '@/types'

export function CompanySnapshot({ company }: { company: CompanySnapshotType }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5">
      <h2 className="text-lg font-semibold text-slate-900 mb-3">Company Snapshot</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="flex items-start gap-2">
          <Building2 className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs text-slate-500">Company</p>
            <p className="text-sm font-medium text-slate-900">{company.name || company.domain}</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Globe className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs text-slate-500">Domain</p>
            <p className="text-sm font-medium text-slate-900">{company.domain}</p>
          </div>
        </div>
        {company.industry && (
          <div className="flex items-start gap-2">
            <Briefcase className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-slate-500">Industry</p>
              <p className="text-sm font-medium text-slate-900">{company.industry}</p>
            </div>
          </div>
        )}
        {company.employee_range && (
          <div className="flex items-start gap-2">
            <Users className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-slate-500">Employees</p>
              <p className="text-sm font-medium text-slate-900">{company.employee_range}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
