import { useEffect, useState } from 'react'
import { useDocument } from '../context/DocumentContext'
import ScoreBadge from './ScoreBadge'

export default function SectionListView() {
  const {
    sections, loading, analyzeAll, analyzeSection, rewriteSection, setView, setFocusedSection,
    setRewritePanelOpen, updateSectionText, documentAnalysis, document: doc,
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

      {/* Document-level aggregate analysis */}
      {documentAnalysis && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Document Summary (Full-Text Analysis)</span>
            <ScoreBadge score={documentAnalysis.overall_score} classification={documentAnalysis.classification} />
          </div>
          {documentAnalysis.patterns.length > 0 && (
            <div>
              <div className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                Cross-Section Patterns ({documentAnalysis.patterns.length})
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                {documentAnalysis.patterns.map((p: any, i: number) => (
                  <span key={i} className="pattern-chip">
                    {typeof p === 'string' ? p : p.pattern || JSON.stringify(p)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {loading && !documentAnalysis && (
        <div className="card" style={{ marginBottom: '1rem', textAlign: 'center', padding: '1.5rem' }}>
          <div className="spinner" />
          <div className="text-muted" style={{ marginTop: '0.5rem' }}>
            Analyzing full document...
          </div>
        </div>
      )}

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

              <textarea
                className="section-edit-text"
                value={s.text}
                onChange={e => updateSectionText(i, e.target.value)}
                rows={Math.min(8, Math.max(3, Math.ceil(s.text.length / 80)))}
              />

              {s.patterns.length > 0 && (
                <div className="section-patterns">
                  {s.patterns.slice(0, 3).map((p, j) => (
                    <span key={j} className="pattern-chip">{typeof p === 'string' ? p : p.pattern}</span>
                  ))}
                  {s.patterns.length > 3 && (
                    <span className="text-muted">+{s.patterns.length - 3} more</span>
                  )}
                </div>
              )}

              <div className="section-card-actions">
                <button className="btn btn-small" onClick={() => analyzeSection(i)} disabled={s.loading}>
                  {s.loading ? 'Analyzing...' : '[ RE-ANALYZE ]'}
                </button>
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
