import { Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Recommendation, RecommendationPriority } from '@/types'

const PRIORITY_BADGE: Record<RecommendationPriority, string> = {
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
}

const PRIORITY_BORDER: Record<RecommendationPriority, string> = {
  medium: 'border-l-yellow-400',
  high: 'border-l-orange-400',
  critical: 'border-l-red-400',
}

interface RecommendationsCardProps {
  recommendations: Recommendation[]
}

export function RecommendationsCard({ recommendations }: RecommendationsCardProps) {
  if (!recommendations || recommendations.length === 0) return null

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-slate-600" />
        <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">
          Recommended Next Steps
        </h3>
      </div>

      <div className="space-y-3">
        {recommendations.map((rec) => (
          <div
            key={rec.code}
            className={cn(
              'border border-slate-200 border-l-4 rounded-md p-3 sm:p-4',
              PRIORITY_BORDER[rec.priority] || 'border-l-slate-400'
            )}
          >
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="min-w-0">
                <h4 className="text-sm font-semibold text-slate-900">
                  {rec.name}
                  <span className="ml-2 text-xs text-slate-400 font-mono tracking-wide">{rec.code}</span>
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">{rec.tagline}</p>
              </div>
              <span className={cn('px-2.5 py-0.5 text-xs font-semibold uppercase rounded-full shrink-0', PRIORITY_BADGE[rec.priority] || PRIORITY_BADGE.medium)}>
                {rec.priority}
              </span>
            </div>

            {rec.rationale && (
              <p className="text-sm text-slate-700 leading-relaxed mb-2">{rec.rationale}</p>
            )}

            {rec.triggers?.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Why this fits</p>
                <ul className="space-y-1">
                  {rec.triggers.map((t, i) => (
                    <li key={i} className="text-xs text-slate-600 flex gap-1.5">
                      <span className="text-slate-400">•</span>
                      <span>{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
