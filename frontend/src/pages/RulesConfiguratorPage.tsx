import { useState, useEffect, useCallback } from 'react'
import type { RulesConfig, ConfigSnapshot, VersionInfo } from '../types'
import { rulesApi } from '../services/rulesApi'
import UpdateNotice from '../components/rules/UpdateNotice'
import ConfigBar from '../components/rules/ConfigBar'
import WordListsTab from '../components/rules/WordListsTab'
import WeightsTab from '../components/rules/WeightsTab'
import PipelineTab from '../components/rules/PipelineTab'
import AIPromptTab from '../components/rules/AIPromptTab'

type TabId = 'wordlists' | 'weights' | 'pipeline' | 'prompt'

const TABS: { id: TabId; label: string; adv?: boolean }[] = [
  { id: 'wordlists', label: 'Word Lists' },
  { id: 'weights', label: 'Weights & Thresholds', adv: true },
  { id: 'pipeline', label: 'Pipeline', adv: true },
  { id: 'prompt', label: 'AI Prompt', adv: true },
]

export default function RulesConfiguratorPage() {
  const [config, setConfig] = useState<RulesConfig | null>(null)
  const [defaults, setDefaults] = useState<RulesConfig | null>(null)
  const [snapshots, setSnapshots] = useState<ConfigSnapshot[]>([])
  const [version, setVersion] = useState<VersionInfo | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('wordlists')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [cfg, defs, snaps, ver] = await Promise.all([
        rulesApi.getAllConfig(),
        rulesApi.getDefaults(),
        rulesApi.listSnapshots(),
        rulesApi.getVersion(),
      ])
      setConfig(cfg)
      setDefaults(defs)
      setSnapshots(Array.isArray(snaps) ? snaps : [])
      setVersion(ver)
    } catch (e: any) {
      setError(e?.message || 'Failed to load configuration.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const loadSnapshots = useCallback(async () => {
    try {
      const snaps = await rulesApi.listSnapshots()
      setSnapshots(Array.isArray(snaps) ? snaps : [])
    } catch {}
  }, [])

  const handleUpdate = useCallback(async (section: string, data: any) => {
    try {
      const result = await rulesApi.updateSection(section, data)
      if (result.status === 'success' || result[section] !== undefined) {
        setConfig(prev => prev ? { ...prev, [section]: data } : prev)
      }
    } catch {
      setError('Failed to save changes.')
    }
  }, [])

  if (loading) {
    return (
      <div className="rules-configurator">
        <h2 className="card-header">Rules Configurator</h2>
        <div className="spinner" />
      </div>
    )
  }

  if (error && !config) {
    return (
      <div className="rules-configurator">
        <h2 className="card-header">Rules Configurator</h2>
        <div className="error-message">{error}</div>
        <button className="btn" onClick={loadAll} style={{ marginTop: '1rem' }}>Retry</button>
      </div>
    )
  }

  if (!config) return null

  return (
    <div className="rules-configurator">
      <h2 className="card-header">Rules Configurator</h2>

      <UpdateNotice version={version} onConfigReload={loadAll} />

      <ConfigBar
        snapshots={snapshots}
        onSnapshotsChange={loadSnapshots}
        onConfigReload={loadAll}
      />

      {error && <div className="error-message" style={{ marginBottom: '1rem' }}>{error}</div>}

      <div className="rules-tabs">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`rules-tab ${activeTab === tab.id ? 'rules-tab-active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {tab.adv && <span className="adv-badge">ADV</span>}
          </button>
        ))}
      </div>

      <div className="rules-tab-content card">
        {activeTab === 'wordlists' && (
          <WordListsTab config={config} defaults={defaults} onUpdate={handleUpdate} />
        )}
        {activeTab === 'weights' && (
          <WeightsTab config={config} defaults={defaults} onUpdate={handleUpdate} />
        )}
        {activeTab === 'pipeline' && (
          <PipelineTab config={config} defaults={defaults} onUpdate={handleUpdate} />
        )}
        {activeTab === 'prompt' && (
          <AIPromptTab config={config} defaults={defaults} onUpdate={handleUpdate} />
        )}
      </div>
    </div>
  )
}
