import type { RulesConfig } from '../../types'

interface Props {
  config: RulesConfig
  defaults: RulesConfig | null
  onUpdate: (section: string, data: any) => void
}

interface FieldGroup {
  title: string
  keys: string[]
}

const GROUPS: FieldGroup[] = [
  {
    title: 'AI / Heuristic Blend',
    keys: ['ai_weight', 'heuristic_weight'],
  },
  {
    title: 'Composite Tier Weights',
    keys: ['sentence_weight', 'paragraph_weight', 'document_weight'],
  },
  {
    title: 'Bonuses & Dampening',
    keys: ['convergence_bonus', 'density_bonus', 'genre_dampening'],
  },
]

export default function PipelineTab({ config, defaults, onUpdate }: Props) {
  const pipeline = config.pipeline || {}

  const updateField = (key: string, value: number) => {
    onUpdate('pipeline', { ...pipeline, [key]: value })
  }

  const isModified = (key: string): boolean => {
    if (!defaults?.pipeline) return false
    return defaults.pipeline[key] !== pipeline[key]
  }

  // Collect ungrouped keys
  const groupedKeys = new Set(GROUPS.flatMap(g => g.keys))
  const ungroupedKeys = Object.keys(pipeline).filter(k => !groupedKeys.has(k))

  return (
    <div className="pipeline-tab">
      {GROUPS.map(group => {
        const visibleKeys = group.keys.filter(k => k in pipeline)
        if (visibleKeys.length === 0) return null
        return (
          <div key={group.title} className="pipeline-section">
            <div className="card-header">{group.title}</div>
            <div className="pipeline-fields">
              {visibleKeys.map(key => (
                <div key={key} className="pipeline-field">
                  {isModified(key) && <span className="modified-dot" />}
                  <label>{key.replace(/_/g, ' ')}</label>
                  <input
                    type="number"
                    step={0.05}
                    value={pipeline[key] ?? 0}
                    onChange={e => updateField(key, parseFloat(e.target.value) || 0)}
                  />
                </div>
              ))}
            </div>
          </div>
        )
      })}

      {ungroupedKeys.length > 0 && (
        <div className="pipeline-section">
          <div className="card-header">Other</div>
          <div className="pipeline-fields">
            {ungroupedKeys.map(key => (
              <div key={key} className="pipeline-field">
                {isModified(key) && <span className="modified-dot" />}
                <label>{key.replace(/_/g, ' ')}</label>
                <input
                  type="number"
                  step={0.05}
                  value={pipeline[key] ?? 0}
                  onChange={e => updateField(key, parseFloat(e.target.value) || 0)}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
