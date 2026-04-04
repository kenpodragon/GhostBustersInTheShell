import type { EnrichedPattern } from '../types'

interface PatternChipProps {
  pattern: EnrichedPattern
  size?: 'small' | 'normal'
}

export default function PatternChip({ pattern, size = 'normal' }: PatternChipProps) {
  const severityClass = pattern.severity ? `pattern-chip--${pattern.severity}` : 'pattern-chip--low'
  const sizeClass = size === 'small' ? 'pattern-chip--small' : ''

  return (
    <span
      className={`analysis-pattern-chip ${severityClass} ${sizeClass}`}
      title={pattern.description || ''}
    >
      {pattern.display_name || pattern.pattern}
      {pattern.count != null && pattern.count > 1 && (
        <span className="analysis-pattern-chip__count">: {pattern.count}</span>
      )}
    </span>
  )
}
