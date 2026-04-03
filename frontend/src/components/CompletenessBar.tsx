import type { CompletenessData } from '../types'

interface Props {
  data: CompletenessData | null
}

const TIER_COLORS: Record<string, string> = {
  bronze: '#cd7f32',
  silver: '#8a9ba8',
  gold: '#d4a017',
}

export default function CompletenessBar({ data }: Props) {
  if (!data || data.elements_total === 0) {
    return (
      <div className="completeness-bar-container">
        <div className="completeness-empty">
          No convergence data yet — submit text samples to build your profile
        </div>
      </div>
    )
  }

  const barColor = data.tier ? TIER_COLORS[data.tier] : 'var(--text-muted)'
  const tierText = data.tier_label || 'Building...'

  return (
    <div className="completeness-bar-container">
      <div className="completeness-header">
        <span className="completeness-tier" style={{ color: barColor }}>
          {tierText}
        </span>
        <span className="completeness-stats">
          {data.pct}% complete ({data.total_words.toLocaleString()} words)
        </span>
      </div>

      <div className="completeness-track">
        <div
          className="completeness-fill"
          style={{ width: `${data.pct}%`, backgroundColor: barColor }}
        />
        <div className="completeness-marker" style={{ left: '50%' }} title="Bronze (50%)" />
        <div className="completeness-marker" style={{ left: '75%' }} title="Silver (75%)" />
        <div className="completeness-marker" style={{ left: '90%' }} title="Gold (90%)" />
      </div>

      {data.words_to_next_tier && data.next_tier_label && (
        <div className="completeness-hint">
          Submit {data.words_to_next_tier} more words for a {data.next_tier_label}
        </div>
      )}

      {data.newly_converged && data.newly_converged.length > 0 && (
        <div className="completeness-toast">
          +{data.newly_converged.length} elements converged: {data.newly_converged.join(', ')}
        </div>
      )}
    </div>
  )
}
