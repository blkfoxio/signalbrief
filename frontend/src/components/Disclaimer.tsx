import { Info } from 'lucide-react'

interface DisclaimerProps {
  text: string
}

export function Disclaimer({ text }: DisclaimerProps) {
  if (!text) return null
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 sm:p-4 flex gap-3">
      <Info className="w-4 h-4 text-amber-700 mt-0.5 shrink-0" />
      <div className="text-xs text-amber-900 leading-relaxed">
        <span className="font-semibold uppercase tracking-wide mr-1">Important:</span>
        {text}
      </div>
    </div>
  )
}
