import { useState } from 'react'
import { Shield, Server, Network, Layers } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SignalCards } from './SignalCards'
import type { SecuritySignal, CategoryFindings, SignalCategory } from '@/types'
import { SIGNAL_CATEGORIES, CATEGORY_LABELS } from '@/types'

const CATEGORY_ICONS: Record<SignalCategory, typeof Shield> = {
  breach_intelligence: Shield,
  infrastructure_exposure: Server,
  attack_surface: Network,
  technology_footprint: Layers,
}

const CATEGORY_COLORS: Record<SignalCategory, string> = {
  breach_intelligence: 'border-red-500 text-red-700 bg-red-50',
  infrastructure_exposure: 'border-orange-500 text-orange-700 bg-orange-50',
  attack_surface: 'border-blue-500 text-blue-700 bg-blue-50',
  technology_footprint: 'border-purple-500 text-purple-700 bg-purple-50',
}

const CATEGORY_ACTIVE: Record<SignalCategory, string> = {
  breach_intelligence: 'border-b-red-500 text-red-700',
  infrastructure_exposure: 'border-b-orange-500 text-orange-700',
  attack_surface: 'border-b-blue-500 text-blue-700',
  technology_footprint: 'border-b-purple-500 text-purple-700',
}

interface CategoryTabsProps {
  signals: SecuritySignal[]
  categoryFindings?: CategoryFindings
}

function getSignalsForCategory(signals: SecuritySignal[], category: SignalCategory): SecuritySignal[] {
  const types = SIGNAL_CATEGORIES[category]
  return signals.filter(s => types.includes(s.signal_type))
}

function getActiveCategories(signals: SecuritySignal[]): SignalCategory[] {
  const categories: SignalCategory[] = ['breach_intelligence', 'infrastructure_exposure', 'attack_surface', 'technology_footprint']
  return categories.filter(cat => getSignalsForCategory(signals, cat).length > 0)
}

export function CategoryTabs({ signals, categoryFindings }: CategoryTabsProps) {
  const activeCategories = getActiveCategories(signals)
  const [activeTab, setActiveTab] = useState<SignalCategory>(activeCategories[0] || 'breach_intelligence')

  if (activeCategories.length === 0) return null

  const currentSignals = getSignalsForCategory(signals, activeTab)
  const currentFinding = categoryFindings?.[activeTab]

  return (
    <div className="bg-white rounded-lg border border-slate-200">
      {/* Tab bar */}
      <div className="flex border-b border-slate-200 overflow-x-auto">
        {activeCategories.map(category => {
          const Icon = CATEGORY_ICONS[category]
          const count = getSignalsForCategory(signals, category).length
          const isActive = activeTab === category

          return (
            <button
              key={category}
              onClick={() => setActiveTab(category)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 cursor-pointer transition-colors',
                isActive
                  ? CATEGORY_ACTIVE[category]
                  : 'border-b-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
              )}
            >
              <Icon className="w-4 h-4" />
              {CATEGORY_LABELS[category]}
              <span className={cn(
                'text-xs px-1.5 py-0.5 rounded-full',
                isActive ? 'bg-slate-200 text-slate-700' : 'bg-slate-100 text-slate-500'
              )}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      <div className="p-5">
        {currentFinding && (
          <div className={cn('border-l-4 rounded-r-lg p-3 mb-4', CATEGORY_COLORS[activeTab])}>
            <p className="text-sm leading-relaxed">{currentFinding}</p>
          </div>
        )}

        <SignalCards signals={currentSignals} showSource />
      </div>
    </div>
  )
}
