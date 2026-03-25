import { useState } from 'react'
import type { ConfigSnapshot } from '../../types'
import { rulesApi } from '../../services/rulesApi'

interface Props {
  snapshots: ConfigSnapshot[]
  onSnapshotsChange: () => void
  onConfigReload: () => void
}

export default function ConfigBar({ snapshots, onSnapshotsChange, onConfigReload }: Props) {
  const [showSave, setShowSave] = useState(false)
  const [showLoad, setShowLoad] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saving, setSaving] = useState(false)
  const [reverting, setReverting] = useState(false)
  const [confirmRevert, setConfirmRevert] = useState(false)
  const [message, setMessage] = useState('')

  const handleSave = async () => {
    if (!saveName.trim()) return
    setSaving(true)
    try {
      await rulesApi.saveSnapshot(saveName.trim())
      setSaveName('')
      setShowSave(false)
      setMessage('Snapshot saved.')
      onSnapshotsChange()
    } catch {
      setMessage('Failed to save snapshot.')
    } finally {
      setSaving(false)
    }
  }

  const handleLoad = async (id: number) => {
    try {
      await rulesApi.loadSnapshot(id)
      setShowLoad(false)
      setMessage('Snapshot loaded.')
      onConfigReload()
    } catch {
      setMessage('Failed to load snapshot.')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await rulesApi.deleteSnapshot(id)
      onSnapshotsChange()
    } catch {
      setMessage('Failed to delete snapshot.')
    }
  }

  const handleRevert = async () => {
    setReverting(true)
    try {
      await rulesApi.revert()
      setConfirmRevert(false)
      setMessage('Reverted to defaults.')
      onConfigReload()
    } catch {
      setMessage('Failed to revert.')
    } finally {
      setReverting(false)
    }
  }

  return (
    <div className="config-bar">
      <div className="config-bar-actions">
        <button className="btn btn-small" onClick={() => { setShowSave(!showSave); setShowLoad(false) }}>
          Save As
        </button>
        <button className="btn btn-small" onClick={() => { setShowLoad(!showLoad); setShowSave(false) }}>
          Load ({snapshots.length})
        </button>
        {!confirmRevert ? (
          <button className="btn btn-small btn-danger" onClick={() => setConfirmRevert(true)}>
            Revert to Defaults
          </button>
        ) : (
          <span className="config-confirm">
            <span className="text-muted">Are you sure?</span>
            <button className="btn btn-small btn-danger" onClick={handleRevert} disabled={reverting}>
              {reverting ? 'Reverting...' : 'Yes, Revert'}
            </button>
            <button className="btn btn-small" onClick={() => setConfirmRevert(false)}>Cancel</button>
          </span>
        )}
      </div>

      {message && (
        <div className="config-message" onClick={() => setMessage('')}>{message}</div>
      )}

      {showSave && (
        <div className="config-panel">
          <input
            type="text"
            placeholder="Snapshot name..."
            value={saveName}
            onChange={e => setSaveName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
          />
          <button className="btn btn-small" onClick={handleSave} disabled={saving || !saveName.trim()}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      )}

      {showLoad && (
        <div className="config-panel">
          {snapshots.length === 0 ? (
            <span className="text-muted">No saved snapshots.</span>
          ) : (
            <div className="snapshot-list">
              {snapshots.map(s => (
                <div key={s.id} className="snapshot-item">
                  <span className="snapshot-name">{s.name}</span>
                  <span className="snapshot-date text-muted">{new Date(s.created_at).toLocaleDateString()}</span>
                  <button className="btn btn-small" onClick={() => handleLoad(s.id)}>Load</button>
                  <button className="btn btn-small btn-danger" onClick={() => handleDelete(s.id)}>Del</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
