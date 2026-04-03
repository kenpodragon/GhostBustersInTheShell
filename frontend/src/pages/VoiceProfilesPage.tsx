import { useState, useEffect, useCallback, useRef } from 'react'
import type { VoiceProfile, ProfileElement, ProfilePrompt, ProfileSnapshot, FidelityScoreResult, CompletenessData } from '../types'
import { voiceProfilesApi } from '../services/voiceProfilesApi'
import { scoringApi } from '../services/scoringApi'
import FidelityScore from '../components/FidelityScore'
import CorpusManager from '../components/CorpusManager'
import CompletenessBar from '../components/CompletenessBar'
import ConsolidationView from '../components/ConsolidationView'
import ReparseView from '../components/ReparseView'

type TabId = 'elements' | 'prompts' | 'finetune' | 'freeze' | 'testvox' | 'corpus' | 'consolidate' | 'reparse'
const TABS: { id: TabId; label: string }[] = [
  { id: 'elements', label: 'Style Elements' },
  { id: 'prompts', label: 'Prompts' },
  { id: 'finetune', label: 'Fine-Tune' },
  { id: 'freeze', label: 'Freeze Voice' },
  { id: 'testvox', label: 'Test Voice' },
  { id: 'corpus', label: 'Corpus' },
  { id: 'consolidate', label: 'AI Observations' },
  { id: 'reparse', label: 'Re-parse' },
]

const BASELINE_NAME = 'Baseline'

/** Check if a profile is the system baseline (id=1 or name match) */
function isBaseline(p: VoiceProfile): boolean {
  return p.id === 1 || p.name === BASELINE_NAME
}

const CATEGORIES = ['lexical', 'character', 'syntactic', 'structural', 'content', 'idiosyncratic'] as const

/** System-defined elements — canonical set with descriptions and defaults */
const SYSTEM_ELEMENTS: { name: string; category: string; element_type: 'directional' | 'metric'; direction?: 'more' | 'less'; description: string; defaultWeight: number; defaultTarget?: number }[] = [
  // Lexical
  { name: 'vocabulary_richness', category: 'lexical', element_type: 'directional', direction: 'more', description: 'Type-token ratio — variety of unique words used', defaultWeight: 0.5 },
  { name: 'avg_word_length', category: 'lexical', element_type: 'metric', description: 'Average number of characters per word', defaultWeight: 0.5, defaultTarget: 4.5 },
  { name: 'contraction_rate', category: 'lexical', element_type: 'directional', direction: 'more', description: 'How often contractions appear (don\'t, can\'t, etc.)', defaultWeight: 0.5 },
  { name: 'long_word_frequency', category: 'lexical', element_type: 'directional', direction: 'less', description: 'Ratio of words longer than 6 characters', defaultWeight: 0.5 },
  // Syntactic
  { name: 'avg_sentence_length', category: 'syntactic', element_type: 'metric', description: 'Average words per sentence', defaultWeight: 0.5, defaultTarget: 18 },
  { name: 'sentence_length_stddev', category: 'syntactic', element_type: 'metric', description: 'Variation in sentence lengths — higher means more variety', defaultWeight: 0.5, defaultTarget: 8 },
  { name: 'short_sentence_ratio', category: 'syntactic', element_type: 'directional', direction: 'more', description: 'Proportion of sentences under 10 words', defaultWeight: 0.5 },
  { name: 'long_sentence_ratio', category: 'syntactic', element_type: 'directional', direction: 'less', description: 'Proportion of sentences over 25 words', defaultWeight: 0.5 },
  { name: 'passive_voice_rate', category: 'syntactic', element_type: 'directional', direction: 'less', description: 'How often passive voice constructions appear', defaultWeight: 0.5 },
  // Idiosyncratic
  { name: 'em_dash_usage', category: 'idiosyncratic', element_type: 'directional', direction: 'less', description: 'Frequency of em dashes (—) per sentence', defaultWeight: 0.5 },
  { name: 'semicolon_usage', category: 'idiosyncratic', element_type: 'directional', direction: 'more', description: 'Frequency of semicolons per sentence', defaultWeight: 0.5 },
  { name: 'ellipsis_usage', category: 'idiosyncratic', element_type: 'directional', direction: 'more', description: 'Frequency of ellipses (...) per sentence', defaultWeight: 0.5 },
  { name: 'exclamation_rate', category: 'idiosyncratic', element_type: 'directional', direction: 'less', description: 'Proportion of sentences ending in exclamation marks', defaultWeight: 0.5 },
  { name: 'parenthetical_usage', category: 'idiosyncratic', element_type: 'directional', direction: 'more', description: 'Frequency of parenthetical asides', defaultWeight: 0.5 },
  { name: 'rhetorical_question_rate', category: 'idiosyncratic', element_type: 'directional', direction: 'more', description: 'Proportion of sentences that are questions', defaultWeight: 0.5 },
  { name: 'first_person_usage', category: 'idiosyncratic', element_type: 'directional', direction: 'more', description: 'Frequency of I/me/my/we pronouns', defaultWeight: 0.5 },
  { name: 'second_person_usage', category: 'idiosyncratic', element_type: 'directional', direction: 'less', description: 'Frequency of you/your pronouns', defaultWeight: 0.5 },
  // Readability (metric)
  { name: 'flesch_kincaid_grade', category: 'idiosyncratic', element_type: 'metric', description: 'Grade level required to understand the text (US school grades)', defaultWeight: 0.5, defaultTarget: 10 },
  { name: 'flesch_reading_ease', category: 'idiosyncratic', element_type: 'metric', description: 'Reading ease score — higher is easier (0-100)', defaultWeight: 0.5, defaultTarget: 60 },
  { name: 'gunning_fog_index', category: 'idiosyncratic', element_type: 'metric', description: 'Years of education needed to understand (like grade level)', defaultWeight: 0.5, defaultTarget: 12 },
  { name: 'coleman_liau_index', category: 'idiosyncratic', element_type: 'metric', description: 'Grade level estimate based on characters per word', defaultWeight: 0.5, defaultTarget: 10 },
  { name: 'smog_index', category: 'idiosyncratic', element_type: 'metric', description: 'Years of education needed — based on polysyllabic words', defaultWeight: 0.5, defaultTarget: 10 },
  { name: 'automated_readability_index', category: 'idiosyncratic', element_type: 'metric', description: 'Grade level estimate from characters and sentences', defaultWeight: 0.5, defaultTarget: 10 },
]


