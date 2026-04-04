import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAnalysisHistory } from '../services/scoringApi'
import type { Classification, Pattern, SentenceResult } from '../types'
import ScoreBadge from './ScoreBadge'
import ScoreGauge from './ScoreGauge'

interface AnalysisResult {
  overall_score: number
  classification: Classification | null
  patterns: Pattern[]
  sentences: SentenceResult[]
}

interface HistoryEntry {
  id: number
  text: string
  result: AnalysisResult
  source: string
  page_url: string | null
  created_at: string
}

export default function ReportView() {
  const { id } = useParams<{ id: string }>()
  const [entry, setEntry] = useState<HistoryEntry | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getAnalysisHistory(parseInt(id))
      .then(setEntry)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className="card" style={{ marginTop: '1rem', textAlign: 'center', padding: '2rem' }}>
      <div className="spinner" />
      <div className="text-muted" style={{ marginTop: '0.75rem' }}>Loading report...</div>
    </div>
  )

  if (error || !entry) return (
    <div className="card" style={{ marginTop: '1rem', padding: '2rem' }}>
      <div className="text-muted" style={{ marginBottom: '1rem' }}>Report not found or expired.</div>
      <Link to="/" className="btn btn-small">Back to Scanner</Link>
    </div>
  )

  const result = entry.result

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      {/* Source info */}
      {(entry.page_url || entry.source !== 'manual') && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <div className="card-header">Report Info</div>
          {entry.page_url && (
            <div style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>
              <span className="text-muted">Source: </span>
              <a href={entry.page_url} target="_blank" rel="noopener" style={{ color: 'var(--teal-primary)' }}>{entry.page_url}</a>
            </div>
          )}
          <div className="text-muted" style={{ fontSize: '0.75rem' }}>
            {entry.source} &middot; {new Date(entry.created_at).toLocaleString()}
          </div>
        </div>
      )}

      {/* Analysis Results — same layout as InputView */}
      <div className="card" style={{ marginTop: '1rem' }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Analysis Results</span>
          <ScoreBadge score={result.overall_score} classification={result.classification} />
        </div>
        <ScoreGauge score={result.overall_score} />

        {/* Detected Patterns */}
        {result.patterns && result.patterns.length > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <div className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
              Detected Patterns ({result.patterns.length})
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
              {result.patterns.map((p: Pattern, i: number) => (
                <span key={i} className="pattern-chip" title={p.detail || ''}>{p.pattern || JSON.stringify(p)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Sentence-level breakdown */}
        {result.sentences && result.sentences.length > 0 && (
          <div>
            <div className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
              Sentence Scores
            </div>
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {result.sentences.map((s: SentenceResult, i: number) => (
                <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', padding: '0.3rem 0', borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ minWidth: '3rem' }}>
                    <ScoreBadge score={s.score} size="small" />
                  </span>
                  <span className={s.score > 50 ? 'highlight-ai' : s.score < 20 ? 'highlight-human' : ''} style={{ fontSize: '0.8rem', color: 'var(--text-white)' }}>
                    {s.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Original Text */}
      <div className="card" style={{ marginTop: '1rem' }}>
        <div className="card-header">Analyzed Text</div>
        <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word', fontSize: '0.8rem', color: 'var(--text-white)', maxHeight: '300px', overflowY: 'auto', margin: 0 }}>
          {entry.text}
        </pre>
      </div>

      {/* Back button */}
      <div style={{ marginTop: '1rem', marginBottom: '2rem' }}>
        <Link to="/" className="btn btn-small">Back to Scanner</Link>
      </div>
    </div>
  )
}
