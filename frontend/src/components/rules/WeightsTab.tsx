import { useMemo } from 'react'
import type { RulesConfig } from '../../types'

interface Props {
  config: RulesConfig
  defaults: RulesConfig | null
  onUpdate: (section: string, data: any) => void
}

export default function WeightsTab({ config, defaults, onUpdate }: Props) {
  const sortedWeights = useMemo(() => {
    const entries = Object.entries(config.heuristic_weights || {})
    return entries.sort((a, b) => {
      if (a[1] === 0 && b[1] !== 0) return 1
      if (a[1] !== 0 && b[1] === 0) return -1
      return a[0].localeCompare(b[0])
    })
  }, [config.heuristic_weights])

  const updateWeight = (key: string, value: number) => {
    onUpdate('heuristic_weights', { ...config.heuristic_weights, [key]: value })
  }

  const updateClassification = (key: string, value: number) => {
    onUpdate('classification', { ...config.classification, [key]: value })
  }

  const updateSeverity = (key: string, value: any) => {
    onUpdate('severity', { ...config.severity, [key]: value })
  }

  const isModified = (section: string, key: string, value: any): boolean => {
    if (!defaults) return false
    const defaultSection = (defaults as any)[section]
    if (!defaultSection) return false
    return defaultSection[key] !== value
  }

  return (
    <div className="weights-tab">
      <div className="weights-section">
        <div className="card-header">Heuristic Weights</div>
        <div className="weights-list">
          {sortedWeights.map(([key, value]) => (
            <div key={key} className={`weight-row ${value === 0 ? 'weight-killed' : ''}`}>
              {isModified('heuristic_weights', key, value) && <span className="modified-dot" />}
              <span className="weight-name">{key.replace(/_/g, ' ')}</span>
              <input
                type="range"
                className="weight-slider"
                min={0}
                max={1}
                step={0.05}
                value={value}
                onChange={e => updateWeight(key, parseFloat(e.target.value))}
              />
              <input
                type="number"
                className="weight-value"
                min={0}
                max={1}
                step={0.05}
                value={value}
                onChange={e => updateWeight(key, parseFloat(e.target.value) || 0)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="weights-section">
        <div className="card-header">Classification Boundaries</div>
        <div className="weights-grid">
          {Object.entries(config.classification || {}).map(([key, value]) => (
            <div key={key} className="weight-field">
              {isModified('classification', key, value) && <span className="modified-dot" />}
              <label>{key.replace(/_/g, ' ')}</label>
              <input
                type="number"
                value={value}
                onChange={e => updateClassification(key, parseFloat(e.target.value) || 0)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="weights-section">
        <div className="card-header">Severity Multipliers</div>
        <div className="weights-grid">
          {Object.entries(config.severity || {}).map(([key, value]) => (
            <div key={key} className="weight-field">
              {isModified('severity', key, value) && <span className="modified-dot" />}
              <label>{key.replace(/_/g, ' ')}</label>
              <input
                type="number"
                step={0.1}
                value={typeof value === 'number' ? value : 0}
                onChange={e => updateSeverity(key, parseFloat(e.target.value) || 0)}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
