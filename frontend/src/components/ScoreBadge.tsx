import type { Classification } from '../types'

function getScoreClass(score: number): string {
  if (score < 20) return 'score-low'
  if (score < 45) return 'score-medium'
  if (score < 70) return 'score-high'
  return 'score-critical'
}

function getCategoryLabel(classification: Classification | null): string {
  if (!classification) return ''
  return classification.category || ''
}

interface Props {
  score: number | null
  classification?: Classification | null
  size?: 'small' | 'normal'
}

export default function ScoreBadge({ score, classification, size = 'normal' }: Props) {
  if (score === null) return <span className="text-muted">—</span>

  const cls = getScoreClass(score)
  const category = getCategoryLabel(classification ?? null)
  const fontSize = size === 'small' ? '0.75rem' : '0.85rem'

  return (
    <span className={`score-badge ${cls}`} style={{ fontSize }}>
      {score.toFixed(1)}
      {category && <span className="category-label"> {category}</span>}
    </span>
  )
}
