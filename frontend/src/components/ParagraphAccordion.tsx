import { useState } from 'react'
import type { EnrichedParagraph, ClassificationBoundaries } from '../types'
import PatternChip from './PatternChip'
import ScoreBadge from './ScoreBadge'

interface ParagraphAccordionProps {
  paragraph: EnrichedParagraph
  boundaries: ClassificationBoundaries
}

export default function ParagraphAccordion({ paragraph, boundaries }: ParagraphAccordionProps) {
  const [expanded, setExpanded] = useState(paragraph.score > 50)

  const borderClass = paragraph.score >= boundaries.ghost_written_lower
    ? 'paragraph-accordion--high'
    : paragraph.score > boundaries.clean_upper
      ? 'paragraph-accordion--medium'
      : 'paragraph-accordion--low'

  return (
    <div className={`paragraph-accordion ${borderClass}`}>
      <div className="paragraph-accordion__header" onClick={() => setExpanded(!expanded)}>
        <div className="paragraph-accordion__title">
          <span className="paragraph-accordion__arrow">{expanded ? '▼' : '▶'}</span>
          <strong>Paragraph {paragraph.index + 1}</strong>
          <span className="paragraph-accordion__meta">— {paragraph.sentence_count} sentences</span>
        </div>
        <div className="paragraph-accordion__right">
          {paragraph.patterns.map((p, i) => (
            <PatternChip key={`${p.name}-${i}`} pattern={p} size="small" />
          ))}
          <ScoreBadge score={paragraph.score} size="small" />
        </div>
      </div>
      {expanded && (
        <div className="paragraph-accordion__body">
          {paragraph.sentences.map((s, i) => (
            <div key={i} className="paragraph-accordion__sentence">
              <span className="paragraph-accordion__sentence-text">
                &ldquo;{s.text.length > 80 ? s.text.substring(0, 80) + '...' : s.text}&rdquo;
              </span>
              <div className="paragraph-accordion__sentence-right">
                {s.patterns.map((p, j) => (
                  <PatternChip key={`${p.name}-${j}`} pattern={p} size="small" />
                ))}
                <span className={`paragraph-accordion__sentence-score ${
                  s.score >= boundaries.ghost_written_lower ? 'score--high' :
                  s.score > boundaries.clean_upper ? 'score--medium' : 'score--low'
                }`}>
                  {s.score.toFixed(1)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
