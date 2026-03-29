import { useState, useEffect } from 'react'
import type { CorpusInfo, CorpusDocument } from '../types'
import { scoringApi } from '../services/scoringApi'

interface Props { profileId: number }

export default function CorpusManager({ profileId }: Props) {
  const [corpus, setCorpus] = useState<CorpusInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')

  const loadCorpus = async () => {
    setLoading(true)
    try {
      const data = await scoringApi.getCorpusInfo(profileId)
      setCorpus(data)
    } catch { setMsg('Failed to load corpus info.') }
    finally { setLoading(false) }
  }

  useEffect(() => { loadCorpus() }, [profileId])

  const handleRemoveDoc = async (docId: number, filename: string) => {
    if (!confirm(`Remove "${filename}" from corpus? This does not undo its effect on current profile — re-parse needed to recalculate.`)) return
    try {
      await scoringApi.removeCorpusDoc(profileId, docId)
      setMsg(`Removed ${filename}.`)
      loadCorpus()
    } catch { setMsg('Failed to remove document.') }
  }

  if (loading) return <div className="terminal-output" style={{ padding: '8px' }}>Loading corpus...</div>
  if (!corpus) return <div className="terminal-output" style={{ padding: '8px' }}>No corpus data.</div>

  const { documents, stats } = corpus
  return (
    <div>
      <div className="terminal-output" style={{ padding: '8px', marginBottom: '8px', display: 'flex', gap: '16px', fontSize: '13px' }}>
        <span>{stats.total_documents} documents</span>
        <span>{Math.round(stats.total_words / 1000)}K chars</span>
        <span>{stats.ai_observations_count} AI observations</span>
      </div>
      {msg && <div style={{ padding: '4px 8px', fontSize: '12px', color: 'var(--yellow, #ffff00)' }}>{msg}</div>}
      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {documents.length === 0 ? (
          <div style={{ padding: '12px', opacity: 0.5 }}>No corpus documents. Parse text into this profile to build a corpus.</div>
        ) : documents.map((doc: CorpusDocument) => (
          <div key={doc.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', borderBottom: '1px solid rgba(0,255,65,0.1)' }}>
            <div style={{ flex: 2 }}>
              <div style={{ fontSize: '13px' }}>{doc.filename}</div>
              <div style={{ fontSize: '11px', opacity: 0.5 }}>
                {new Date(doc.created_at).toLocaleDateString()} — {Math.round(doc.word_count / 1000)}K chars
                {doc.has_ai_observations && ' — AI analyzed'}
              </div>
            </div>
            <button className="vp-btn vp-btn-danger" onClick={() => handleRemoveDoc(doc.id, doc.filename)} style={{ fontSize: '11px' }}>Remove</button>
          </div>
        ))}
      </div>
    </div>
  )
}
