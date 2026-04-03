import type { CompletenessData } from '../types'

interface Props {
  data: CompletenessData | null
}

const TIER_COLORS: Record<string, string> = {
  starter: '#4a9eff',
  bronze: '#cd7f32',
  silver: '#8a9ba8',
  gold: '#d4a017',
}

const STARTER_MILESTONE_POSITIONS = [
  { label: '2K', pct: 10 },
  { label: '5K', pct: 25 },
  { label: '10K', pct: 50 },
  { label: '20K', pct: 100 },
]

export default function CompletenessBar({ data }: Props) {
  if (!data) {
    return (
      <div className="completeness-bar-container">
        <div className="completeness-empty">
          No convergence data yet — submit text samples to build your profile
        </div>
      </div>
    )
  }

  const isStarter = data.tier === 'starter'
  const barColor = data.tier ? TIER_COLORS[data.tier] || 'var(--text-muted)' : 'var(--text-muted)'
  const tierText = data.tier_label || 'Building...'

  if (isStarter && data.starter_progress) {
    return <StarterBar data={data} barColor={barColor} tierText={tierText} />
  }

  return <ConvergenceBar data={data} barColor={barColor} tierText={tierText} />
}

function StarterBar({
  data,
  barColor,
  tierText,
}: {
  data: CompletenessData
  barColor: string
  tierText: string
}) {
  const sp = data.starter_progress!
  const isComplete = sp.milestone === 4

  // Overall progress through Starter (0-100% of the full 0→20K range)
  const overallPct = Math.min(100, (sp.words_current / 20000) * 100)

  return (
    <div className="completeness-bar-container">
      <div className="completeness-header">
        <span className="completeness-tier" style={{ color: barColor }}>
          {tierText}
        </span>
        <span className="completeness-stats">
          {sp.words_current.toLocaleString()} words
        </span>
      </div>

      <div className="completeness-track">
        <div
          className="completeness-fill"
          style={{ width: `${overallPct}%`, backgroundColor: barColor }}
        />
        {STARTER_MILESTONE_POSITIONS.map((m, i) => (
          <div
            key={i}
            className="completeness-marker"
            style={{ left: `${m.pct}%` }}
            title={`${m.label} words`}
          />
        ))}
      </div>

      {data.guidance && (
        <div className="completeness-hint">{data.guidance}</div>
      )}

      {isComplete && data.pct !== undefined && (
        <div className="completeness-secondary">
          {data.pct}% voice convergence — need 50% for Bronze
        </div>
      )}

      {!isComplete && data.pct > 0 && (
        <div className="completeness-secondary">
          {data.pct}% voice convergence
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

function ConvergenceBar({
  data,
  barColor,
  tierText,
}: {
  data: CompletenessData
  barColor: string
  tierText: string
}) {
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

      {data.guidance && (
        <div className="completeness-hint">{data.guidance}</div>
      )}

      {data.words_to_next_tier && data.next_tier_label && !data.guidance && (
        <div className="completeness-hint">
          Submit {data.words_to_next_tier} more words for {data.next_tier_label}
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
