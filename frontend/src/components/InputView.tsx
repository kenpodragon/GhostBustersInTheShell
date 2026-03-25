import { useState, useRef, useEffect } from 'react'
import { useDocument } from '../context/DocumentContext'
import type { VoiceProfile } from '../types'

export default function InputView() {
  const { submitText, uploadFile, selectProfile, selectedProfileId, loading, error } = useDocument()
  const [text, setText] = useState('')
  const [profiles, setProfiles] = useState<VoiceProfile[]>([])
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetch('/api/voice-profiles')
      .then(r => r.json())
      .then(setProfiles)
      .catch(() => {})
  }, [])

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0

  const handleSubmit = () => {
    if (!text.trim()) return
    submitText(text.trim())
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

      {/* Voice Profile Selector */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <label className="card-header" style={{ display: 'block', marginBottom: '0.5rem' }}>
          Voice Profile
        </label>
        <select
          value={selectedProfileId ?? ''}
          onChange={e => selectProfile(e.target.value ? Number(e.target.value) : null)}
          className="select-input"
        >
          <option value="">None (default heuristics)</option>
          {profiles.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Text Input */}
      <div className="card">
        <div className="card-header">Paste Text</div>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Paste text to analyze for AI patterns..."
          className="text-input"
          rows={12}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
          <span className="text-muted">{wordCount} words</span>
          <button className="btn" onClick={handleSubmit} disabled={loading || !text.trim()}>
            {loading ? 'Processing...' : '[ ANALYZE ]'}
          </button>
        </div>
      </div>

      {/* File Upload */}
      <div
        className="file-drop-zone"
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        style={{ marginTop: '1rem' }}
      >
        <p>Drop a file here or click to upload</p>
        <p className="text-muted">.pdf, .docx, .txt</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFile}
          style={{ display: 'none' }}
        />
      </div>

      {error && (
        <div className="error-message" style={{ marginTop: '1rem' }}>
          {error}
        </div>
      )}
    </div>
  )
}
