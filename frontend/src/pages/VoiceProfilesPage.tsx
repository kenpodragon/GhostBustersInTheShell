// code/frontend/src/pages/VoiceProfilesPage.tsx
import { useState, useEffect } from 'react'
import RulesEditor from '../components/RulesEditor'

interface VoiceProfile {
  id: number
  name: string
  description: string
  created_at: string
  rules_json?: string
}

type WizardStep = 'paste' | 'review' | 'preview' | null

export default function VoiceProfilesPage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([])
  const [wizardStep, setWizardStep] = useState<WizardStep>(null)
  const [sampleContent, setSampleContent] = useState('')
  const [proposedRules, setProposedRules] = useState<any>(null)
  const [profileName, setProfileName] = useState('')
  const [previewResult, setPreviewResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)

  const AI_SAMPLE = "In today's rapidly evolving landscape, it is essential to leverage innovative solutions that streamline processes and drive meaningful outcomes. By harnessing the power of cutting-edge technology, organizations can navigate complex challenges and unlock unprecedented opportunities for growth and transformation."

  useEffect(() => { fetchProfiles() }, [])

  const fetchProfiles = async () => {
    const res = await fetch('/api/voice-profiles')
    if (res.ok) setProfiles(await res.json())
  }

  const wordCount = sampleContent.trim() ? sampleContent.trim().split(/\s+/).length : 0

  const resetWizard = () => {
    setWizardStep(null)
    setSampleContent('')
    setProposedRules(null)
    setProfileName('')
    setPreviewResult(null)
    setError('')
  }

  const handleGenerate = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/voice-profiles/onboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sample_content: sampleContent, preview_only: true }),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error || 'Generation failed')
      }
      setProposedRules(await res.json())
      setWizardStep('review')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handlePreview = async () => {
    setLoading(true)
    setError('')
    try {
      // Save profile with the already-proposed rules (don't re-generate)
      const saveRes = await fetch('/api/voice-profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: profileName || 'New Profile',
          description: `Generated from ${wordCount} words of sample content`,
          rules_json: JSON.stringify(proposedRules?.rules || {}),
        }),
      })
      if (!saveRes.ok) throw new Error('Failed to save profile')
      const savedProfile = await saveRes.json()

      // Preview with AI sample text
      const prevRes = await fetch(`/api/voice-profiles/${savedProfile.id}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: AI_SAMPLE }),
      })
      if (prevRes.ok) setPreviewResult(await prevRes.json())

      setWizardStep('preview')
      fetchProfiles()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this profile?')) return
    await fetch(`/api/voice-profiles/${id}`, { method: 'DELETE' })
    fetchProfiles()
  }

  // Edit mode — show RulesEditor
  if (editingId) {
    return (
      <div>
        <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>{'>'} Edit Voice Profile_</h1>
        <RulesEditor profileId={editingId} onClose={() => { setEditingId(null); fetchProfiles() }} />
      </div>
    )
  }

  // Wizard: Step 1 — Paste
  if (wizardStep === 'paste') {
    return (
      <div>
        <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
          {'>'} Create Voice Profile — Step 1: Paste Samples_
        </h1>
        <div className="card">
          <div className="card-header">Writing Samples</div>
          <p className="text-muted" style={{ marginBottom: '0.5rem' }}>
            Paste 2000+ words of YOUR writing. Include emails, essays, documents — anything that sounds like you.
          </p>
          <input
            className="select-input"
            value={profileName}
            onChange={e => setProfileName(e.target.value)}
            placeholder="Profile name (e.g., 'My Academic Voice')"
            style={{ marginBottom: '0.5rem' }}
          />
          <textarea
            className="text-input"
            value={sampleContent}
            onChange={e => setSampleContent(e.target.value)}
            placeholder="Paste your writing samples here..."
            rows={15}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
            <span className={`text-muted ${wordCount < 500 ? 'error-text' : ''}`}>
              {wordCount} words {wordCount < 500 ? '(need 500+)' : wordCount < 2000 ? '(2000+ recommended)' : '✓'}
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn btn-small" onClick={resetWizard}>[ CANCEL ]</button>
              <button className="btn" onClick={handleGenerate} disabled={loading || wordCount < 500}>
                {loading ? 'Analyzing...' : '[ GENERATE PROFILE ]'}
              </button>
            </div>
          </div>
          {error && <div className="error-message" style={{ marginTop: '0.5rem' }}>{error}</div>}
        </div>
      </div>
    )
  }

  // Wizard: Step 2 — Review
  if (wizardStep === 'review') {
    return (
      <div>
        <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
          {'>'} Create Voice Profile — Step 2: Review Rules_
        </h1>
        <div className="card">
          <div className="card-header">Extracted Patterns</div>
          {proposedRules && (
            <div className="terminal-output" style={{ maxHeight: '400px', overflowY: 'auto' }}>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                {JSON.stringify(proposedRules.rules, null, 2)}
              </pre>
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
            <button className="btn btn-small" onClick={() => setWizardStep('paste')}>[ ← BACK ]</button>
            <button className="btn" onClick={handlePreview} disabled={loading}>
              {loading ? 'Saving...' : '[ SAVE & PREVIEW ]'}
            </button>
          </div>
          {error && <div className="error-message" style={{ marginTop: '0.5rem' }}>{error}</div>}
        </div>
      </div>
    )
  }

  // Wizard: Step 3 — Preview
  if (wizardStep === 'preview') {
    return (
      <div>
        <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
          {'>'} Create Voice Profile — Step 3: Preview_
        </h1>
        <div className="card">
          <div className="card-header">Before / After — AI Sample Text</div>
          <div className="rewrite-split" style={{ marginTop: '0.5rem' }}>
            <div className="rewrite-side">
              <div className="rewrite-side-header">AI Sample</div>
              <div className="rewrite-text">{AI_SAMPLE}</div>
            </div>
            <div className="rewrite-side">
              <div className="rewrite-side-header">Analysis</div>
              {previewResult ? (
                <div className="rewrite-text">
                  <p>Score: {previewResult.score?.toFixed(1)}</p>
                  <p>Classification: {previewResult.classification?.category || '—'}</p>
                  <p>Voice violations: {previewResult.voice_violations?.length || 0}</p>
                </div>
              ) : (
                <div className="rewrite-text text-muted">No preview available</div>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
            <button className="btn" onClick={resetWizard}>[ DONE ]</button>
          </div>
        </div>
      </div>
    )
  }

  // Default: Profile list
  return (
    <div>
      <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
        {'>'} Voice Profiles_
      </h1>

      <button className="btn" onClick={() => setWizardStep('paste')} style={{ marginBottom: '1rem' }}>
        [ + CREATE NEW PROFILE ]
      </button>

      {profiles.length === 0 ? (
        <div className="card">
          <p className="text-muted">No voice profiles yet. Create one from your writing samples.</p>
        </div>
      ) : (
        profiles.map(p => (
          <div key={p.id} className="card" style={{ marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{p.name}</strong>
                <p className="text-muted" style={{ margin: '0.2rem 0 0' }}>{p.description}</p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-small" onClick={() => setEditingId(p.id)}>
                  [ EDIT ]
                </button>
                <button className="btn btn-small btn-reject" onClick={() => handleDelete(p.id)}>
                  [ DELETE ]
                </button>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