// ─── Style Elements Tab ───────────────────────────────────────────────────────
function ElementsTab({ profileId }: { profileId: number }) {
  const [elements, setElements] = useState<ProfileElement[]>([])
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    voiceProfilesApi.getElements(profileId).then(data => {
      const arr = Array.isArray(data) ? data : []
      setElements(arr.map((e: any) => ({ ...e, tags: Array.isArray(e.tags) ? e.tags : [] })))
    }).catch(() => setElements([]))
  }, [profileId])

  // Auto-save after 800ms of inactivity
  const scheduleAutoSave = useCallback((updated: ProfileElement[]) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(async () => {
      try {
        await voiceProfilesApi.updateElements(profileId, updated)
        setMsg('Auto-saved.')
        setTimeout(() => setMsg(''), 2000)
      } catch { setMsg('Save failed.') }
    }, 800)
  }, [profileId])

  // Cleanup timer on unmount
  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current) }, [])

  const updateElement = (name: string, patch: Partial<ProfileElement>) => {
    setElements(prev => {
      const next = prev.map(e => e.name === name ? { ...e, ...patch } : e)
      scheduleAutoSave(next)
      return next
    })
  }

  const toggleElement = (def: typeof SYSTEM_ELEMENTS[0], enabled: boolean) => {
    setElements(prev => {
      let next: ProfileElement[]
      if (enabled) {
        // Add with defaults
        next = [...prev, {
          id: Date.now(),
          name: def.name,
          category: def.category as ProfileElement['category'],
          element_type: def.element_type,
          direction: def.direction,
          weight: def.defaultWeight,
          target_value: def.defaultTarget,
          tags: [],
          source: 'manual',
        }]
      } else {
        next = prev.filter(e => e.name !== def.name)
      }
      scheduleAutoSave(next)
      return next
    })
  }

  // Build a map of active elements by name for quick lookup
  const activeMap = new Map<string, ProfileElement>(elements.map(e => [e.name, e]))

  // Group system elements by category
  const grouped = CATEGORIES.reduce<Record<string, typeof SYSTEM_ELEMENTS>>((acc, cat) => {
    acc[cat] = SYSTEM_ELEMENTS.filter(e => e.category === cat)
    return acc
  }, {} as Record<string, typeof SYSTEM_ELEMENTS>)

  return (
    <div className="vp-tab-body">
      {CATEGORIES.map(cat => {
        const catDefs = grouped[cat]
        if (!catDefs || catDefs.length === 0) return null
        const isCollapsed = collapsed[cat]
        const activeCount = catDefs.filter(d => activeMap.has(d.name)).length
        return (
          <div key={cat} className="vp-category">
            <button
              className="vp-category-header"
              onClick={() => setCollapsed(prev => ({ ...prev, [cat]: !isCollapsed }))}
            >
              <span className="vp-category-name">[{isCollapsed ? '+' : '−'}] {cat}</span>
              <span className="text-muted" style={{ fontSize: '0.75rem' }}>{activeCount}/{catDefs.length}</span>
            </button>
            {!isCollapsed && (
              <div className="vp-element-list">
                {catDefs.map(def => {
                  const el: ProfileElement | undefined = activeMap.get(def.name)
                  const isOn = el !== undefined
                  return (
                    <div key={def.name} className={`vp-element-card ${!isOn ? 'vp-element-off' : ''}`}>
                      <div className="vp-element-row">
                        <label className="vp-element-check">
                          <input
                            type="checkbox"
                            checked={isOn}
                            onChange={e => toggleElement(def, (e.target as HTMLInputElement).checked)}
                          />
                        </label>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <span className="vp-element-name">{def.name.replace(/_/g, ' ')}</span>
                          <div className="vp-element-desc">{def.description}</div>
                        </div>
                        {isOn && el !== undefined && (
                          <span className="text-muted" style={{ fontSize: '0.7rem', flexShrink: 0 }}>
                            {def.element_type === 'directional' ? `↕ ${el.direction ?? def.direction}` : `target: ${(el.target_value ?? def.defaultTarget ?? 0).toFixed(1)}`}
                          </span>
                        )}
                      </div>
                      {isOn && el !== undefined && (
                        <div className="vp-element-controls">
                          {def.element_type === 'directional' ? (
                            <select
                              className="select-input vp-select-sm"
                              value={el.direction ?? def.direction ?? 'more'}
                              onChange={e => updateElement(def.name, { direction: (e.target as HTMLSelectElement).value as 'more' | 'less' })}
                            >
                              <option value="more">more</option>
                              <option value="less">less</option>
                            </select>
                          ) : (
                            <input
                              type="number"
                              className="threshold-input"
                              value={el.target_value ?? def.defaultTarget ?? 0}
                              step={0.1}
                              onChange={e => updateElement(def.name, { target_value: Number((e.target as HTMLInputElement).value) })}
                              style={{ width: '5rem' }}
                            />
                          )}
                          <div className="vp-weight-wrap">
                            <input
                              type="range"
                              min={0} max={1} step={0.05}
                              value={el.weight}
                              className="vp-weight-slider"
                              onChange={e => updateElement(def.name, { weight: Number((e.target as HTMLInputElement).value) })}
                            />
                            <span className="vp-weight-val">{el.weight.toFixed(2)}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
      {msg && <div className="text-muted" style={{ fontSize: '0.8rem', padding: '0.5rem 0' }}>{msg}</div>}
    </div>
  )
}

// ─── Prompts Tab ──────────────────────────────────────────────────────────────
function PromptsTab({ profileId }: { profileId: number }) {
  const [prompts, setPrompts] = useState<ProfilePrompt[]>([])
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [aiEnabled, setAiEnabled] = useState(false)
  const [showAiHelp, setShowAiHelp] = useState(false)
  const [aiHelpInput, setAiHelpInput] = useState('')
  const [aiHelpLoading, setAiHelpLoading] = useState(false)
  const [aiHelpResult, setAiHelpResult] = useState('')

  useEffect(() => {
    voiceProfilesApi.getPrompts(profileId).then(data => {
      setPrompts(Array.isArray(data) ? data : [])
    }).catch(() => setPrompts([]))
  }, [profileId])

  const handleAiHelp = async () => {
    if (!aiHelpInput.trim()) return
    setAiHelpLoading(true)
    setAiHelpResult('')
    try {
      const res = await fetch('http://localhost:8066/api/rewrite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `Convert this description into a concise voice style prompt for an AI rewriter. The prompt should be specific, actionable writing instructions (2-3 sentences max). Description: "${aiHelpInput.trim()}"`,
          use_ai: true,
        }),
      })
      const data = await res.json()
      setAiHelpResult(data.rewritten_text || data.text || 'Could not generate prompt.')
    } catch {
      setAiHelpResult('AI help unavailable.')
    } finally {
      setAiHelpLoading(false)
    }
  }

  const insertAiResult = () => {
    if (!aiHelpResult) return
    setPrompts(prev => [...prev, { prompt_text: aiHelpResult, sort_order: prev.length }])
    setShowAiHelp(false)
    setAiHelpInput('')
    setAiHelpResult('')
  }

  const addPrompt = () => {
    setPrompts(prev => [...prev, { prompt_text: '', sort_order: prev.length }])
  }

  const updatePrompt = (idx: number, text: string) => {
    setPrompts(prev => prev.map((p, i) => i === idx ? { ...p, prompt_text: text } : p))
  }

  const removePrompt = async (idx: number) => {
    const updated = prompts.filter((_, i) => i !== idx).map((p, i) => ({ ...p, sort_order: i }))
    setPrompts(updated)
    // Auto-save the deletion immediately
    try {
      await voiceProfilesApi.updatePrompts(profileId, updated)
    } catch { /* ignore */ }
  }

  const movePrompt = (idx: number, dir: -1 | 1) => {
    const next = [...prompts]
    const swap = idx + dir
    if (swap < 0 || swap >= next.length) return
    ;[next[idx], next[swap]] = [next[swap], next[idx]]
    setPrompts(next.map((p, i) => ({ ...p, sort_order: i })))
  }

  const handleSave = async () => {
    setSaving(true)
    setMsg('')
    try {
      await voiceProfilesApi.updatePrompts(profileId, prompts)
      setMsg('Saved.')
    } catch {
      setMsg('Save failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="vp-tab-body">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <p className="text-muted" style={{ fontSize: '0.8rem', margin: 0 }}>
          Style prompts are injected into the rewrite request. Order matters — earlier prompts take priority.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexShrink: 0 }}>
          <span className="text-muted" style={{ fontSize: '0.7rem' }}>AI Assistant</span>
          <button
            className={`toggle-btn ${aiEnabled ? 'toggle-on' : 'toggle-off'}`}
            onClick={() => setAiEnabled(v => !v)}
            style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem' }}
          >
            {aiEnabled ? '[ ON ]' : '[ OFF ]'}
          </button>
        </div>
      </div>
      {prompts.map((p, i) => (
        <div key={i} className="vp-prompt-row">
          <div className="vp-prompt-order-btns">
            <button className="btn btn-small" onClick={() => movePrompt(i, -1)} disabled={i === 0}>▲</button>
            <button className="btn btn-small" onClick={() => movePrompt(i, 1)} disabled={i === prompts.length - 1}>▼</button>
          </div>
          <textarea
            className="text-input vp-prompt-input"
            rows={2}
            value={p.prompt_text}
            onChange={e => updatePrompt(i, e.target.value)}
            placeholder="e.g. Use short, punchy sentences. Avoid passive voice."
          />
          <button className="btn btn-small btn-reject" onClick={() => removePrompt(i)}>[ × ]</button>
        </div>
      ))}
      {showAiHelp && (
        <div className="card" style={{ marginBottom: '1rem', padding: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <strong style={{ fontSize: '0.85rem' }}>AI Prompt Help</strong>
            <button className="btn btn-small" onClick={() => setShowAiHelp(false)}>[ × ]</button>
          </div>
          <p className="text-muted" style={{ fontSize: '0.75rem', margin: '0 0 0.5rem 0' }}>
            Describe what you want in plain language and AI will generate a voice prompt for you.
          </p>
          <textarea
            className="text-input"
            rows={3}
            value={aiHelpInput}
            onChange={e => setAiHelpInput(e.target.value)}
            placeholder={"e.g. \"I don't like flowery language and want short, direct sentences\""}
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button className="btn btn-small" onClick={handleAiHelp} disabled={aiHelpLoading || !aiHelpInput.trim()}>
              {aiHelpLoading ? 'Generating...' : '[ Generate ]'}
            </button>
          </div>
          {aiHelpResult && (
            <div style={{ marginTop: '0.75rem' }}>
              <div className="terminal-output" style={{ padding: '0.5rem', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
                {aiHelpResult}
              </div>
              <button className="btn btn-small" onClick={insertAiResult}>[ Use This Prompt ]</button>
            </div>
          )}
        </div>
      )}

      <div className="vp-tab-actions">
        <button className="btn btn-small" onClick={addPrompt}>[ + Add Prompt ]</button>
        {aiEnabled && (
          <button className="btn btn-small" onClick={() => setShowAiHelp(v => !v)}>
            {showAiHelp ? '[ Hide AI Help ]' : '[ AI Help ]'}
          </button>
        )}
        <button className="btn" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : '[ Save Prompts ]'}
        </button>
        {msg && <span className="text-muted" style={{ fontSize: '0.8rem' }}>{msg}</span>}
      </div>
    </div>
  )
}

// ─── Fine-Tune Tab ───────────────────────────────────────────────────────────
function FineTuneTab({ profile }: { profile: VoiceProfile }) {
  const [text, setText] = useState('')
  const [parseResult, setParseResult] = useState<any>(null)
  const [parsing, setParsing] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const [msg, setMsg] = useState('')
  const [loadedFiles, setLoadedFiles] = useState<string[]>([])
  const [useAI, setUseAI] = useState(false)
  const [fileProgress, setFileProgress] = useState<{ current: number; total: number } | null>(null)
  const ftFileRef = useRef<HTMLInputElement>(null)

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0

  const handleFileLoad = async () => {
    if (!ftFileRef.current?.files?.length) return
    const files = Array.from(ftFileRef.current.files)
    setFileProgress({ current: 0, total: files.length })
    let combined = text
    const names: string[] = [...loadedFiles]
    for (let i = 0; i < files.length; i++) {
      setFileProgress({ current: i + 1, total: files.length })
      const content = await files[i].text()
      combined += (combined ? '\n\n' : '') + content
      names.push(files[i].name)
    }
    setText(combined)
    setLoadedFiles(names)
    setFileProgress(null)
    ftFileRef.current.value = ''
  }

  const handleParse = async () => {
    if (!text.trim()) return
    setParsing(true)
    setMsg('')
    setParseResult(null)
    try {
      const res = await voiceProfilesApi.parse(profile.id, text)
      setParseResult(res)
      setText('')
      setLoadedFiles([])
      setMsg(`Parse complete. Corpus now has ${res.parse_count ?? profile.parse_count + 1} sample(s).`)
    } catch {
      setMsg('Parse failed.')
    } finally {
      setParsing(false)
    }
  }

  const handleReset = async () => {
    setResetting(true)
    setMsg('')
    try {
      await voiceProfilesApi.reset(profile.id)
      setParseResult(null)
      setConfirmReset(false)
      setMsg('Corpus reset. All parsed data cleared.')
    } catch {
      setMsg('Reset failed.')
    } finally {
      setResetting(false)
    }
  }

  return (
    <div className="vp-tab-body">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div>
            <span className="text-muted" style={{ fontSize: '0.8rem' }}>Parse count: </span>
            <strong>{profile.parse_count}</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span className="text-muted" style={{ fontSize: '0.7rem' }}>Use AI</span>
            <button
              className={`toggle-btn ${useAI ? 'toggle-on' : 'toggle-off'}`}
              onClick={() => setUseAI(v => !v)}
              style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem' }}
            >
              {useAI ? '[ ON ]' : '[ OFF ]'}
            </button>
          </div>
        </div>
        {confirmReset ? (
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span className="text-muted" style={{ fontSize: '0.8rem' }}>Confirm reset?</span>
            <button className="btn btn-small btn-reject" onClick={handleReset} disabled={resetting}>
              {resetting ? 'Resetting...' : '[ Yes, Reset ]'}
            </button>
            <button className="btn btn-small" onClick={() => setConfirmReset(false)}>[ Cancel ]</button>
          </div>
        ) : (
          <button className="btn btn-small btn-reject" onClick={() => setConfirmReset(true)}>
            [ Reset Corpus ]
          </button>
        )}
      </div>

      <p className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.75rem' }}>
        Paste your own writing to fine-tune this profile's style elements. Emails, essays, blog posts — anything in your natural voice. 500+ words recommended per sample. Each sample refines the weights; avoid duplicates.
      </p>

      <textarea
        className="text-input"
        rows={12}
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Paste a writing sample here to parse voice patterns..."
      />

      {/* File progress bar */}
      {fileProgress && (
        <div style={{ marginTop: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
            <span>Loading files...</span>
            <span>{fileProgress.current}/{fileProgress.total}</span>
          </div>
          <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(fileProgress.current / fileProgress.total) * 100}%`, background: 'var(--cyan-info)', transition: 'width 0.2s' }} />
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
        <span className="text-muted" style={{ fontSize: '0.8rem' }}>
          {wordCount} words {wordCount > 0 && wordCount < 500 ? '(500+ recommended)' : ''}
          {loadedFiles.length > 0 && ` — ${loadedFiles.length} file(s) loaded`}
        </span>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <input
            ref={ftFileRef}
            type="file"
            multiple
            accept=".txt,.md,.doc,.docx"
            style={{ display: 'none' }}
            onChange={handleFileLoad}
          />
          <button className="btn btn-small" onClick={() => ftFileRef.current?.click()}>
            [ Load Files ]
          </button>
          <button className="btn" onClick={handleParse} disabled={parsing || !text.trim()} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {parsing && <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} />}
            {parsing ? (useAI ? 'AI Parsing...' : 'Parsing...') : '[ Parse Sample ]'}
          </button>
        </div>
      </div>

      {msg && <div className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.75rem' }}>{msg}</div>}

      {parseResult && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <div className="card-header">Parse Results</div>
          <div className="terminal-output" style={{ maxHeight: '300px', overflowY: 'auto' }}>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.75rem' }}>
              {JSON.stringify(parseResult, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Freeze Voice Tab ────────────────────────────────────────────────────────
function FreezeVoiceTab({ profileId }: { profileId: number }) {
  const [snapshots, setSnapshots] = useState<ProfileSnapshot[]>([])
  const [newName, setNewName] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const load = useCallback(() => {
    voiceProfilesApi.listSnapshots(profileId).then(setSnapshots).catch(() => {})
  }, [profileId])

  useEffect(() => { load() }, [load])

  const handleSave = async () => {
    if (!newName.trim()) return
    setSaving(true)
    setMsg('')
    try {
      await voiceProfilesApi.saveSnapshot(profileId, newName.trim())
      setNewName('')
      load()
      setMsg('Snapshot saved.')
    } catch {
      setMsg('Save failed.')
    } finally {
      setSaving(false)
    }
  }

  const handleLoad = async (snapshotId: number) => {
    try {
      await voiceProfilesApi.loadSnapshot(profileId, snapshotId)
      setMsg('Snapshot loaded. Refresh elements/prompts tabs to see changes.')
    } catch {
      setMsg('Load failed.')
    }
  }

  const handleDelete = async (snapshotId: number) => {
    if (!confirm('Delete this snapshot?')) return
    try {
      await voiceProfilesApi.deleteSnapshot(profileId, snapshotId)
      load()
    } catch {
      setMsg('Delete failed.')
    }
  }

  const handleExport = async () => {
    try {
      const data = await voiceProfilesApi.exportProfile(profileId)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `voice-profile-${profileId}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setMsg('Export failed.')
    }
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return
      try {
        const text = await file.text()
        await voiceProfilesApi.importProfile(JSON.parse(text))
        load()
        setMsg('Profile imported.')
      } catch {
        setMsg('Import failed — invalid file.')
      }
    }
    input.click()
  }

  return (
    <div className="vp-tab-body">
      <p className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '1rem' }}>
        Freeze your current voice profile so you can revert back to it later. If you make changes and things go wrong,
        loading a frozen version will restore your elements, prompts, and weights to that point — but your parse count
        will reset to what it was when you froze it, and any changes since then are lost.
      </p>

      <div className="vp-tab-actions" style={{ marginBottom: '1rem' }}>
        <input
          className="select-input"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          placeholder="Give this freeze point a name..."
          style={{ flex: 1 }}
          onKeyDown={e => e.key === 'Enter' && handleSave()}
        />
        <button className="btn" onClick={handleSave} disabled={saving || !newName.trim()}>
          {saving ? 'Freezing...' : '[ Freeze Current ]'}
        </button>
      </div>

      {snapshots.length === 0 ? (
        <div className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '1rem' }}>No frozen versions yet.</div>
      ) : (
        <div style={{ marginBottom: '1rem' }}>
          {snapshots.map(s => (
            <div key={s.id} className="vp-snapshot-row">
              <div>
                <strong style={{ fontSize: '0.85rem' }}>{s.snapshot_name}</strong>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {new Date(s.created_at).toLocaleString()}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-small" onClick={() => handleLoad(s.id)}>[ Load ]</button>
                <button className="btn btn-small btn-reject" onClick={() => handleDelete(s.id)}>[ Delete ]</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="vp-tab-actions">
        <button className="btn btn-small" onClick={handleExport}>[ Export JSON ]</button>
        <button className="btn btn-small" onClick={handleImport}>[ Import JSON ]</button>
      </div>

      {msg && <div className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>{msg}</div>}
    </div>
  )
}

// ─── Create Profile Modal ─────────────────────────────────────────────────────
function CreateProfileModal({ onClose, onCreated }: { onClose: () => void; onCreated: (p: VoiceProfile) => void }) {
  const [mode, setMode] = useState<'choose' | 'manual' | 'wizard'>('choose')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')
  const [wizardText, setWizardText] = useState('')
  const [wizardFiles, setWizardFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const wizardWordCount = wizardText.trim() ? wizardText.trim().split(/\s+/).length : 0

  const handleCreate = async () => {
    if (!name.trim()) { setErr('Name is required.'); return }
    setSaving(true)
    setErr('')
    try {
      const p = await voiceProfilesApi.create({ name: name.trim(), description, profile_type: 'overlay' })
      // If wizard mode with text, parse it immediately
      if (mode === 'wizard' && wizardText.trim()) {
        try {
          await voiceProfilesApi.parse(p.id, wizardText.trim())
        } catch {
          // Profile created, parse can be retried
        }
      }
      onCreated(p)
    } catch {
      setErr('Create failed.')
    } finally {
      setSaving(false)
    }
  }

  const handleFileLoad = async () => {
    if (!fileInputRef.current?.files?.length) return
    const files = Array.from(fileInputRef.current.files)
    setWizardFiles(files)
    let combined = wizardText
    for (const f of files) {
      const content = await f.text()
      combined += (combined ? '\n\n' : '') + content
    }
    setWizardText(combined)
  }

  if (mode === 'choose') {
    return (
      <div className="vp-modal card">
          <div className="card-header">Create Voice Profile</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
            <p className="text-muted" style={{ fontSize: '0.8rem' }}>
              How would you like to create your new voice profile?
            </p>
            <button className="btn" onClick={() => setMode('wizard')} style={{ textAlign: 'left' }}>
              [ Wizard ] — Upload writing samples to auto-generate style
            </button>
            <button className="btn" onClick={() => setMode('manual')} style={{ textAlign: 'left' }}>
              [ Manual ] — Clone Baseline and edit prompts & weights yourself
            </button>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-small" onClick={onClose}>[ Cancel ]</button>
            </div>
          </div>
      </div>
    )
  }

  return (
    <div className="vp-modal card" style={mode === 'wizard' ? { maxWidth: '600px' } : undefined}>
        <div className="card-header">
          {mode === 'wizard' ? 'Create Profile — Wizard' : 'Create Profile — Manual'}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
          <input
            className="select-input"
            placeholder="Profile name"
            value={name}
            onChange={e => setName(e.target.value)}
            autoFocus
          />
          <input
            className="select-input"
            placeholder="Description (optional)"
            value={description}
            onChange={e => setDescription(e.target.value)}
          />

          {mode === 'wizard' && (
            <>
              <p className="text-muted" style={{ fontSize: '0.75rem', margin: 0 }}>
                Paste your writing or load files. The system will analyze your style and generate weights automatically.
              </p>
              <textarea
                className="text-input"
                rows={8}
                value={wizardText}
                onChange={e => setWizardText(e.target.value)}
                placeholder="Paste writing samples here..."
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {wizardWordCount} words {wizardWordCount > 0 && wizardWordCount < 500 ? '(500+ recommended)' : ''}
                  {wizardFiles.length > 0 && ` — ${wizardFiles.length} file(s) loaded`}
                </span>
                <div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".txt,.md,.doc,.docx"
                    style={{ display: 'none' }}
                    onChange={handleFileLoad}
                  />
                  <button className="btn btn-small" onClick={() => fileInputRef.current?.click()}>
                    [ Load Files ]
                  </button>
                </div>
              </div>
            </>
          )}

          {mode === 'manual' && (
            <p className="text-muted" style={{ fontSize: '0.75rem', margin: 0 }}>
              Creates a new profile cloned from Baseline defaults. You can then edit elements, prompts, and weights.
            </p>
          )}

          {err && <div className="error-message">{err}</div>}
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
            <button className="btn btn-small" onClick={() => setMode('choose')}>[ ← Back ]</button>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn btn-small" onClick={onClose}>[ Cancel ]</button>
              <button className="btn" onClick={handleCreate} disabled={saving}>
                {saving ? 'Creating...' : '[ Create Profile ]'}
              </button>
            </div>
          </div>
        </div>
      </div>
  )
}

// ─── Test Voice Tab ──────────────────────────────────────────────────────────
function TestVoiceTab({ profileId }: { profileId: number }) {
  const [text, setText] = useState('')
  const [mode, setMode] = useState<'quantitative' | 'qualitative' | 'both'>('quantitative')
  const [result, setResult] = useState<FidelityScoreResult | null>(null)
  const [loading, setLoading] = useState(false)

  const handleScore = async () => {
    if (!text.trim()) return
    setLoading(true); setResult(null)
    try {
      const data = await scoringApi.scoreFidelity(text, profileId, mode)
      setResult(data)
    } catch { /* handled by component */ }
    finally { setLoading(false) }
  }

  return (
    <div>
      <textarea
        className="terminal-input"
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Paste text to score against this voice profile..."
        rows={6}
        style={{ width: '100%', marginBottom: '8px' }}
      />
      <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
        {(['quantitative', 'qualitative', 'both'] as const).map(m => (
          <label key={m} style={{ fontSize: '12px', cursor: 'pointer' }}>
            <input type="radio" name="score-mode" value={m} checked={mode === m} onChange={() => setMode(m)} /> {m}
          </label>
        ))}
        <button className="vp-btn" onClick={handleScore} disabled={loading || !text.trim()}>
          {loading ? 'Scoring...' : 'Score'}
        </button>
      </div>
      {result && <FidelityScore result={result} />}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function VoiceProfilesPage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('elements')
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<number | null>(null)
  const [editingName, setEditingName] = useState(false)
  const [nameDraft, setNameDraft] = useState('')
  const [completeness, setCompleteness] = useState<CompletenessData | null>(null)
  const nameInputRef = useRef<HTMLInputElement>(null)

  const loadProfiles = useCallback(async (autoSelectFirst = false) => {
    try {
      const data = await voiceProfilesApi.list()
      const list = Array.isArray(data) ? data : []
      setProfiles(list)
      if (autoSelectFirst && list.length > 0) {
        setSelectedId(prev => prev ?? list[0].id)
      }
    } catch {
      setProfiles([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadProfiles(true) }, [loadProfiles])

  const loadCompleteness = useCallback(async (pid: number) => {
    try {
      const data = await voiceProfilesApi.fetchCompleteness(pid)
      setCompleteness(data)
    } catch {
      setCompleteness(null)
    }
  }, [])

  const selectedProfile = profiles.find(p => p.id === selectedId) ?? null

  // Load completeness when selected profile changes
  useEffect(() => {
    if (selectedId) {
      loadCompleteness(selectedId)
    } else {
      setCompleteness(null)
    }
  }, [selectedId, loadCompleteness])

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this voice profile? This cannot be undone.')) return
    setDeleting(id)
    try {
      await voiceProfilesApi.delete(id)
      if (selectedId === id) setSelectedId(null)
      await loadProfiles()
    } catch {
      // ignore
    } finally {
      setDeleting(null)
    }
  }

  const handleCreated = (p: VoiceProfile) => {
    setShowCreate(false)
    loadProfiles()
    setSelectedId(p.id)
  }

  const handleClone = async (id: number) => {
    try {
      const exported = await voiceProfilesApi.exportProfile(id)
      const source = profiles.find(p => p.id === id)
      exported.name = `${source?.name ?? 'Profile'} (Copy)`
      delete exported.id
      const imported = await voiceProfilesApi.importProfile(exported)
      await loadProfiles()
      setSelectedId(imported.id)
    } catch {
      // ignore
    }
  }

  const handleResetBaseline = async () => {
    const baseline = profiles.find(isBaseline)
    if (!baseline) return
    if (!confirm('Reset Baseline to factory defaults? This clears all customizations.')) return
    try {
      await voiceProfilesApi.reset(baseline.id)
      await loadProfiles()
    } catch {
      // ignore
    }
  }

  const startRename = () => {
    if (!selectedProfile || isBaseline(selectedProfile)) return
    setNameDraft(selectedProfile.name)
    setEditingName(true)
    setTimeout(() => nameInputRef.current?.focus(), 50)
  }

  const commitRename = async () => {
    if (!selectedProfile || !nameDraft.trim()) {
      setEditingName(false)
      return
    }
    if (nameDraft.trim() === selectedProfile.name) {
      setEditingName(false)
      return
    }
    try {
      await voiceProfilesApi.update(selectedProfile.id, { name: nameDraft.trim() })
      await loadProfiles()
    } catch {
      // ignore
    }
    setEditingName(false)
  }

  const handleSetActive = async (id: number) => {
    try {
      await voiceProfilesApi.update(id, { is_active: true })
      // Deactivate all others
      for (const p of profiles) {
        if (p.id !== id && p.is_active) {
          await voiceProfilesApi.update(p.id, { is_active: false })
        }
      }
      await loadProfiles()
    } catch {
      // ignore
    }
  }

  return (
    <div className="vp-page">
      {/* Left panel */}
      <div className="vp-left-panel">
        <div className="vp-panel-header">
          <span>{'>'} Voice Profiles_</span>
          <button className="btn btn-small" onClick={() => setShowCreate(true)}>[ + New ]</button>
        </div>

        {loading ? (
          <div className="spinner" style={{ margin: '2rem auto' }} />
        ) : profiles.length === 0 ? (
          <div className="text-muted" style={{ padding: '1rem', fontSize: '0.85rem' }}>
            No profiles yet. Create one to get started.
          </div>
        ) : (
          <ul className="vp-profile-list">
            {profiles.map(p => (
              <li
                key={p.id}
                className={`vp-profile-card ${selectedId === p.id ? 'selected' : ''}`}
                onClick={() => setSelectedId(p.id)}
              >
                <div className="vp-profile-card-top">
                  <strong className="vp-profile-name">{p.name}</strong>
                </div>
                {p.description && (
                  <div className="text-muted vp-profile-desc">{p.description}</div>
                )}
                <div className="vp-profile-meta">
                  <span className="text-muted">{p.parse_count} parse{p.parse_count !== 1 ? 's' : ''}</span>
                  {p.is_active && <span className="vp-active-dot">● active</span>}
                </div>
                <div className="vp-profile-actions" onClick={e => e.stopPropagation()}>
                  {!p.is_active && (
                    <button
                      className="btn btn-small"
                      onClick={() => handleSetActive(p.id)}
                      title="Set as active voice profile"
                    >
                      [ Set Active ]
                    </button>
                  )}
                  <button
                    className="btn btn-small"
                    onClick={() => handleClone(p.id)}
                    title="Clone profile"
                  >
                    [ Clone ]
                  </button>
                  {isBaseline(p) ? (
                    <button
                      className="btn btn-small btn-reject"
                      onClick={() => handleResetBaseline()}
                      title="Reset to factory defaults"
                    >
                      [ Reset ]
                    </button>
                  ) : (
                    <button
                      className="btn btn-small btn-reject"
                      onClick={() => handleDelete(p.id)}
                      disabled={deleting === p.id}
                    >
                      {deleting === p.id ? '...' : '[ Delete ]'}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Right panel */}
      <div className="vp-right-panel" style={{ position: 'relative' }}>
        {showCreate && (
          <div className="vp-panel-modal-overlay">
            <CreateProfileModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
          </div>
        )}
        {!selectedProfile ? (
          <div className="vp-empty-state">
            <div className="text-muted">Select a profile to edit</div>
          </div>
        ) : (
          <>
            <div className="vp-right-header">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                  {editingName ? (
                    <input
                      ref={nameInputRef}
                      className="select-input"
                      value={nameDraft}
                      onChange={e => setNameDraft(e.target.value)}
                      onBlur={commitRename}
                      onKeyDown={e => { if (e.key === 'Enter') commitRename(); if (e.key === 'Escape') setEditingName(false) }}
                      style={{ fontSize: '1.1rem', fontWeight: 'bold', padding: '0.2rem 0.4rem' }}
                    />
                  ) : (
                    <>
                      <h2 className="card-header" style={{ margin: 0 }}>{selectedProfile.name}</h2>
                      {!isBaseline(selectedProfile) && (
                        <button
                          className="btn btn-small"
                          onClick={startRename}
                          title="Rename profile"
                          style={{ padding: '0.1rem 0.3rem', fontSize: '0.8rem', lineHeight: 1 }}
                        >
                          ✏
                        </button>
                      )}
                    </>
                  )}
                </div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {selectedProfile.parse_count} parse{selectedProfile.parse_count !== 1 ? 's' : ''} &bull; updated {new Date(selectedProfile.updated_at).toLocaleDateString()}
                </div>
              </div>
            </div>

            <div className="vp-tabs">
              {TABS.map(t => (
                <button
                  key={t.id}
                  className={`vp-tab ${activeTab === t.id ? 'vp-tab-active' : ''}`}
                  onClick={() => setActiveTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <CompletenessBar data={completeness} />

            <div className="vp-tab-content card">
              {activeTab === 'elements' && <ElementsTab key={selectedProfile.id} profileId={selectedProfile.id} />}
              {activeTab === 'prompts' && <PromptsTab key={selectedProfile.id} profileId={selectedProfile.id} />}
              {activeTab === 'finetune' && <FineTuneTab key={selectedProfile.id} profile={selectedProfile} />}
              {activeTab === 'freeze' && <FreezeVoiceTab key={selectedProfile.id} profileId={selectedProfile.id} />}
              {activeTab === 'testvox' && <TestVoiceTab key={selectedProfile.id} profileId={selectedProfile.id} />}
              {activeTab === 'corpus' && <CorpusManager key={selectedProfile.id} profileId={selectedProfile.id} completeness={completeness} onCorpusChange={() => loadCompleteness(selectedProfile.id)} />}
              {activeTab === 'consolidate' && <ConsolidationView key={selectedProfile.id} profileId={selectedProfile.id} observationCount={0} />}
              {activeTab === 'reparse' && selectedProfile && <ReparseView key={selectedProfile.id} profileId={selectedProfile.id} profileName={selectedProfile.name} />}
            </div>
          </>
        )}
      </div>

    </div>
  )
}
