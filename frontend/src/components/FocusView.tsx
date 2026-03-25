import { useDocument } from '../context/DocumentContext'
import ScoreBadge from './ScoreBadge'

export default function FocusView() {
  const {
    sections, focusedSectionIndex, setFocusedSection,
    setView, setRewritePanelOpen,
  } = useDocument()

  const index = focusedSectionIndex ?? 0
  const section = sections[index]
  if (!section) return null

  const hasPrev = index > 0
  const hasNext = index < sections.length - 1

  return (
    <div className="focus-view">
      {/* Navigation header */}
      <div className="focus-header">
        <button
          className="btn btn-small"
          onClick={() => setView('sections')}
        >
          [ ← LIST ]
        </button>
        <div className="focus-nav">
          <button
            className="btn btn-small"
            disabled={!hasPrev}
            onClick={() => setFocusedSection(index - 1)}
          >
            [ PREV ]
          </button>
          <span className="text-muted">
            Section {index + 1} of {sections.length}
          </span>
          <button
            className="btn btn-small"
            disabled={!hasNext}
            onClick={() => setFocusedSection(index + 1)}
          >
            [ NEXT ]
          </button>
        </div>
        <button
          className="btn btn-small"
          onClick={() => setRewritePanelOpen(true)}
        >
          [ REWRITE ]
        </button>
      </div>

      {/* Section heading + score */}
      <div className="focus-title">
        <h2 style={{ fontSize: '1rem', margin: 0 }}>{section.heading}</h2>
        <ScoreBadge score={section.score} classification={section.classification} />
      </div>

      {/* Sentence-level highlighted text */}
      <div className="card focus-text">
        {section.sentences.length > 0 ? (
          section.sentences.map((sent, i) => (
            <span
              key={i}
              className={
                sent.score > 50 ? 'highlight-ai' :
                sent.score < 20 ? 'highlight-human' : ''
              }
              title={`Score: ${sent.score.toFixed(1)}`}
            >
              {sent.text}{' '}
            </span>
          ))
        ) : (
          <p>{section.text}</p>
        )}
      </div>

      {/* Score breakdown */}
      {section.score !== null && (
        <div className="card focus-breakdown">
          <div className="card-header">Score Breakdown</div>
          <div className="breakdown-grid">
            <div>
              <span className="text-muted">Overall</span>
              <strong>{section.score.toFixed(1)}</strong>
            </div>
            <div>
              <span className="text-muted">Classification</span>
              <strong>{section.classification?.category || '—'}</strong>
            </div>
            <div>
              <span className="text-muted">Confidence</span>
              <strong>{section.classification?.confidence || '—'}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Detected patterns */}
      {section.patterns.length > 0 && (
        <div className="card">
          <div className="card-header">Detected Patterns ({section.patterns.length})</div>
          <div className="terminal-output">
            {section.patterns.map((p, i) => (
              <div key={i} className="pattern-row">
                <span className="pattern-name">{p.pattern}</span>
                <span className="text-muted"> — {p.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
