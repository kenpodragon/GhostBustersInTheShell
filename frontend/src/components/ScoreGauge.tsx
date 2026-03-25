interface Props {
  score: number | null
}

export default function ScoreGauge({ score }: Props) {
  if (score === null) return null

  const clampedScore = Math.max(0, Math.min(100, score))

  return (
    <div className="score-gauge">
      <div className="score-gauge-bar">
        <div className="score-gauge-zone gauge-clean" />
        <div className="score-gauge-zone gauge-touched" />
        <div className="score-gauge-zone gauge-written" />
        <div
          className="score-gauge-marker"
          style={{ left: `${clampedScore}%` }}
        />
      </div>
      <div className="score-gauge-labels">
        <span className="gauge-label-clean">Clean</span>
        <span className="gauge-label-touched">Ghost Touched</span>
        <span className="gauge-label-written">Ghost Written</span>
      </div>
    </div>
  )
}
