const API = 'http://localhost:8066/api'

const json = async (r: Response) => {
  const data = await r.json()
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`)
  return data
}

export const scoringApi = {
  scoreFidelity: (generated_text: string, profile_id: number, mode: string = 'quantitative', sample_text?: string) =>
    fetch(`${API}/score-fidelity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ generated_text, profile_id, mode, sample_text }),
    }).then(json),

  getCorpusInfo: (profileId: number) =>
    fetch(`${API}/voice-profiles/${profileId}/corpus`).then(json),

  removeCorpusDoc: (profileId: number, docId: number) =>
    fetch(`${API}/voice-profiles/${profileId}/corpus/${docId}`, { method: 'DELETE' }).then(json),

  listManagementDocs: (purpose: string = 'analysis', olderThan?: string) => {
    const params = new URLSearchParams({ purpose })
    if (olderThan) params.set('older_than', olderThan)
    return fetch(`${API}/documents/management?${params}`).then(json)
  },

  purgeDocs: (purpose: string, older_than_days: number) =>
    fetch(`${API}/documents/purge`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ purpose, older_than_days }),
    }).then(json),
}
