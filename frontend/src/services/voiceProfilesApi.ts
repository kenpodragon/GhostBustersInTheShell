const API = 'http://localhost:8066/api'

const json = (r: Response) => r.json()
const post = (url: string, body?: any) =>
  fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined }).then(json)
const put = (url: string, body: any) =>
  fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(json)
const del = (url: string) =>
  fetch(url, { method: 'DELETE' }).then(json)

export const voiceProfilesApi = {
  // Profile CRUD
  list: () => fetch(`${API}/voice-profiles`).then(json),
  create: (data: { name: string; description: string; profile_type: 'baseline' | 'overlay' }) =>
    post(`${API}/voice-profiles`, data),
  get: (id: number) => fetch(`${API}/voice-profiles/${id}`).then(json),
  update: (id: number, data: Partial<{ name: string; description: string; profile_type: string; stack_order: number; is_active: boolean }>) =>
    put(`${API}/voice-profiles/${id}`, data),
  delete: (id: number) => del(`${API}/voice-profiles/${id}`),

  // Elements
  getElements: (id: number) => fetch(`${API}/voice-profiles/${id}/elements`).then(json),
  updateElements: (id: number, elements: any[]) =>
    put(`${API}/voice-profiles/${id}/elements`, elements),

  // Prompts
  getPrompts: (id: number) => fetch(`${API}/voice-profiles/${id}/prompts`).then(json),
  updatePrompts: (id: number, prompts: any[]) =>
    put(`${API}/voice-profiles/${id}/prompts`, prompts),

  // Corpus / parse
  parse: (id: number, text: string) =>
    post(`${API}/voice-profiles/${id}/parse`, { text }),
  reset: (id: number) =>
    post(`${API}/voice-profiles/${id}/reset`),

  // Active stack
  getActive: () => fetch(`${API}/voice-profiles/active`).then(json),
  setActive: (baseline_id: number | null, overlay_ids: number[]) =>
    post(`${API}/voice-profiles/active`, { baseline_id, overlay_ids }),

  // Snapshots
  listSnapshots: (id: number) => fetch(`${API}/voice-profiles/${id}/snapshots`).then(json),
  saveSnapshot: (id: number, name: string) =>
    post(`${API}/voice-profiles/${id}/snapshots`, { name }),
  loadSnapshot: (id: number, snapshotId: number) =>
    post(`${API}/voice-profiles/${id}/snapshots/${snapshotId}/load`),
  deleteSnapshot: (id: number, snapshotId: number) =>
    del(`${API}/voice-profiles/${id}/snapshots/${snapshotId}`),

  // Export / import
  exportProfile: (id: number) => fetch(`${API}/voice-profiles/${id}/export`).then(json),
  importProfile: (data: any) =>
    post(`${API}/voice-profiles/import`, data),

  // Style guide
  getStyleGuide: (id: number) => fetch(`${API}/voice-profiles/${id}/style-guide`).then(json),
  getFullGuide: (id: number) => fetch(`${API}/voice-profiles/${id}/full-guide`).then(json),
}
