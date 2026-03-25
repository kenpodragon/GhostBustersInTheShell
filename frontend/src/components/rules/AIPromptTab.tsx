import { useState, useMemo } from 'react'
import type { RulesConfig } from '../../types'

interface Props {
  config: RulesConfig
  defaults: RulesConfig | null
  onUpdate: (section: string, data: any) => void
}

export default function AIPromptTab({ config, defaults, onUpdate }: Props) {
  const [localPrompt, setLocalPrompt] = useState(config.ai_prompt || '')
  const [saved, setSaved] = useState(false)

  const isModified = useMemo(() => {
    if (!defaults) return false
    return config.ai_prompt !== defaults.ai_prompt
  }, [config.ai_prompt, defaults])

  const isDirty = localPrompt !== config.ai_prompt

  const handleSave = () => {
    onUpdate('ai_prompt', localPrompt)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleReset = () => {
    if (!defaults) return
    setLocalPrompt(defaults.ai_prompt)
    onUpdate('ai_prompt', defaults.ai_prompt)
  }

  // Sync local state when config changes externally
  if (!isDirty && localPrompt !== config.ai_prompt) {
    setLocalPrompt(config.ai_prompt || '')
  }

  return (
    <div className="ai-prompt-tab">
      <div className="ai-prompt-header">
        <div className="ai-prompt-title">
          <span>AI Detection Prompt</span>
          {isModified && <span className="modified-badge">Modified from default</span>}
        </div>
        <div className="ai-prompt-actions">
          <button className="btn btn-small" onClick={handleSave} disabled={!isDirty}>
            {saved ? 'Saved!' : 'Save'}
          </button>
          <button className="btn btn-small btn-danger" onClick={handleReset} disabled={!defaults}>
            Reset to Default
          </button>
        </div>
      </div>

      <textarea
        className="prompt-editor"
        value={localPrompt}
        onChange={e => setLocalPrompt(e.target.value)}
        spellCheck={false}
      />

      <div className="ai-prompt-footer text-muted">
        {localPrompt.length.toLocaleString()} characters
        {isDirty && ' (unsaved changes)'}
      </div>
    </div>
  )
}
