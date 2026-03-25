import { useDocument } from '../context/DocumentContext'
import ScoreBadge from './ScoreBadge'

export default function PreviewView() {
  const { sections, setView, setFocusedSection, exportMarkdown } = useDocument()

  const avgScore = sections.length > 0
    ? sections.reduce((sum, s) => sum + (s.score ?? 0), 0) / sections.length
    : 0

  const handleExport = (format: 'md' | 'txt') => {
    const content = exportMarkdown()
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `document.${format}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleEditSection = (index: number) => {
    setFocusedSection(index)
    setView('focus')
  }

  return (
    <div className="preview-view">
      <div className="preview-header">
        <button className="btn btn-small" onClick={() => setView('sections')}>
          [ ← SECTIONS ]
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span className="text-muted">Overall: {avgScore.toFixed(1)}</span>
          <button className="btn btn-small" onClick={() => handleExport('md')}>
            [ EXPORT .MD ]
          </button>
          <button className="btn btn-small" onClick={() => handleExport('txt')}>
            [ EXPORT .TXT ]
          </button>
        </div>
      </div>

      <div className="preview-body">
        {sections.map((s, i) => {
          const text = s.rewrite.status === 'accepted' && s.rewrite.text
            ? s.rewrite.text
            : s.text
          const isRewritten = s.rewrite.status === 'accepted'
          const isEditing = s.rewrite.status === 'editing'

          return (
            <div key={s.id} className={`preview-section ${!isRewritten ? 'preview-original' : ''}`}>
              <div className="preview-section-header">
                <span className="section-heading">{s.heading}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ScoreBadge score={isRewritten ? (s.rewrite.score ?? s.score) : s.score} size="small" />
                  {isRewritten && <span className="tag tag-clean">rewritten</span>}
                  {isEditing && <span className="tag tag-touched">editing</span>}
                  {!isRewritten && !isEditing && <span className="text-muted">original</span>}
                  <button className="btn btn-small" onClick={() => handleEditSection(i)}>
                    [ EDIT ]
                  </button>
                </div>
              </div>
              <div className="preview-section-text">{text}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
