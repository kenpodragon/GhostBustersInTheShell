import { useState } from 'react'
import type { FidelityScoreResult, ElementScore } from '../types'

interface Props {
  result: FidelityScoreResult
  loading?: boolean
}

function scoreColor(pct: number): string {
  if (pct >= 75) return 'var(--green, #00ff41)'
  if (pct >= 50) return 'var(--yellow, #ffff00)'
  return 'var(--red, #ff0040)'
}

function ElementRow({ el }: { el: ElementScore }) {
  const pct = Math.round(el.similarity * 100)
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', borderBottom: '1px solid rgba(0,255,65,0.1)' }}>
      <span style={{ flex: 2 }}>{el.name}</span>
      <span style={{ flex: 1, textAlign: 'right' }}>{el.profile_value?.toFixed(3)}</span>
      <span style={{ flex: 1, textAlign: 'right' }}>{el.generated_value?.toFixed(3)}</span>
      <span style={{ flex: 1, textAlign: 'right', color: scoreColor(pct) }}>{pct}%</span>
    </div>
  )
}

export default function FidelityScore({ result, loading }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (loading) return <div className="terminal-output" style={{ padding: '8px' }}>Scoring...</div>

  const quant = result.quantitative
  const qual = result.qualitative
  const aggPct = quant ? Math.round(quant.aggregate_similarity * 100) : null

  return (
    <div className="terminal-output" style={{ padding: '12px', marginTop: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
        <span style={{ fontSize: '14px', opacity: 0.7 }}>VOICE FIDELITY</span>
        {aggPct !== null && (
          <span style={{ fontSize: '24px', fontWeight: 'bold', color: scoreColor(aggPct) }}>{aggPct}%</span>
        )}
        {quant && <span style={{ fontSize: '12px', opacity: 0.5 }}>{quant.matched} elements matched</span>}
      </div>
      {quant && (
        <div>
          <button className="vp-btn" onClick={() => setExpanded(!expanded)} style={{ fontSize: '12px', marginBottom: '4px' }}>
            {expanded ? 'Collapse' : 'Expand'} per-element breakdown
          </button>
          {expanded && (
            <div style={{ maxHeight: '300px', overflowY: 'auto', fontSize: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontWeight: 'bold', borderBottom: '1px solid rgba(0,255,65,0.3)' }}>
                <span style={{ flex: 2 }}>Element</span>
                <span style={{ flex: 1, textAlign: 'right' }}>Profile</span>
                <span style={{ flex: 1, textAlign: 'right' }}>Generated</span>
                <span style={{ flex: 1, textAlign: 'right' }}>Match</span>
              </div>
              {[...quant.per_element].sort((a, b) => a.similarity - b.similarity).map(el => <ElementRow key={el.name} el={el} />)}
            </div>
          )}
        </div>
      )}
      {qual && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontSize: '14px', opacity: 0.7, marginBottom: '4px' }}>AI ASSESSMENT</div>
          <p style={{ fontSize: '13px', marginBottom: '8px' }}>{qual.overall_assessment}</p>
          {qual.matches.length > 0 && (
            <div style={{ marginBottom: '4px' }}>
              <span style={{ color: 'var(--green, #00ff41)', fontSize: '12px' }}>MATCHES: </span>
              <span style={{ fontSize: '12px' }}>{qual.matches.join(' | ')}</span>
            </div>
          )}
          {qual.gaps.length > 0 && (
            <div>
              <span style={{ color: 'var(--red, #ff0040)', fontSize: '12px' }}>GAPS: </span>
              <span style={{ fontSize: '12px' }}>{qual.gaps.join(' | ')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
