import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import type { NarrativeOutput } from '@/types'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="text-slate-400 hover:text-blue-600 cursor-pointer p-1"
      title="Copy to clipboard"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

interface NarrativeSectionProps {
  label: string
  content: string
}

function NarrativeSection({ label, content }: NarrativeSectionProps) {
  if (!content) return null
  return (
    <div className="py-4 border-b border-slate-100 last:border-b-0">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</h3>
        <CopyButton text={content} />
      </div>
      <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{content}</p>
    </div>
  )
}

export function NarrativeView({ narrative }: { narrative: NarrativeOutput }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-0">
      {narrative.headline && (
        <div className="pb-4 border-b border-slate-100">
          <p className="text-base font-semibold text-slate-900">{narrative.headline}</p>
        </div>
      )}
      <NarrativeSection label="Executive Narrative" content={narrative.executive_narrative} />
      <NarrativeSection label="Talk Track" content={narrative.talk_track} />
      <NarrativeSection label="Business Impact" content={narrative.business_impact} />
      <NarrativeSection label="Transition" content={narrative.transition} />
    </div>
  )
}
