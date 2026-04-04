import { useState, useRef, useEffect } from 'react'
import { useDocument } from '../context/DocumentContext'
import ScoreBadge from './ScoreBadge'
import ScoreGauge from './ScoreGauge'
import FidelityScore from './FidelityScore'
import type { VoiceProfile, Pattern, SentenceResult, FidelityScoreResult } from '../types'
import { voiceProfilesApi } from '../services/voiceProfilesApi'
import { scoringApi } from '../services/scoringApi'

interface AnalysisResult {
  overall_score: number
  classification: { category: string; label: string; confidence: string } | null
  patterns: Pattern[]
  sentences: SentenceResult[]
}

type Mode = 'scan' | 'generate'

export default function InputView() {
  const { submitText, uploadFile, selectProfile, selectedProfileId, useAI, setUseAI, loading: docLoading, error: docError } = useDocument()
  const [text, setText] = useState('')
  const [profiles, setProfiles] = useState<VoiceProfile[]>([])
  const [selectedOverlayIds, setSelectedOverlayIds] = useState<number[]>([])
  const [showOverlays, setShowOverlays] = useState(false)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [rewriting, setRewriting] = useState(false)
  const [wasGenerated, setWasGenerated] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<Mode>('scan')
  const [fidelityResult, setFidelityResult] = useState<FidelityScoreResult | null>(null)
  const [scoringFidelity, setScoringFidelity] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const baselines = profiles
  const overlays = profiles.filter(p => p.profile_type === 'overlay')

  useEffect(() => {
    voiceProfilesApi.list()
      .then((data: VoiceProfile[]) => {
        setProfiles(data)
        if (!selectedProfileId) {
          const first = data[0]
          if (first) selectProfile(first.id)
        }
      })
      .catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // When AI is turned off, switch back to scan mode (keep text)
  useEffect(() => {
    if (!useAI && mode === 'generate') {
      setMode('scan')
    }
  }, [useAI]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleModeSwitch = (newMode: Mode) => {
    if (newMode === mode) return
    setAnalysis(null)
    setMode(newMode)
  }

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

  const handleGenerate = async () => {
    if (!text.trim()) return
    setGenerating(true)
    setError(null)
    setAnalysis(null)
    try {
      const res = await fetch('/api/rewrite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.trim(),
          use_ai: true,
          voice_profile_id: selectedProfileId || undefined,
          overlay_ids: selectedOverlayIds.length > 0 ? selectedOverlayIds : undefined,
          comment: 'GENERATE: Create original content from this prompt. Do NOT rewrite it — use it as instructions for what to write about.',
        }),
      })
      if (!res.ok) throw new Error('Generation failed')
      const data = await res.json()
      const generated = data.rewritten_text || data.text || ''
      // Put generated text in the box
      setText(generated)
      // Switch to scan mode and auto-analyze
      setMode('scan')
      setWasGenerated(true)
      setGenerating(false)
      // Auto-analyze the generated text
      setAnalyzing(true)
      try {
        const analyzeRes = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: generated, use_ai: useAI }),
        })
        if (analyzeRes.ok) {
          const analyzeData = await analyzeRes.json()
          setAnalysis({
            overall_score: analyzeData.overall_score,
            classification: analyzeData.classification || null,
            patterns: analyzeData.detected_patterns || analyzeData.patterns || [],
            sentences: analyzeData.sentences || [],
          })
        }
      } catch { /* analysis failed, text is still there */ }
      setAnalyzing(false)
    } catch (e: any) {
      setError(e.message)
      setGenerating(false)
    }
  }

  const handleRewrite = async () => {
    if (!text.trim()) return
    setRewriting(true)
    setError(null)
    setAnalysis(null)
    try {
      const res = await fetch('/api/rewrite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.trim(),
          use_ai: true,
          voice_profile_id: selectedProfileId || undefined,
          overlay_ids: selectedOverlayIds.length > 0 ? selectedOverlayIds : undefined,
          comment: 'Rewrite this text to sound more human, following the voice profile and anti-AI rules',
        }),
      })
      if (!res.ok) throw new Error('Rewrite failed')
      const data = await res.json()
      const rewritten = data.rewritten_text || data.text || ''
      setText(rewritten)
      setRewriting(false)
      // Auto-analyze the rewritten text
      setAnalyzing(true)
      try {
        const analyzeRes = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: rewritten, use_ai: useAI }),
        })
        if (analyzeRes.ok) {
          const analyzeData = await analyzeRes.json()
          setAnalysis({
            overall_score: analyzeData.overall_score,
            classification: analyzeData.classification || null,
            patterns: analyzeData.detected_patterns || analyzeData.patterns || [],
            sentences: analyzeData.sentences || [],
          })
        }
      } catch { /* ignore */ }
      setAnalyzing(false)
    } catch (e: any) {
      setError(e.message)
      setRewriting(false)
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

  const isBusy = analyzing || generating || rewriting

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
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                <label className="vp-scanner-label" style={{ margin: 0 }}>Overlays</label>
                <button
                  className="btn btn-small"
                  onClick={() => setShowOverlays(v => !v)}
                  style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem' }}
                >
                  {showOverlays ? '[ Hide ]' : `[ ${selectedOverlayIds.length} selected ]`}
                </button>
              </div>
              {showOverlays && (
                <div className="vp-overlay-list" style={{ flexDirection: 'column', gap: '0.4rem' }}>
                  {overlays.map(p => (
                    <label key={p.id} className="vp-overlay-check" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.8rem' }}>
                      <input
                        type="checkbox"
                        checked={selectedOverlayIds.includes(p.id)}
                        onChange={() => toggleOverlay(p.id)}
                        style={{ accentColor: 'var(--cyan-info)' }}
                      />
                      <span>{p.name}</span>
                    </label>
                  ))}
                </div>
              )}
              {selectedOverlayIds.length > 0 && !showOverlays && (
                <div className="vp-overlay-list" style={{ marginTop: '0.3rem' }}>
                  {selectedOverlayIds.map((id, idx) => {
                    const p = overlays.find(o => o.id === id)
                    if (!p) return null
                    return (
                      <div key={id} className="vp-overlay-chip selected" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <span style={{ cursor: 'grab', opacity: 0.6 }}>≡</span>
                        {idx > 0 && (
                          <button className="btn btn-small" style={{ padding: '0 0.2rem', fontSize: '0.65rem', lineHeight: 1 }}
                            onClick={() => { const next = [...selectedOverlayIds]; [next[idx-1], next[idx]] = [next[idx], next[idx-1]]; setSelectedOverlayIds(next) }}>▲</button>
                        )}
                        {idx < selectedOverlayIds.length - 1 && (
                          <button className="btn btn-small" style={{ padding: '0 0.2rem', fontSize: '0.65rem', lineHeight: 1 }}
                            onClick={() => { const next = [...selectedOverlayIds]; [next[idx], next[idx+1]] = [next[idx+1], next[idx]]; setSelectedOverlayIds(next) }}>▼</button>
                        )}
                        <span>{p.name}</span>
                        <button className="btn btn-small" style={{ padding: '0 0.2rem', fontSize: '0.65rem', lineHeight: 1 }} onClick={() => toggleOverlay(id)}>×</button>
                      </div>
                    )
                  })}
                </div>
              )}
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

      {/* Scan / Generate mode toggle — only when AI is on */}
      {useAI && (
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
          <div className="scanner-mode-toggle">
            <button
              className={`scanner-mode-btn ${mode === 'scan' ? 'scanner-mode-active' : ''}`}
              onClick={() => handleModeSwitch('scan')}
              disabled={isBusy}
            >
              SCAN
            </button>
            <button
              className={`scanner-mode-btn ${mode === 'generate' ? 'scanner-mode-active' : ''}`}
              onClick={() => handleModeSwitch('generate')}
              disabled={isBusy}
            >
              GENERATE
            </button>
          </div>
        </div>
      )}

      {/* Text Input */}
      <div className="card">
        <div className="card-header">
          {mode === 'generate' ? 'Describe Prompt' : 'Paste Text'}
        </div>
        <textarea
          value={text}
          onChange={e => { setText(e.target.value); if (mode === 'scan') { setAnalysis(null); setWasGenerated(false) } }}
          placeholder={mode === 'generate'
            ? 'Write a prompt for the AI to generate content with your voice and following all the anti-AI rules you\'ve set...'
            : 'Paste text to analyze for AI patterns...'}
          className="text-input"
          rows={12}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
          <span className="text-muted">{wordCount} words</span>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            {mode === 'generate' ? (
              <button
                className="btn"
                onClick={handleGenerate}
                disabled={isBusy || !text.trim()}
                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
              >
                {generating && <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />}
                {generating ? 'Generating...' : '[ GENERATE ]'}
              </button>
            ) : (
              <>
                {wasGenerated && useAI && (
                  <button
                    className="btn"
                    onClick={handleRewrite}
                    disabled={isBusy || !text.trim()}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                  >
                    {rewriting && <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />}
                    {rewriting ? 'Rewriting...' : '[ REWRITE ]'}
                  </button>
                )}
                <button
                  className="btn"
                  onClick={handleAnalyze}
                  disabled={isBusy || !text.trim()}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  {analyzing && <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />}
                  {analyzing ? 'Analyzing...' : analysis ? '[ RE-ANALYZE ]' : '[ ANALYZE ]'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Loading spinner */}
      {docLoading && (
        <div className="card" style={{ marginTop: '1rem', textAlign: 'center', padding: '2rem' }}>
          <div className="spinner" />
          <div className="text-muted" style={{ marginTop: '0.75rem' }}>
            Splitting into sections...
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

      {/* Fidelity Scoring — available after rewrite/generate */}
      {analysis && !analyzing && selectedProfileId && (wasGenerated || rewriting === false) && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Voice Fidelity</span>
            <button
              className="btn btn-small"
              onClick={async () => {
                if (!text.trim() || !selectedProfileId) return
                setScoringFidelity(true)
                setFidelityResult(null)
                try {
                  const data = await scoringApi.scoreFidelity(text, selectedProfileId, 'quantitative')
                  setFidelityResult(data)
                } catch (err: any) {
                  console.error('Fidelity scoring error:', err)
                  setError(err.message || 'Fidelity scoring failed')
                }
                finally { setScoringFidelity(false) }
              }}
              disabled={scoringFidelity || !text.trim()}
            >
              {scoringFidelity ? 'Scoring...' : '[ Score Fidelity ]'}
            </button>
          </div>
          {fidelityResult && <FidelityScore result={fidelityResult} />}
        </div>
      )}

      {/* File Upload — this goes to sections view (scan mode only) */}
      {mode === 'scan' && (
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
      )}

      {(error || docError) && (
        <div className="error-message" style={{ marginTop: '1rem' }}>
          {error || docError}
        </div>
      )}
    </div>
  )
}
