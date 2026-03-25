// code/frontend/src/components/RulesEditor.tsx
import { useState, useEffect } from 'react'

interface VoiceRule {
  id: number
  part: string
  rule_type: string
  rule_text: string
  weight: number
}

interface Props {
  profileId: number
  onClose: () => void
}

export default function RulesEditor({ profileId, onClose }: Props) {
  const [rules, setRules] = useState<VoiceRule[]>([])
  const [defaults, setDefaults] = useState<VoiceRule[]>([])
  const [loading, setLoading] = useState(true)
  const [showDefaults, setShowDefaults] = useState(false)

  useEffect(() => {
    Promise.all([
      fetch(`/api/voice-profiles/${profileId}`).then(r => r.json()),
      fetch('/api/voice-profiles/defaults').then(r => r.json()),
    ]).then(([profile, defaultData]) => {
      // Parse rules from profile
      const parsed = typeof profile.rules_json === 'string'
        ? JSON.parse(profile.rules_json)
        : profile.rules_json
      setRules(Array.isArray(parsed) ? parsed : [])
      setDefaults(defaultData.rules || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [profileId])

  const handleRemoveRule = (index: number) => {
    setRules(prev => prev.filter((_, i) => i !== index))
  }

  const handleWeightChange = (index: number, weight: number) => {
    setRules(prev => prev.map((r, i) => i === index ? { ...r, weight } : r))
  }

  const handleAddRule = () => {
    setRules(prev => [...prev, { id: 0, part: 'custom', rule_type: 'banned_word', rule_text: '', weight: 1.0 }])
  }

  const handleRuleTextChange = (index: number, text: string) => {
    setRules(prev => prev.map((r, i) => i === index ? { ...r, rule_text: text } : r))
  }

  const handleSave = async () => {
    await fetch(`/api/voice-profiles/${profileId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rules_json: JSON.stringify(rules) }),
    })
    onClose()
  }

  const handleResetDefaults = () => {
    if (confirm('Reset all rules to defaults? Your custom rules will be lost.')) {
      setRules(defaults)
    }
  }

  // Group rules by part/category
  const grouped = rules.reduce((acc: Record<string, Array<VoiceRule & { _index: number }>>, rule, index) => {
    const key = rule.part || 'uncategorized'
    if (!acc[key]) acc[key] = []
    acc[key].push({ ...rule, _index: index })
    return acc
  }, {})

  if (loading) return <div className="text-muted">Loading rules...</div>

  return (
    <div className="rules-editor">
      <div className="rules-editor-header">
        <h2 style={{ fontSize: '1rem', margin: 0 }}>Rules Editor</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-small" onClick={handleAddRule}>[ + ADD RULE ]</button>
          <button className="btn btn-small" onClick={handleResetDefaults}>[ RESET DEFAULTS ]</button>
          <button className="btn btn-small" onClick={() => setShowDefaults(!showDefaults)}>
            [ {showDefaults ? 'HIDE' : 'CHECK'} UPDATES ]
          </button>
        </div>
      </div>

      {showDefaults && (
        <div className="card" style={{ marginBottom: '1rem', fontSize: '0.8rem' }}>
          <div className="card-header">Default Rules ({defaults.length} rules)</div>
          <p className="text-muted">
            Your profile has {rules.length} rules vs {defaults.length} defaults.
            Click "Reset Defaults" to replace your rules with the latest defaults.
          </p>
        </div>
      )}

      {Object.entries(grouped).map(([category, categoryRules]) => (
        <div key={category} className="rules-category">
          <div className="card-header">{category} ({categoryRules.length})</div>
          {categoryRules.map(rule => (
            <div key={rule._index} className="rule-row">
              <input
                className="select-input rule-text"
                value={rule.rule_text}
                onChange={e => handleRuleTextChange(rule._index, e.target.value)}
              />
              <input
                type="number"
                className="threshold-input"
                value={rule.weight}
                onChange={e => handleWeightChange(rule._index, Number(e.target.value))}
                min={0}
                max={2}
                step={0.1}
              />
              <button
                className="btn btn-small btn-reject"
                onClick={() => handleRemoveRule(rule._index)}
              >
                [ × ]
              </button>
            </div>
          ))}
        </div>
      ))}

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
        <button className="btn btn-small" onClick={onClose}>[ CANCEL ]</button>
        <button className="btn" onClick={handleSave}>[ SAVE RULES ]</button>
      </div>
    </div>
  )
}
