import { useState } from 'react'
import type { EnrichedTiers } from '../types'

interface ScoreMathExpanderProps {
  tiers: EnrichedTiers
}

export default function ScoreMathExpander({ tiers }: ScoreMathExpanderProps) {
  const [expanded, setExpanded] = useState(false)
  const math = tiers.score_math

  return (
    <div className="score-math-expander" onClick={() => setExpanded(!expanded)}>
      <div className="score-math-expander__header">
        <span className="score-math-expander__arrow">{expanded ? '▼' : '▶'}</span>
        <span className="score-math-expander__title">Score Math</span>
      </div>
      {expanded && (
        <div className="score-math-expander__body" onClick={(e) => e.stopPropagation()}>
          <div className="score-math-expander__row">
            <span>Sentence ({tiers.sentence_score.toFixed(1)}) × 0.45</span>
            <span>= {math.sentence_weighted.toFixed(1)}</span>
          </div>
          <div className="score-math-expander__row">
            <span>Paragraph ({tiers.paragraph_score.toFixed(1)}) × 0.30</span>
            <span>= {math.paragraph_weighted.toFixed(1)}</span>
          </div>
          <div className="score-math-expander__row">
            <span>Document ({tiers.document_score.toFixed(1)}) × 0.25</span>
            <span>= {math.document_weighted.toFixed(1)}</span>
          </div>
          <div className="score-math-expander__divider" />
          <div className="score-math-expander__row">
            <span>Raw Composite</span>
            <span>{math.raw_composite.toFixed(1)}</span>
          </div>
          {math.convergence_bonus > 0 && (
            <div className="score-math-expander__row score-math-expander__row--bonus">
              <span>Convergence Bonus</span>
              <span>+{math.convergence_bonus.toFixed(1)}</span>
            </div>
          )}
          {math.cross_tier_bonus > 0 && (
            <div className="score-math-expander__row score-math-expander__row--bonus">
              <span>Cross-Tier Bonus</span>
              <span>+{math.cross_tier_bonus.toFixed(1)}</span>
            </div>
          )}
          {math.genre_dampening > 0 && (
            <div className="score-math-expander__row score-math-expander__row--penalty">
              <span>Genre Dampening</span>
              <span>-{math.genre_dampening.toFixed(1)}</span>
            </div>
          )}
          <div className="score-math-expander__divider" />
          {math.heuristic_final != null && math.heuristic_weight != null ? (
            <>
              <div className="score-math-expander__row">
                <span>Heuristic ({math.heuristic_final.toFixed(1)}) × {math.heuristic_weight}</span>
                <span>= {(math.heuristic_final * math.heuristic_weight).toFixed(1)}</span>
              </div>
              {math.ai_score != null && math.ai_weight != null && (
                <div className="score-math-expander__row">
                  <span>AI Score ({math.ai_score.toFixed(1)}) × {math.ai_weight}</span>
                  <span>= {(math.ai_score * math.ai_weight).toFixed(1)}</span>
                </div>
              )}
              {math.roberta_score != null && math.roberta_weight != null && (
                <div className="score-math-expander__row score-math-expander__row--roberta">
                  <span>Neural ({math.roberta_score.toFixed(1)}) × {math.roberta_weight}</span>
                  <span>= {(math.roberta_score * math.roberta_weight).toFixed(1)}</span>
                </div>
              )}
              <div className="score-math-expander__divider" />
              <div className="score-math-expander__row score-math-expander__row--total">
                <span>Final Score (Combined)</span>
                <span>{math.final_score.toFixed(1)}</span>
              </div>
            </>
          ) : (
            <div className="score-math-expander__row score-math-expander__row--total">
              <span>Final Score</span>
              <span>{math.final_score.toFixed(1)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
