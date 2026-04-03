import { useState } from 'react'
import type { CompletenessData } from '../types'

interface Props {
  data: CompletenessData | null
}

const STATUS_COLORS: Record<string, string> = {
  complete: 'var(--accent)',
  good: '#d4a017',
  needs_more: 'var(--danger)',
}

const STATUS_ICONS: Record<string, string> = {
  complete: '✓',
  good: '◐',
  needs_more: '○',
}

const CATEGORY_LABELS: Record<string, string> = {
  readability: 'Readability',
  lexical: 'Lexical / Vocabulary',
  syntactic: 'Sentence Structure',
  structural: 'Paragraph Structure',
  idiosyncratic: 'Punctuation & Pronouns',
  voice_tone: 'Voice & Tone',
}

export default function CategoryConvergence({ data }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)

  if (!data || !data.categories || Object.keys(data.categories).length === 0) {
    return null
  }

  const categories = Object.entries(data.categories).sort(
    ([, a], [, b]) => (a.status === 'complete' ? 1 : 0) - (b.status === 'complete' ? 1 : 0)
  )

  return (
    <div className="category-convergence">
      <h4 style={{ margin: '0.5rem 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Element Convergence by Category
      </h4>
      {categories.map(([cat, info]) => {
        const label = CATEGORY_LABELS[cat] || cat
        const icon = STATUS_ICONS[info.status] || '?'
        const color = STATUS_COLORS[info.status] || 'var(--text-muted)'
        const isExpanded = expanded === cat

        return (
          <div key={cat} className="convergence-category">
            <button
              className="convergence-category-header"
              onClick={() => setExpanded(isExpanded ? null : cat)}
              style={{ borderLeftColor: color }}
            >
              <span style={{ color }}>{icon}</span>
              <span className="convergence-category-label">{label}</span>
              <span className="convergence-category-count">
                {info.converged}/{info.total}
              </span>
              <span className="convergence-expand">{isExpanded ? '▾' : '▸'}</span>
            </button>
            {isExpanded && (
              <div className="convergence-category-detail">
                {info.status === 'complete'
                  ? 'All elements converged — this category is stable.'
                  : `${info.total - info.converged} element(s) still need more writing samples.`}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
