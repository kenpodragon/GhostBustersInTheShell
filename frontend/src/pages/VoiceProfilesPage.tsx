import { useState, useEffect, useCallback } from 'react'
import type { VoiceProfile, ProfileElement, ProfilePrompt, ProfileSnapshot } from '../types'
import { voiceProfilesApi } from '../services/voiceProfilesApi'

type TabId = 'elements' | 'prompts' | 'samples' | 'snapshots'
const TABS: { id: TabId; label: string }[] = [
  { id: 'elements', label: 'Style Elements' },
  { id: 'prompts', label: 'Prompts' },
  { id: 'samples', label: 'Samples' },
  { id: 'snapshots', label: 'Snapshots' },
]

const CATEGORIES = ['lexical', 'character', 'syntactic', 'structural', 'content', 'idiosyncratic'] as const

// ─── Style Elements Tab ───────────────────────────────────────────────────────
function ElementsTab({ profileId }: { profileId: number }) {
  const [elements, setElements] = useState<ProfileElement[]>([])
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    voiceProfilesApi.getElements(profileId).then(setElements).catch(() => {})
  }, [profileId])

  const grouped = CATEGORIES.reduce<Record<string, ProfileElement[]>>((acc, cat) => {
    acc[cat] = elements.filter(e => e.category === cat)
    return acc
  }, {} as Record<string, ProfileElement[]>)

  const updateElement = (id: number, patch: Partial<ProfileElement>) => {
    setElements(prev => prev.map(e => e.id === id ? { ...e, ...patch } : e))
  }

  const removeElement = (id: number) => {
    setElements(prev => prev.filter(e => e.id !== id))
  }

  const addElement = () => {
    const newEl: ProfileElement = {
      id: Date.now(), // temp id
      name: 'New element',
      category: 'lexical',
      element_type: 'directional',
      direction: 'more',
      weight: 0.5,
      tags: [],
      source: 'manual',
    }
    setElements(prev => [...prev, newEl])
  }

  const handleSave = async () => {
    setSaving(true)
    setMsg('')
    try {
      await voiceProfilesApi.updateElements(profileId, elements)
      setMsg('Saved.')
    } catch {
      setMsg('Save failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="vp-tab-body">
      {CATEGORIES.map(cat => {
        const catEls = grouped[cat]
        if (!catEls) return null
        const isCollapsed = collapsed[cat]
        return (
          <div key={cat} className="vp-category">
            <button
              className="vp-category-header"
              onClick={() => setCollapsed(prev => ({ ...prev, [cat]: !isCollapsed }))}
            >
              <span className="vp-category-name">[{isCollapsed ? '+' : '−'}] {cat}</span>
              <span className="text-muted" style={{ fontSize: '0.75rem' }}>{catEls.length}</span>
            </button>
            {!isCollapsed && (
              <div className="vp-element-list">
                {catEls.length === 0 && (
                  <div className="text-muted" style={{ fontSize: '0.8rem', padding: '0.5rem 0' }}>No elements in this category.</div>
                )}
                {catEls.map(el => (
                  <div key={el.id} className="vp-element-row">
                    <span className="vp-element-name">{el.name}</span>
                    {el.element_type === 'directional' ? (
                      <select
                        className="select-input vp-select-sm"
                        value={el.direction ?? 'more'}
                        onChange={e => updateElement(el.id, { direction: e.target.value as 'more' | 'less' })}
                      >
                        <option value="more">more</option>
                        <option value="less">less</option>
                      </select>
                    ) : (
                      <input
                        type="number"
                        className="threshold-input"
                        value={el.target_value ?? 0}
                        step={0.01}
                        onChange={e => updateElement(el.id, { target_value: Number(e.target.value) })}
                        style={{ width: '5rem' }}
                      />
                    )}
                    <div className="vp-weight-wrap">
                      <input
                        type="range"
                        min={0} max={1} step={0.05}
                        value={el.weight}
                        className="vp-weight-slider"
                        onChange={e => updateElement(el.id, { weight: Number(e.target.value) })}
                      />
                      <span className="vp-weight-val">{el.weight.toFixed(2)}</span>
                    </div>
                    <div className="vp-tags">
                      {el.tags.map(t => <span key={t} className="pattern-chip">{t}</span>)}
                    </div>
                    <span className={`vp-source-badge ${el.source}`}>{el.source}</span>
                    {el.source === 'manual' && (
                      <button className="btn btn-small btn-reject" onClick={() => removeElement(el.id)}>[ × ]</button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
      <div className="vp-tab-actions">
        <button className="btn btn-small" onClick={addElement}>[ + Add Element ]</button>
        <button className="btn" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : '[ Save Elements ]'}
        </button>
        {msg && <span className="text-muted" style={{ fontSize: '0.8rem' }}>{msg}</span>}
      </div>
    </div>
  )
}

// ─── Prompts Tab ──────────────────────────────────────────────────────────────
function PromptsTab({ profileId }: { profileId: number }) {
  const [prompts, setPrompts] = useState<ProfilePrompt[]>([])
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    voiceProfilesApi.getPrompts(profileId).then(setPrompts).catch(() => {})
  }, [profileId])

  const addPrompt = () => {
    setPrompts(prev => [...prev, { prompt_text: '', sort_order: prev.length }])
  }

  const updatePrompt = (idx: number, text: string) => {
    setPrompts(prev => prev.map((p, i) => i === idx ? { ...p, prompt_text: text } : p))
  }

  const removePrompt = (idx: number) => {
    setPrompts(prev => prev.filter((_, i) => i !== idx).map((p, i) => ({ ...p, sort_order: i })))
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
      <p className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '1rem' }}>
        Style prompts are injected into the rewrite request. Order matters — earlier prompts take priority.
      </p>
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
      <div className="vp-tab-actions">
        <button className="btn btn-small" onClick={addPrompt}>[ + Add Prompt ]</button>
        <button className="btn" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : '[ Save Prompts ]'}
        </button>
        {msg && <span className="text-muted" style={{ fontSize: '0.8rem' }}>{msg}</span>}
      </div>
    </div>
  )
}

// ─── Samples Tab ──────────────────────────────────────────────────────────────
function SamplesTab({ profile }: { profile: VoiceProfile }) {
  const [text, setText] = useState('')
  const [parseResult, setParseResult] = useState<any>(null)
  const [parsing, setParsing] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const [msg, setMsg] = useState('')

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0

  const handleParse = async () => {
    if (!text.trim()) return
    setParsing(true)
    setMsg('')
    setParseResult(null)
    try {
      const res = await voiceProfilesApi.parse(profile.id, text)
      setParseResult(res)
      setText('')
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
        <div>
          <span className="text-muted" style={{ fontSize: '0.8rem' }}>Parse count: </span>
          <strong>{profile.parse_count}</strong>
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
        Paste YOUR writing — emails, essays, documents. 500+ words recommended. Do not upload the same text twice — it biases element weights.
      </p>

      <textarea
        className="text-input"
        rows={12}
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Paste a writing sample here to parse voice patterns..."
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
        <span className={`text-muted ${wordCount > 0 && wordCount < 500 ? '' : ''}`} style={{ fontSize: '0.8rem' }}>
          {wordCount} words {wordCount > 0 && wordCount < 500 ? '(500+ recommended)' : ''}
        </span>
        <button className="btn" onClick={handleParse} disabled={parsing || !text.trim()}>
          {parsing ? 'Parsing...' : '[ Parse Sample ]'}
        </button>
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

// ─── Snapshots Tab ────────────────────────────────────────────────────────────
function SnapshotsTab({ profileId }: { profileId: number }) {
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
      <div className="vp-tab-actions" style={{ marginBottom: '1rem' }}>
        <input
          className="select-input"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          placeholder="Snapshot name..."
          style={{ flex: 1 }}
          onKeyDown={e => e.key === 'Enter' && handleSave()}
        />
        <button className="btn" onClick={handleSave} disabled={saving || !newName.trim()}>
          {saving ? 'Saving...' : '[ Save Snapshot ]'}
        </button>
      </div>

      {snapshots.length === 0 ? (
        <div className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '1rem' }}>No snapshots yet.</div>
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
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [profileType, setProfileType] = useState<'baseline' | 'overlay'>('baseline')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const handleCreate = async () => {
    if (!name.trim()) { setErr('Name is required.'); return }
    setSaving(true)
    setErr('')
    try {
      const p = await voiceProfilesApi.create({ name: name.trim(), description, profile_type: profileType })
      onCreated(p)
    } catch {
      setErr('Create failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="vp-modal-overlay" onClick={onClose}>
      <div className="vp-modal card" onClick={e => e.stopPropagation()}>
        <div className="card-header">Create Voice Profile</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
          <input
            className="select-input"
            placeholder="Profile name"
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <input
            className="select-input"
            placeholder="Description (optional)"
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
          <div style={{ display: 'flex', gap: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
              <input type="radio" value="baseline" checked={profileType === 'baseline'} onChange={() => setProfileType('baseline')} />
              <span>Baseline <span className="text-muted" style={{ fontSize: '0.75rem' }}>(primary voice)</span></span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
              <input type="radio" value="overlay" checked={profileType === 'overlay'} onChange={() => setProfileType('overlay')} />
              <span>Overlay <span className="text-muted" style={{ fontSize: '0.75rem' }}>(layered on top)</span></span>
            </label>
          </div>
          {err && <div className="error-message">{err}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
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

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function VoiceProfilesPage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('elements')
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<number | null>(null)

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

  const selectedProfile = profiles.find(p => p.id === selectedId) ?? null

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
                  <span className={`vp-type-badge ${p.profile_type}`}>{p.profile_type}</span>
                </div>
                {p.description && (
                  <div className="text-muted vp-profile-desc">{p.description}</div>
                )}
                <div className="vp-profile-meta">
                  <span className="text-muted">{p.parse_count} parse{p.parse_count !== 1 ? 's' : ''}</span>
                  {p.is_active && <span className="vp-active-dot">● active</span>}
                </div>
                <div className="vp-profile-actions" onClick={e => e.stopPropagation()}>
                  <button
                    className="btn btn-small btn-reject"
                    onClick={() => handleDelete(p.id)}
                    disabled={deleting === p.id}
                  >
                    {deleting === p.id ? '...' : '[ Delete ]'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Right panel */}
      <div className="vp-right-panel" style={{ position: 'relative' }}>
        {showCreate && (
          <CreateProfileModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
        )}
        {!selectedProfile ? (
          <div className="vp-empty-state">
            <div className="text-muted">Select a profile to edit</div>
          </div>
        ) : (
          <>
            <div className="vp-right-header">
              <div>
                <h2 className="card-header" style={{ marginBottom: '0.2rem' }}>{selectedProfile.name}</h2>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {selectedProfile.profile_type} &bull; {selectedProfile.parse_count} parse{selectedProfile.parse_count !== 1 ? 's' : ''} &bull; updated {new Date(selectedProfile.updated_at).toLocaleDateString()}
                </div>
              </div>
            </div>

            <div className="rules-tabs">
              {TABS.map(t => (
                <button
                  key={t.id}
                  className={`rules-tab ${activeTab === t.id ? 'rules-tab-active' : ''}`}
                  onClick={() => setActiveTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="rules-tab-content card">
              {activeTab === 'elements' && <ElementsTab key={selectedProfile.id} profileId={selectedProfile.id} />}
              {activeTab === 'prompts' && <PromptsTab key={selectedProfile.id} profileId={selectedProfile.id} />}
              {activeTab === 'samples' && <SamplesTab key={selectedProfile.id} profile={selectedProfile} />}
              {activeTab === 'snapshots' && <SnapshotsTab key={selectedProfile.id} profileId={selectedProfile.id} />}
            </div>
          </>
        )}
      </div>

    </div>
  )
}
