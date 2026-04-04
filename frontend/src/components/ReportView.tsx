import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAnalysisHistory } from '../services/scoringApi'
import type { Classification, Pattern, SentenceResult, ClassificationBoundaries, EnrichedAnalyzeResponse } from '../types'
import ScoreBadge from './ScoreBadge'
import ScoreGauge from './ScoreGauge'
import AnalysisReport from './AnalysisReport'

interface Tiers {
  sentence_score: number
  paragraph_score: number
  document_score: number
}

interface AnalysisResult {
  overall_score: number
  classification: Classification | null
  patterns: Pattern[]
  sentences: SentenceResult[]
  tiers?: Tiers
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
  const [boundaries, setBoundaries] = useState<ClassificationBoundaries>({ clean_upper: 20, ghost_written_lower: 40 })

  useEffect(() => {
    if (!id) return
    getAnalysisHistory(parseInt(id))
      .then(setEntry)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    fetch('/api/rules/config/classification')
      .then(r => r.json())
      .then(data => {
        if (data.clean_upper && data.ghost_written_lower) {
          setBoundaries({ clean_upper: data.clean_upper, ghost_written_lower: data.ghost_written_lower })
        }
      })
      .catch(() => {})
  }, [])

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

        <AnalysisReport data={result as EnrichedAnalyzeResponse} boundaries={boundaries} />
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
