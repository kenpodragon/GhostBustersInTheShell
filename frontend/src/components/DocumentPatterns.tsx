import type { EnrichedPattern } from '../types'
import PatternChip from './PatternChip'

interface DocumentPatternsProps {
  patterns: EnrichedPattern[]
}

export default function DocumentPatterns({ patterns }: DocumentPatternsProps) {
  if (!patterns || patterns.length === 0) {
    return (
      <div className="document-patterns">
        <div className="document-patterns__header">
          DOCUMENT PATTERNS <span className="document-patterns__count">(0)</span>
        </div>
        <div className="document-patterns__empty">No document-level patterns detected</div>
      </div>
    )
  }

  return (
    <div className="document-patterns">
      <div className="document-patterns__header">
        DOCUMENT PATTERNS <span className="document-patterns__count">({patterns.length})</span>
      </div>
      <div className="document-patterns__chips">
        {patterns.map((p, i) => (
          <PatternChip key={`${p.name}-${i}`} pattern={p} />
        ))}
      </div>
    </div>
  )
}
