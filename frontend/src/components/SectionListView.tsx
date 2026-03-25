import { useEffect, useState } from 'react'
import { useDocument } from '../context/DocumentContext'
import ScoreBadge from './ScoreBadge'

export default function SectionListView() {
  const {
    sections, loading, analyzeAll, rewriteSection, setView, setFocusedSection,
    setRewritePanelOpen, document: doc,
  } = useDocument()

  // Auto-analyze on mount (only if sections are unscored)
  const [hasAutoAnalyzed, setHasAutoAnalyzed] = useState(false)
  useEffect(() => {
    if (hasAutoAnalyzed) return
    const unscored = sections.some(s => s.score === null)
    if (unscored) {
      setHasAutoAnalyzed(true)
      analyzeAll()
    }
  }, [sections, hasAutoAnalyzed, analyzeAll])

  const cleanCount = sections.filter(s => s.classification?.category === 'Clean').length
  const touchedCount = sections.filter(s => s.classification?.category === 'Ghost Touched').length
  const writtenCount = sections.filter(s => s.classification?.category === 'Ghost Written').length
  const avgScore = sections.length > 0
    ? sections.reduce((sum, s) => sum + (s.score ?? 0), 0) / sections.length
    : 0

  const handleFocus = (index: number) => {
    setFocusedSection(index)
    setView('focus')
  }

  const handleRewrite = (index: number) => {
    setFocusedSection(index)
    setRewritePanelOpen(true)
    setView('focus')
  }

  return (
    <div className="section-list-layout">
      {/* Top bar */}
      <div className="section-list-topbar">
        <div className="section-summary">
          <span className="text-muted">{doc?.title || 'Document'}</span>
          <span className="text-muted">|</span>
          <span className="text-muted">{sections.length} sections</span>
          {cleanCount > 0 && <span className="tag tag-clean">{cleanCount} Clean</span>}
          {touchedCount > 0 && <span className="tag tag-touched">{touchedCount} Ghost Touched</span>}
          {writtenCount > 0 && <span className="tag tag-written">{writtenCount} Ghost Written</span>}
          <span className="text-muted"> | Overall: {avgScore.toFixed(1)}</span>
        </div>
        <div className="section-actions">
          <button className="btn btn-small" onClick={analyzeAll} disabled={loading}>
            [ RE-ANALYZE ALL ]
          </button>
          <button className="btn btn-small" onClick={() => {
            sections.forEach((s, i) => { if ((s.score ?? 0) > 20) rewriteSection(i) })
          }} disabled={loading}>
            [ REWRITE ALL &gt;20 ]
          </button>
          <button className="btn btn-small" onClick={() => setView('preview')}>
            [ PREVIEW ]
          </button>
        </div>
      </div>

      <div className="section-list-body">
        {/* Left TOC */}
        <nav className="section-toc">
          <div className="card-header">Sections</div>
          {sections.map((s, i) => (
            <div
              key={s.id}
              className="toc-item"
              onClick={() => {
                const el = document.getElementById(`section-${i}`)
                el?.scrollIntoView({ behavior: 'smooth' })
              }}
            >
              <ScoreBadge score={s.score} size="small" />
              <span className="toc-heading">{s.heading}</span>
              {s.rewrite.status === 'accepted' && <span className="toc-status">✓</span>}
            </div>
          ))}
        </nav>

        {/* Section cards */}
        <div className="section-cards">
          {sections.map((s, i) => (
            <div key={s.id} id={`section-${i}`} className="card section-card">
              <div className="section-card-header">
                <span className="section-heading">{s.heading}</span>
                <ScoreBadge score={s.score} classification={s.classification} />
              </div>

              <p className="section-preview">
                {s.text.slice(0, 200)}{s.text.length > 200 ? '...' : ''}
              </p>

              {s.patterns.length > 0 && (
                <div className="section-patterns">
                  {s.patterns.slice(0, 3).map((p, j) => (
                    <span key={j} className="pattern-chip">{p.pattern}</span>
                  ))}
                  {s.patterns.length > 3 && (
                    <span className="text-muted">+{s.patterns.length - 3} more</span>
                  )}
                </div>
              )}

              <div className="section-card-actions">
                <button className="btn btn-small" onClick={() => handleFocus(i)}>
                  [ FOCUS ]
                </button>
                <button className="btn btn-small" onClick={() => handleRewrite(i)}>
                  [ REWRITE ]
                </button>
                {s.rewrite.status !== 'pending' && (
                  <span className={`rewrite-status status-${s.rewrite.status}`}>
                    {s.rewrite.status} {s.rewrite.score !== null && `(${s.rewrite.score.toFixed(1)})`}
                  </span>
                )}
              </div>

              {s.loading && <div className="loading-bar" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
