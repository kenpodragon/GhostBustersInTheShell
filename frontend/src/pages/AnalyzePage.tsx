import { useState, useEffect } from 'react'

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
  _analysis_mode?: string
}

interface AIStatus {
  ai_enabled: boolean
  ai_provider: string
  ai_runtime_available: boolean
  ai_runtime_error: string | null
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
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null)
  const [togglingAi, setTogglingAi] = useState(false)

  useEffect(() => {
    fetchAiStatus()
  }, [])

  const fetchAiStatus = async () => {
    try {
      const res = await fetch('/api/settings')
      if (res.ok) {
        const data = await res.json()
        setAiStatus(data)
      }
    } catch {
      // Settings not available — AI status unknown
    }
  }

  const toggleAi = async () => {
    if (!aiStatus || togglingAi) return
    setTogglingAi(true)
    try {
      const res = await fetch('/api/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ai_enabled: !aiStatus.ai_enabled }),
      })
      if (res.ok) {
        const data = await res.json()
        setAiStatus(data)
      }
    } catch {
      // ignore
    } finally {
      setTogglingAi(false)
    }
  }

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
      fetchAiStatus()  // Refresh status in case of runtime disable
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
      fetchAiStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const aiActive = aiStatus?.ai_enabled && aiStatus?.ai_runtime_available

  return (
    <div>
      <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
        {'>'} AI Detection Scanner_
      </h1>

      {/* AI Status Indicator */}
      {aiStatus && (
        <div className="card" style={{ padding: '0.5rem 1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: aiActive ? 'var(--green-glow)' : 'var(--text-muted)',
                boxShadow: aiActive ? '0 0 6px var(--green-glow)' : 'none',
              }} />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-white)' }}>
                AI Engine: {aiActive ? `ON (${aiStatus.ai_provider})` : 'OFF'}
                {aiStatus.ai_enabled && !aiStatus.ai_runtime_available && (
                  <span style={{ color: 'var(--red-alert)', marginLeft: '0.5rem' }}>
                    [Runtime disabled: {aiStatus.ai_runtime_error}]
                  </span>
                )}
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {aiActive ? 'Claude-powered analysis' : 'Heuristic analysis only'}
              </span>
            </div>
            <button
              className="btn"
              onClick={toggleAi}
              disabled={togglingAi}
              style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
            >
              {togglingAi ? '...' : aiStatus.ai_enabled ? 'Disable AI' : 'Enable AI'}
            </button>
          </div>
        </div>
      )}

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
              {result._analysis_mode && (
                <span style={{
                  fontSize: '0.7rem',
                  color: result._analysis_mode === 'ai' ? 'var(--green-glow)' : 'var(--text-muted)',
                  border: `1px solid ${result._analysis_mode === 'ai' ? 'var(--green-glow)' : 'var(--text-muted)'}`,
                  padding: '0.1rem 0.4rem',
                  borderRadius: '3px',
                }}>
                  {result._analysis_mode === 'ai' ? 'AI-powered' : 'Heuristic'}
                </span>
              )}
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
