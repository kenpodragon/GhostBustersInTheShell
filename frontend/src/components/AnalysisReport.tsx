import type { EnrichedAnalyzeResponse, ClassificationBoundaries } from '../types'
import TemperatureGauge from './TemperatureGauge'
import ScoreMathExpander from './ScoreMathExpander'
import DocumentPatterns from './DocumentPatterns'
import ParagraphAccordion from './ParagraphAccordion'
import '../styles/analysis-report.css'

interface AnalysisReportProps {
  data: EnrichedAnalyzeResponse
  boundaries: ClassificationBoundaries
}

export default function AnalysisReport({ data, boundaries }: AnalysisReportProps) {
  const paragraphs = data.paragraphs || []
  const documentPatterns = data.document_patterns || []
  const tiers = data.tiers || { sentence_score: 0, paragraph_score: 0, document_score: 0, score_math: { sentence_weighted: 0, paragraph_weighted: 0, document_weighted: 0, convergence_bonus: 0, cross_tier_bonus: 0, genre_dampening: 0, raw_composite: 0, final_score: 0 } }

  return (
    <div className="analysis-report">
      <div className="analysis-report__left">
        <TemperatureGauge score={data.overall_score} boundaries={boundaries} />

        <div className="analysis-report__tiers">
          {[
            { label: 'Sentence', score: tiers.sentence_score, weight: '45%' },
            { label: 'Paragraph', score: tiers.paragraph_score, weight: '30%' },
            { label: 'Document', score: tiers.document_score, weight: '25%' },
          ].map((tier) => (
            <div key={tier.label} className="analysis-report__tier-box">
              <div className="analysis-report__tier-label">{tier.label}</div>
              <div className="analysis-report__tier-weight">{tier.weight}</div>
              <div className={`analysis-report__tier-score ${
                tier.score >= boundaries.ghost_written_lower ? 'score--high' :
                tier.score > boundaries.clean_upper ? 'score--medium' : 'score--low'
              }`}>
                {tier.score.toFixed(1)}
              </div>
            </div>
          ))}
        </div>

        {tiers.score_math && <ScoreMathExpander tiers={tiers} />}
        <DocumentPatterns patterns={documentPatterns} />
      </div>

      <div className="analysis-report__right">
        {paragraphs.length > 0 ? (
          paragraphs.map((para) => (
            <ParagraphAccordion key={para.index} paragraph={para} boundaries={boundaries} />
          ))
        ) : (
          <div className="analysis-report__no-paragraphs">No paragraphs to display</div>
        )}
      </div>
    </div>
  )
}
