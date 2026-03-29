import { Loader2, Shield } from 'lucide-react'

export function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div className="relative">
        <Shield className="w-12 h-12 text-blue-100" />
        <Loader2 className="w-6 h-6 text-blue-600 animate-spin absolute top-3 left-3" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-slate-700">Analyzing prospect...</p>
        <p className="text-xs text-slate-400 mt-1">Querying breach data and generating insights</p>
      </div>
    </div>
  )
}
