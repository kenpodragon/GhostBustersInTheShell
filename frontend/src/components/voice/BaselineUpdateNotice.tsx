import { useState } from 'react'
import type { BaselineUpdateCheckResult } from '../../types'
import { voiceProfilesApi } from '../../services/voiceProfilesApi'

interface Props {
  version: { baseline_version?: string | null; baseline_version_date?: string | null } | null
  onUpdate: () => void
}

export default function BaselineUpdateNotice({ version, onUpdate }: Props) {
  const [checking, setChecking] = useState(false)
  const [applying, setApplying] = useState(false)
  const [result, setResult] = useState<BaselineUpdateCheckResult | null>(null)
  const [showInstructions, setShowInstructions] = useState(false)
  const [message, setMessage] = useState('')

  const checkUpdates = async () => {
    setChecking(true)
    setMessage('')
    try {
      const data = await voiceProfilesApi.checkBaselineUpdates()
      setResult(data)
      if (data.status === 'up_to_date') {
        setMessage('Baseline voice profile is up to date.')
      }
    } catch {
      setMessage('Failed to check for updates.')
    } finally {
      setChecking(false)
    }
  }

  const applyUpdate = async () => {
    setApplying(true)
    setMessage('')
    try {
      const data = await voiceProfilesApi.applyBaselineUpdate()
      if (data.success) {
        setMessage('Update applied successfully.')
        setResult(null)
        onUpdate()
      } else {
        setMessage(data.error || 'Failed to apply update.')
      }
    } catch {
      setMessage('Failed to apply update.')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="update-notice">
      <div className="update-notice-row">
        <span className="update-version">
          Baseline Voice: {version?.baseline_version || '...'}{' '}
          {version?.baseline_version_date && (
            <span className="text-muted">({version.baseline_version_date})</span>
          )}
        </span>
        <button className="btn btn-small" onClick={checkUpdates} disabled={checking}>
          {checking ? 'Checking...' : 'Check for Updates'}
        </button>
      </div>

      {message && <div className="update-message">{message}</div>}

      {result?.status === 'update_available' && !result.app_update_required && (
        <div className="update-available">
          <div className="update-available-header">
            Update available: {result.remote_version} ({result.remote_date})
          </div>
          {result.changelog && <div className="update-changelog">{result.changelog}</div>}
          <button className="btn btn-small" onClick={applyUpdate} disabled={applying}>
            {applying ? 'Applying...' : 'Apply Update'}
          </button>
        </div>
      )}

      {result?.app_update_required && (
        <div className="update-app-required">
          <div className="update-app-header">
            App update required (min: {result.min_app_version}, current: {result.app_version})
          </div>
          <button
            className="btn btn-small"
            onClick={() => setShowInstructions(!showInstructions)}
          >
            {showInstructions ? 'Hide Instructions' : 'Show Instructions'}
          </button>
          {showInstructions && (
            <div className="update-instructions">
              <code>git pull</code>
              <code>docker compose up --build -d</code>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
