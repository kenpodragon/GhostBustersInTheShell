import { useState } from 'react'
import { useDocument } from '../context/DocumentContext'
import ScoreBadge from './ScoreBadge'

export default function RewritePanel() {
  const {
    sections, focusedSectionIndex, rewriteSection, acceptRewrite,
    rejectRewrite, updateEditedText, updateComment, regenerateRewrite,
    autoOptimize, setRewritePanelOpen,
  } = useDocument()

  const [threshold, setThreshold] = useState(20)
  const [optimizing, setOptimizing] = useState(false)

  const index = focusedSectionIndex ?? 0
  const section = sections[index]
  if (!section) return null

  const { rewrite } = section

  const handleAutoOptimize = async () => {
    setOptimizing(true)
    await autoOptimize(index, threshold, rewrite.comment)
    setOptimizing(false)
  }

  return (
    <div className="rewrite-panel">
      <div className="rewrite-panel-header">
        <h3 style={{ fontSize: '0.9rem', margin: 0 }}>Rewrite: {section.heading}</h3>
        <button className="btn btn-small" onClick={() => setRewritePanelOpen(false)}>
          [ CLOSE ]
        </button>
      </div>

      <div className="rewrite-split">
        {/* Left: Original */}
        <div className="rewrite-side">
          <div className="rewrite-side-header">
            <span>Original</span>
            <ScoreBadge score={section.score} classification={section.classification} size="small" />
          </div>
          <div className="rewrite-text">{section.text}</div>
        </div>

        {/* Right: Rewritten */}
        <div className="rewrite-side">
          <div className="rewrite-side-header">
            <span>Rewritten</span>
            {rewrite.score !== null && (
              <ScoreBadge score={rewrite.score} classification={rewrite.classification} size="small" />
            )}
          </div>
          {rewrite.status === 'editing' ? (
            <textarea
              className="text-input rewrite-edit-area"
              value={rewrite.editedText || ''}
              onChange={e => updateEditedText(index, e.target.value)}
              rows={10}
            />
          ) : rewrite.text ? (
            <div className="rewrite-text">{rewrite.text}</div>
          ) : (
            <div className="rewrite-text text-muted">
              Click REWRITE to generate a humanized version.
            </div>
          )}
        </div>
      </div>

      {/* Comment box */}
      <div className="rewrite-comment">
        <textarea
          className="text-input"
          value={rewrite.comment}
          onChange={e => updateComment(index, e.target.value)}
          placeholder="Add instructions for the rewriter (e.g., 'keep the technical terms', 'make it more casual')"
          rows={2}
        />
      </div>

      {/* Action buttons */}
      <div className="rewrite-actions">
        {!rewrite.text ? (
          <button
            className="btn"
            onClick={() => rewriteSection(index)}
            disabled={section.loading}
          >
            {section.loading ? 'Rewriting...' : '[ REWRITE ]'}
          </button>
        ) : (
          <>
            <button className="btn btn-accept" onClick={() => acceptRewrite(index)}>
              [ ACCEPT ]
            </button>
            <button className="btn btn-reject" onClick={() => rejectRewrite(index)}>
              [ REJECT ]
            </button>
            <button
              className="btn"
              onClick={() => regenerateRewrite(index)}
              disabled={section.loading}
            >
              {section.loading ? 'Rewriting...' : `[ REGENERATE (${rewrite.iterations}) ]`}
            </button>
          </>
        )}

        <div className="auto-optimize">
          <button
            className="btn"
            onClick={handleAutoOptimize}
            disabled={section.loading || optimizing}
          >
            {optimizing ? 'Optimizing...' : '[ AUTO-OPTIMIZE ]'}
          </button>
          <label className="text-muted">
            Target: &lt;
            <input
              type="number"
              className="threshold-input"
              value={threshold}
              onChange={e => setThreshold(Number(e.target.value))}
              min={0}
              max={100}
            />
          </label>
        </div>

        <span className="text-muted" style={{ marginLeft: 'auto' }}>
          {rewrite.iterations > 0 && `${rewrite.iterations} iteration(s)`}
        </span>
      </div>

      {section.loading && <div className="loading-bar" />}
    </div>
  )
}
