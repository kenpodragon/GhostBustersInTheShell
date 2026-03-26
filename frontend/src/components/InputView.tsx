import { useState, useRef, useEffect } from 'react'
import { useDocument } from '../context/DocumentContext'
import ScoreBadge from './ScoreBadge'
import ScoreGauge from './ScoreGauge'
import type { VoiceProfile, Pattern, SentenceResult } from '../types'
import { voiceProfilesApi } from '../services/voiceProfilesApi'

interface AnalysisResult {
  overall_score: number
  classification: { category: string; label: string; confidence: string } | null
  patterns: Pattern[]
  sentences: SentenceResult[]
}

export default function InputView() {
  const { submitText, uploadFile, selectProfile, selectedProfileId, useAI, setUseAI, loading: docLoading, error: docError } = useDocument()
  const [text, setText] = useState('')
  const [profiles, setProfiles] = useState<VoiceProfile[]>([])
  const [selectedOverlayIds, setSelectedOverlayIds] = useState<number[]>([])
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const baselines = profiles.filter(p => p.profile_type === 'baseline')
  const overlays = profiles.filter(p => p.profile_type === 'overlay')

  useEffect(() => {
    voiceProfilesApi.list()
      .then((data: VoiceProfile[]) => {
        setProfiles(data)
        if (!selectedProfileId) {
          const firstBaseline = data.find(p => p.profile_type === 'baseline')
          if (firstBaseline) selectProfile(firstBaseline.id)
        }
      })
      .catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleOverlay = (id: number) => {
    setSelectedOverlayIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0

  const handleAnalyze = async () => {
    if (!text.trim()) return

    // Long text (>2000 chars) → section splitting workflow
    if (text.trim().length > 2000) {
      submitText(text.trim())
      return
    }

    // Short text → inline analysis, stay on this page
    setAnalyzing(true)
    setError(null)
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim(), use_ai: useAI }),
      })
      if (!res.ok) throw new Error('Analysis failed')
      const data = await res.json()
      setAnalysis({
        overall_score: data.overall_score,
        classification: data.classification || null,
        patterns: data.detected_patterns || data.patterns || [],
        sentences: data.sentences || [],
      })
    } catch (e: any) {
      setError(e.message)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) uploadFile(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) uploadFile(file)
  }

  return (
    <div>
      <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
        {'>'} GhostBusters Scanner_
      </h1>

      {/* Settings Row: Voice Profile + AI Toggle */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="vp-scanner-selector">
          <div className="vp-scanner-field">
            <label className="vp-scanner-label">Baseline Profile</label>
            <select
              value={selectedProfileId ?? ''}
              onChange={e => selectProfile(e.target.value ? Number(e.target.value) : null)}
              className="select-input"
            >
              <option value="">— none —</option>
              {baselines.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          {overlays.length > 0 && (
            <div className="vp-scanner-field">
              <label className="vp-scanner-label">Overlays</label>
              <div className="vp-overlay-list">
                {overlays.map(p => (
                  <button
                    key={p.id}
                    className={`vp-overlay-chip ${selectedOverlayIds.includes(p.id) ? 'selected' : ''}`}
                    onClick={() => toggleOverlay(p.id)}
                  >
                    {selectedOverlayIds.includes(p.id) ? '✓ ' : ''}{p.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <label className="vp-scanner-label">AI Enhanced</label>
            <button
              className={`toggle-btn ${useAI ? 'toggle-on' : 'toggle-off'}`}
              onClick={() => setUseAI(!useAI)}
            >
              {useAI ? '[ ON ]' : '[ OFF ]'}
            </button>
          </div>
        </div>
      </div>

      {/* Text Input — stays editable, analyze shows results below */}
      <div className="card">
        <div className="card-header">Paste Text</div>
        <textarea
          value={text}
          onChange={e => { setText(e.target.value); setAnalysis(null) }}
          placeholder="Paste text to analyze for AI patterns..."
          className="text-input"
          rows={12}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
          <span className="text-muted">{wordCount} words</span>
          <button className="btn" onClick={handleAnalyze} disabled={analyzing || !text.trim()}>
            {analyzing ? 'Analyzing...' : analysis ? '[ RE-ANALYZE ]' : '[ ANALYZE ]'}
          </button>
        </div>
      </div>

      {/* Loading spinner */}
      {(analyzing || docLoading) && (
        <div className="card" style={{ marginTop: '1rem', textAlign: 'center', padding: '2rem' }}>
          <div className="spinner" />
          <div className="text-muted" style={{ marginTop: '0.75rem' }}>
            {docLoading ? 'Splitting into sections...' : 'Analyzing text...'}
          </div>
        </div>
      )}

      {/* Analysis Results — shown inline below text */}
      {analysis && !analyzing && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Analysis Results</span>
            <ScoreBadge score={analysis.overall_score} classification={analysis.classification} />
          </div>
          <ScoreGauge score={analysis.overall_score} />

          {/* Detected Patterns */}
          {analysis.patterns.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <div className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                Detected Patterns ({analysis.patterns.length})
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                {analysis.patterns.map((p, i) => (
                  <span key={i} className="pattern-chip" title={typeof p === 'string' ? '' : p.detail || ''}>{typeof p === 'string' ? p : p.pattern || JSON.stringify(p)}</span>
                ))}
              </div>
            </div>
          )}

          {/* Sentence-level breakdown */}
          {analysis.sentences.length > 0 && (
            <div>
              <div className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                Sentence Scores
              </div>
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {analysis.sentences.map((s, i) => (
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
      )}

      {/* File Upload — this goes to sections view */}
      <div
        className="file-drop-zone"
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        style={{ marginTop: '1rem' }}
      >
        <p>Drop a file here or click to upload</p>
        <p className="text-muted">.pdf, .docx, .txt — opens section view</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFile}
          style={{ display: 'none' }}
        />
      </div>

      {(error || docError) && (
        <div className="error-message" style={{ marginTop: '1rem' }}>
          {error || docError}
        </div>
      )}
    </div>
  )
}
