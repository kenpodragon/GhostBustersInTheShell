import { useState } from 'react'

interface SentenceResult {
  index: number
  text: string
  score: number
  patterns: Array<{ pattern: string; detail: string }>
}

interface AnalysisResult {
  overall_score: number
  sentences: SentenceResult[]
  detected_patterns: Array<{ pattern: string; detail: string }>
}

function getScoreClass(score: number): string {
  if (score < 30) return 'score-low'
  if (score < 60) return 'score-medium'
  if (score < 80) return 'score-high'
  return 'score-critical'
}

function getScoreLabel(score: number): string {
  if (score < 30) return 'LIKELY HUMAN'
  if (score < 60) return 'MIXED SIGNALS'
  if (score < 80) return 'LIKELY AI'
  return 'AI DETECTED'
}

function AnalyzePage() {
  const [text, setText] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleAnalyze = async () => {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Analysis failed')
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/analyze', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Analysis failed')
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
        {'>'} AI Detection Scanner_
      </h1>

      <div className="card">
        <div className="card-header">Input Text</div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste text here for AI detection analysis..."
          rows={10}
        />
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', alignItems: 'center' }}>
          <button className="btn" onClick={handleAnalyze} disabled={loading || !text.trim()}>
            {loading ? 'Scanning' : 'Scan Text'}
          </button>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>or</span>
          <label className="btn" style={{ cursor: 'pointer' }}>
            Upload File
            <input type="file" accept=".pdf,.docx,.txt" onChange={handleFileUpload} hidden />
          </label>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            {text.split(/\s+/).filter(Boolean).length} words
          </span>
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--red-alert)' }}>
          <span style={{ color: 'var(--red-alert)' }}>ERROR: {error}</span>
        </div>
      )}

      {result && (
        <>
          <div className="card">
            <div className="card-header">Detection Result</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span className={`score-badge ${getScoreClass(result.overall_score)}`}>
                {result.overall_score}%
              </span>
              <span style={{ color: 'var(--text-white)', fontSize: '0.85rem' }}>
                {getScoreLabel(result.overall_score)}
              </span>
            </div>
          </div>

          <div className="card">
            <div className="card-header">Sentence Analysis</div>
            <div style={{ fontSize: '0.85rem', lineHeight: '1.8' }}>
              {result.sentences.map((s) => (
                <span
                  key={s.index}
                  className={s.score > 50 ? 'highlight-ai' : s.score < 20 ? 'highlight-human' : ''}
                  title={`Score: ${s.score}% | ${s.patterns.map(p => p.detail).join(', ') || 'No patterns detected'}`}
                >
                  {s.text}{' '}
                </span>
              ))}
            </div>
          </div>

          {result.detected_patterns.length > 0 && (
            <div className="card">
              <div className="card-header">Detected Patterns</div>
              <div className="terminal-output">
                {result.detected_patterns.map((p, i) => (
                  <div key={i}>
                    <span className="warning">[!]</span> {p.pattern}: {p.detail}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default AnalyzePage
