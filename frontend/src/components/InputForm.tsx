import { useState, type FormEvent } from 'react'
import type { ReportInput } from '@/types'
import { Loader2 } from 'lucide-react'

interface InputFormProps {
  onSubmit: (input: ReportInput) => Promise<void>
  isLoading: boolean
}

export function InputForm({ onSubmit, isLoading }: InputFormProps) {
  const [domain, setDomain] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!domain && !contactEmail) {
      setError('Please provide a company domain or contact email.')
      return
    }

    await onSubmit({
      domain,
      company_name: companyName,
      linkedin_url: '',
      contact_email: contactEmail,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Company Domain</label>
        <input
          type="text"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder="acme.com"
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="text-xs text-slate-400 mt-1">Best for the most accurate results.</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Company Name</label>
        <input
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder="Acme Health"
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Contact Email <span className="text-slate-400">(optional)</span></label>
        <input
          type="email"
          value={contactEmail}
          onChange={(e) => setContactEmail(e.target.value)}
          placeholder="jane@acme.com"
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyzing...
          </>
        ) : (
          'Generate Security Brief'
        )}
      </button>
    </form>
  )
}
