import { useState } from 'react'
import type { ConsolidationResult, ConsolidatedPrompt } from '../types'
import { voiceProfilesApi } from '../services/voiceProfilesApi'

interface Props { profileId: number; observationCount: number }

export default function ConsolidationView({ profileId, observationCount }: Props) {
  const [result, setResult] = useState<ConsolidationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [msg, setMsg] = useState('')

  const handleConsolidate = async () => {
    setLoading(true); setMsg('')
    try {
      const data = await voiceProfilesApi.consolidate(profileId)
      setResult(data)
      setSelected(new Set(data.consolidated_prompts.map((_: ConsolidatedPrompt, i: number) => i)))
    } catch { setMsg('Consolidation failed.') }
    finally { setLoading(false) }
  }

  const togglePrompt = (idx: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx); else next.add(idx)
      return next
    })
  }

  const handleAcceptPrompts = async () => {
    if (!result) return
    const acceptedPrompts = result.consolidated_prompts
      .filter((_: ConsolidatedPrompt, i: number) => selected.has(i))
      .map((p: ConsolidatedPrompt, i: number) => ({ prompt_text: p.prompt, sort_order: i }))
    try {
      const existing = await voiceProfilesApi.getPrompts(profileId)
      const merged = [...(Array.isArray(existing) ? existing : []), ...acceptedPrompts]
        .map((p: { prompt_text: string }, i: number) => ({ ...p, sort_order: i }))
      await voiceProfilesApi.updatePrompts(profileId, merged)
      setMsg(`${acceptedPrompts.length} prompts added to profile.`)
    } catch { setMsg('Failed to save prompts.') }
  }

  if (observationCount === 0) return <div style={{ padding: '12px', opacity: 0.5 }}>No AI observations to consolidate. Parse documents with AI enabled first.</div>

  return (
    <div>
      <button className="vp-btn" onClick={handleConsolidate} disabled={loading} style={{ marginBottom: '8px' }}>
        {loading ? 'Consolidating...' : `Consolidate AI Observations (${observationCount})`}
      </button>
      {msg && <div style={{ padding: '4px', fontSize: '12px', color: 'var(--yellow, #ffff00)' }}>{msg}</div>}
      {result && (
        <div>
          <div style={{ fontSize: '14px', opacity: 0.7, margin: '8px 0 4px' }}>CONSOLIDATED PROMPTS</div>
          {result.consolidated_prompts.map((p: ConsolidatedPrompt, i: number) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', padding: '6px 8px', borderBottom: '1px solid rgba(0,255,65,0.1)', opacity: selected.has(i) ? 1 : 0.4 }}>
              <input type="checkbox" checked={selected.has(i)} onChange={() => togglePrompt(i)} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '13px' }}>{p.prompt}</div>
                <div style={{ fontSize: '11px', opacity: 0.5 }}>Found in {p.frequency}/{result.document_count} documents — confidence {Math.round(p.confidence * 100)}%</div>
              </div>
            </div>
          ))}
          <button className="vp-btn" onClick={handleAcceptPrompts} style={{ marginTop: '8px' }}>Accept Selected Prompts ({selected.size})</button>

          {result.metric_consensus.filter(m => m.flagged_misleading).length > 0 && (
            <div style={{ marginTop: '12px' }}>
              <div style={{ fontSize: '14px', opacity: 0.7, marginBottom: '4px' }}>FLAGGED METRICS</div>
              {result.metric_consensus.filter(m => m.flagged_misleading).map((m, i) => (
                <div key={i} style={{ fontSize: '12px', padding: '2px 0', color: 'var(--yellow, #ffff00)' }}>
                  {m.element}: {m.consensus_description} (flagged misleading {m.disagreement_count}x)
                </div>
              ))}
            </div>
          )}

          {result.discovered_patterns.length > 0 && (
            <div style={{ marginTop: '12px' }}>
              <div style={{ fontSize: '14px', opacity: 0.7, marginBottom: '4px' }}>DISCOVERED PATTERNS</div>
              {result.discovered_patterns.map((p, i) => (
                <div key={i} style={{ fontSize: '12px', padding: '2px 0' }}>
                  <span style={{ color: 'var(--green, #00ff41)' }}>{p.suggested_element_name}</span>: {p.pattern} ({p.occurrences}x)
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
