import { useState } from 'react'
import type { ReparseResult, ProfileElement } from '../types'
import { voiceProfilesApi } from '../services/voiceProfilesApi'

interface Props { profileId: number; profileName: string; onAccepted?: () => void }

export default function ReparseView({ profileId, profileName, onAccepted }: Props) {
  const [result, setResult] = useState<ReparseResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')
  const [confirming, setConfirming] = useState(false)

  const handleReparse = async () => {
    if (!confirming) { setConfirming(true); return }
    setLoading(true); setMsg(''); setConfirming(false)
    try {
      const data = await voiceProfilesApi.reparse(profileId)
      setResult(data)
    } catch { setMsg('Re-parse failed.') }
    finally { setLoading(false) }
  }

  const handleAccept = async () => {
    if (!result) return
    try {
      await voiceProfilesApi.acceptReparse(profileId, result.new_profile_id)
      setMsg('New profile accepted and activated.')
      setResult(null)
      onAccepted?.()
    } catch { setMsg('Failed to accept re-parse.') }
  }

  const handleReject = async () => {
    if (!result) return
    try {
      await voiceProfilesApi.rejectReparse(profileId, result.new_profile_id)
      setMsg('Re-parse rejected. Original profile unchanged.')
      setResult(null)
    } catch { setMsg('Failed to reject re-parse.') }
  }

  if (loading) return <div className="terminal-output" style={{ padding: '12px' }}>Re-parsing corpus... This may take a while.</div>

  if (result) {
    const oldMap = new Map(result.old_elements.map((e: ProfileElement) => [e.name, e]))
    const newMap = new Map(result.new_elements.map((e: ProfileElement) => [e.name, e]))
    const allNames = [...new Set([...oldMap.keys(), ...newMap.keys()])].sort()
    return (
      <div>
        <div style={{ fontSize: '14px', opacity: 0.7, marginBottom: '8px' }}>
          RE-PARSE COMPARISON — {result.parsed_count}/{result.total_documents} documents
        </div>
        {result.errors.length > 0 && (
          <div style={{ color: 'var(--red, #ff0040)', fontSize: '12px', marginBottom: '8px' }}>{result.errors.length} documents failed to parse.</div>
        )}
        <div style={{ maxHeight: '300px', overflowY: 'auto', fontSize: '12px', marginBottom: '12px' }}>
          <div style={{ display: 'flex', padding: '4px 0', fontWeight: 'bold', borderBottom: '1px solid rgba(0,255,65,0.3)' }}>
            <span style={{ flex: 2 }}>Element</span>
            <span style={{ flex: 1, textAlign: 'right' }}>Old</span>
            <span style={{ flex: 1, textAlign: 'right' }}>New</span>
            <span style={{ flex: 1, textAlign: 'right' }}>Delta</span>
          </div>
          {allNames.map(name => {
            const oldEl = oldMap.get(name)
            const newEl = newMap.get(name)
            const oldVal = oldEl?.target_value ?? oldEl?.weight ?? 0
            const newVal = newEl?.target_value ?? newEl?.weight ?? 0
            const delta = newVal - oldVal
            const color = Math.abs(delta) < 0.01 ? 'inherit' : delta > 0 ? 'var(--green, #00ff41)' : 'var(--red, #ff0040)'
            return (
              <div key={name} style={{ display: 'flex', padding: '2px 0', borderBottom: '1px solid rgba(0,255,65,0.05)' }}>
                <span style={{ flex: 2 }}>{name}</span>
                <span style={{ flex: 1, textAlign: 'right' }}>{oldVal.toFixed(3)}</span>
                <span style={{ flex: 1, textAlign: 'right' }}>{newVal.toFixed(3)}</span>
                <span style={{ flex: 1, textAlign: 'right', color }}>{delta > 0 ? '+' : ''}{delta.toFixed(3)}</span>
              </div>
            )
          })}
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="vp-btn" onClick={handleAccept}>Accept New Profile</button>
          <button className="vp-btn vp-btn-danger" onClick={handleReject}>Reject (Keep Original)</button>
        </div>
        {msg && <div style={{ padding: '4px', fontSize: '12px', color: 'var(--yellow, #ffff00)', marginTop: '4px' }}>{msg}</div>}
      </div>
    )
  }

  return (
    <div>
      {confirming ? (
        <div>
          <p style={{ fontSize: '13px', marginBottom: '8px' }}>
            This will create a new version of "{profileName}" by re-parsing all corpus documents with the current parser. Your original profile will not be modified until you accept.
          </p>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="vp-btn" onClick={handleReparse}>Confirm Re-parse</button>
            <button className="vp-btn" onClick={() => setConfirming(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <button className="vp-btn" onClick={handleReparse}>Re-parse Corpus</button>
      )}
      {msg && <div style={{ padding: '4px', fontSize: '12px', color: 'var(--yellow, #ffff00)' }}>{msg}</div>}
    </div>
  )
}
