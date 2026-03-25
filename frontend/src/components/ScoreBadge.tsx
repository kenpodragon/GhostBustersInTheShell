import type { Classification } from '../types'

function getScoreClass(score: number, classification?: Classification | null): string {
  // Use backend classification if available, otherwise fall back to score thresholds
  if (classification?.category) {
    if (classification.category === 'clean') return 'score-low'
    if (classification.category === 'ghost_touched') return 'score-medium'
    return 'score-critical'
  }
  if (score <= 30) return 'score-low'
  if (score < 40) return 'score-medium'
  return 'score-critical'
}

function getCategoryLabel(classification: Classification | null): string {
  if (!classification) return ''
  return classification.label || classification.category || ''
}

interface Props {
  score: number | null
  classification?: Classification | null
  size?: 'small' | 'normal'
}

export default function ScoreBadge({ score, classification, size = 'normal' }: Props) {
  if (score === null) return <span className="text-muted">—</span>

  const cls = getScoreClass(score, classification)
  const category = getCategoryLabel(classification ?? null)
  const fontSize = size === 'small' ? '0.75rem' : '0.85rem'

  return (
    <span className={`score-badge ${cls}`} style={{ fontSize }}>
      {score.toFixed(1)}
      {category && <span className="category-label"> {category}</span>}
    </span>
  )
}
