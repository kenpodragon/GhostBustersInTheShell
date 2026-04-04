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

  if (loading) return <div className="report-loading">Loading report...</div>
  if (error) return <div className="report-error">Report not found or expired.</div>
  if (!entry) return <div className="report-error">Report not found.</div>

  const result = entry.result

  return (
    <div className="report-view">
      <div className="report-header">
        <h2>Analysis Report</h2>
        {entry.page_url && (
          <div className="report-source">
            Source: <a href={entry.page_url} target="_blank" rel="noopener">{entry.page_url}</a>
          </div>
        )}
        <div className="report-meta">
          {entry.source} &middot; {new Date(entry.created_at).toLocaleString()}
        </div>
      </div>

      <div className="report-score-section">
        <ScoreGauge score={result.overall_score} />
        <ScoreBadge score={result.overall_score} classification={result.classification} />
      </div>

      {result.patterns && result.patterns.length > 0 && (
        <div className="report-patterns">
          <h3>Detected Patterns ({result.patterns.length})</h3>
          <div className="pattern-list">
            {result.patterns.map((p: Pattern, i: number) => (
              <div key={i} className="pattern-chip" title={p.detail}>
                {p.pattern}
              </div>
            ))}
          </div>
        </div>
      )}

      {result.sentences && result.sentences.length > 0 && (
        <div className="report-sentences">
          <h3>Sentence Analysis</h3>
          {result.sentences.map((s: SentenceResult, i: number) => (
            <div key={i} className={`sentence-row ${s.score > 30 ? 'sentence-hot' : s.score > 15 ? 'sentence-warm' : 'sentence-clean'}`}>
              <span className="sentence-score">{s.score.toFixed(1)}</span>
              <span className="sentence-text">{s.text}</span>
            </div>
          ))}
        </div>
      )}

      <div className="report-original-text">
        <h3>Analyzed Text</h3>
        <pre className="report-text-block">{entry.text}</pre>
      </div>

      <div className="report-footer">
        <Link to="/" className="action-btn secondary">Back to Scanner</Link>
      </div>
    </div>
  )
}
