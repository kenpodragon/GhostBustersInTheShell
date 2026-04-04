import type { ClassificationBoundaries } from '../types'

interface TemperatureGaugeProps {
  score: number
  boundaries: ClassificationBoundaries
}

export default function TemperatureGauge({ score, boundaries }: TemperatureGaugeProps) {
  const { clean_upper, ghost_written_lower } = boundaries
  const cleanPct = clean_upper
  const touchedPct = ghost_written_lower - clean_upper
  const writtenPct = 100 - ghost_written_lower

  const needleLeft = Math.min(100, Math.max(0, score))

  const getZoneLabel = () => {
    if (score <= clean_upper) return 'Clean'
    if (score < ghost_written_lower) return 'Ghost Touched'
    return 'Ghost Written'
  }

  return (
    <div className="temperature-gauge">
      <div className="temperature-gauge__bar">
        <div className="temperature-gauge__zone temperature-gauge__zone--clean" style={{ width: `${cleanPct}%` }}>
          <span className="temperature-gauge__label">CLEAN</span>
        </div>
        <div className="temperature-gauge__zone temperature-gauge__zone--touched" style={{ width: `${touchedPct}%` }}>
          <span className="temperature-gauge__label">TOUCHED</span>
        </div>
        <div className="temperature-gauge__zone temperature-gauge__zone--written" style={{ width: `${writtenPct}%` }}>
          <span className="temperature-gauge__label">WRITTEN</span>
        </div>
        <div
          className="temperature-gauge__needle"
          style={{ left: `${needleLeft}%` }}
          title={`${score.toFixed(1)} — ${getZoneLabel()}`}
        />
      </div>
      <div className="temperature-gauge__ticks">
        <span>0</span>
        <span style={{ left: `${clean_upper}%` }}>{clean_upper}</span>
        <span style={{ left: `${ghost_written_lower}%` }}>{ghost_written_lower}</span>
        <span style={{ left: '100%' }}>100</span>
      </div>
    </div>
  )
}
