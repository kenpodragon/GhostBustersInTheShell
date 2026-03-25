const API = 'http://localhost:8066/api'

export const rulesApi = {
  getAllConfig: () => fetch(`${API}/rules/config`).then(r => r.json()),
  getSection: (section: string) => fetch(`${API}/rules/config/${section}`).then(r => r.json()),
  updateSection: (section: string, data: any) =>
    fetch(`${API}/rules/config/${section}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => r.json()),
  getDefaults: () => fetch(`${API}/rules/defaults`).then(r => r.json()),
  revert: () => fetch(`${API}/rules/revert`, { method: 'POST' }).then(r => r.json()),
  listSnapshots: () => fetch(`${API}/rules/snapshots`).then(r => r.json()),
  saveSnapshot: (name: string) =>
    fetch(`${API}/rules/snapshots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }).then(r => r.json()),
  loadSnapshot: (id: number) =>
    fetch(`${API}/rules/snapshots/${id}/load`, { method: 'POST' }).then(r => r.json()),
  deleteSnapshot: (id: number) =>
    fetch(`${API}/rules/snapshots/${id}`, { method: 'DELETE' }).then(r => r.json()),
  checkForUpdates: () => fetch(`${API}/rules/updates/check`).then(r => r.json()),
  applyUpdate: () => fetch(`${API}/rules/updates/apply`, { method: 'POST' }).then(r => r.json()),
  getVersion: () => fetch(`${API}/version`).then(r => r.json()),
}
