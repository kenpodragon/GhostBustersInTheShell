import { useState, useMemo } from 'react'
import type { RulesConfig } from '../../types'

interface Props {
  config: RulesConfig
  defaults: RulesConfig | null
  onUpdate: (section: string, data: any) => void
}

interface CategoryEntry {
  section: string
  category: string
  label: string
}

export default function WordListsTab({ config, defaults, onUpdate }: Props) {
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [search, setSearch] = useState('')
  const [newWord, setNewWord] = useState('')

  const categories = useMemo(() => {
    const result: CategoryEntry[] = []
    const addSection = (sectionKey: string, label: string, data: Record<string, string[]>) => {
      for (const cat of Object.keys(data || {})) {
        result.push({ section: sectionKey, category: cat, label: `${label} > ${cat}` })
      }
    }
    addSection('buzzwords', 'Buzzwords', config.buzzwords)
    addSection('ai_phrases', 'AI Phrases', config.ai_phrases)
    addSection('word_lists', 'Word Lists', config.word_lists)
    return result
  }, [config.buzzwords, config.ai_phrases, config.word_lists])

  const selected = categories[selectedIdx] || null

  // Active words = what's currently in the config array
  const activeWords = useMemo(() => {
    if (!selected) return new Set<string>()
    const section = (config as any)[selected.section] as Record<string, string[]> | undefined
    const words = section?.[selected.category]
    return new Set(Array.isArray(words) ? words : [])
  }, [config, selected])

  // Default words = what shipped with the app
  const defaultWords = useMemo(() => {
    if (!defaults || !selected) return new Set<string>()
    const section = (defaults as any)[selected.section] as Record<string, string[]> | undefined
    const words = section?.[selected.category]
    return new Set(Array.isArray(words) ? words : [])
  }, [defaults, selected])

  // Built-in words: everything in defaults (always shown, toggle on/off)
  const builtInWords = useMemo(() => {
    const words = Array.from(defaultWords).sort()
    if (!search) return words
    const q = search.toLowerCase()
    return words.filter(w => w.toLowerCase().includes(q))
  }, [defaultWords, search])

  // Custom words: in active but NOT in defaults
  const customWords = useMemo(() => {
    const words = Array.from(activeWords).filter(w => !defaultWords.has(w)).sort()
    if (!search) return words
    const q = search.toLowerCase()
    return words.filter(w => w.toLowerCase().includes(q))
  }, [activeWords, defaultWords, search])

  // Count for sidebar
  const getCategoryCount = (cat: CategoryEntry) => {
    const section = (config as any)[cat.section] as Record<string, string[]> | undefined
    const words = section?.[cat.category]
    return Array.isArray(words) ? words.length : 0
  }

  const toggleWord = (word: string) => {
    if (!selected) return
    const sectionData = { ...(config as any)[selected.section] } as Record<string, string[]>
    const words = [...(sectionData[selected.category] || [])]
    const idx = words.indexOf(word)
    if (idx >= 0) {
      words.splice(idx, 1) // turn off
    } else {
      words.push(word) // turn on
    }
    sectionData[selected.category] = words
    onUpdate(selected.section, sectionData)
  }

  const addWord = () => {
    const word = newWord.trim().toLowerCase()
    if (!word || !selected) return
    if (activeWords.has(word)) {
      setNewWord('')
      return
    }
    const sectionData = { ...(config as any)[selected.section] } as Record<string, string[]>
    const words = [...(sectionData[selected.category] || []), word]
    sectionData[selected.category] = words
    onUpdate(selected.section, sectionData)
    setNewWord('')
  }

  const deleteWord = (word: string) => {
    if (!selected) return
    const sectionData = { ...(config as any)[selected.section] } as Record<string, string[]>
    const words = (sectionData[selected.category] || []).filter(w => w !== word)
    sectionData[selected.category] = words
    onUpdate(selected.section, sectionData)
  }

  return (
    <div className="word-lists-tab">
      <div className="word-lists-search">
        <input
          type="text"
          placeholder="Search all word lists..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className="word-lists-layout">
        <div className="word-lists-sidebar">
          <div className="category-list">
            {categories.map((cat, idx) => (
              <div
                key={cat.label}
                className={`category-item ${idx === selectedIdx ? 'category-active' : ''}`}
                onClick={() => { setSelectedIdx(idx); setSearch('') }}
              >
                <span className="category-name">{cat.label}</span>
                <span className="category-count">{getCategoryCount(cat)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="word-lists-main">
          {selected && (
            <>
              <div className="word-add-row">
                <input
                  type="text"
                  placeholder="Add custom word..."
                  value={newWord}
                  onChange={e => setNewWord(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addWord()}
                />
                <button className="btn btn-small" onClick={addWord} disabled={!newWord.trim()}>
                  Add
                </button>
              </div>

              {/* Built-in words */}
              <div className="word-section-label">Built-in ({builtInWords.length})</div>
              <div className="word-chips">
                {builtInWords.map(word => {
                  const isOn = activeWords.has(word)
                  return (
                    <span
                      key={word}
                      className={`word-chip ${isOn ? 'word-chip-on' : 'word-chip-off'}`}
                      onClick={() => toggleWord(word)}
                      title={isOn ? 'Click to disable' : 'Click to enable'}
                    >
                      {word}
                      {!isOn && <span className="word-chip-x">✕</span>}
                    </span>
                  )
                })}
                {builtInWords.length === 0 && (
                  <span className="text-muted">No built-in words {search ? 'match' : 'in this category'}.</span>
                )}
              </div>

              {/* Custom words */}
              {(customWords.length > 0 || !search) && (
                <>
                  <hr className="word-divider" />
                  <div className="word-section-label">Custom ({customWords.length})</div>
                  <div className="word-chips">
                    {customWords.map(word => {
                      const isOn = activeWords.has(word)
                      return (
                        <span
                          key={word}
                          className={`word-chip word-chip-custom ${isOn ? 'word-chip-on' : 'word-chip-off'}`}
                          onClick={() => toggleWord(word)}
                          title={isOn ? 'Click to disable' : 'Click to enable'}
                        >
                          {word}
                          {!isOn && <span className="word-chip-x">✕</span>}
                          <button
                            className="word-chip-trash"
                            onClick={e => { e.stopPropagation(); deleteWord(word) }}
                            title="Delete custom word"
                          >
                            🗑
                          </button>
                        </span>
                      )
                    })}
                    {customWords.length === 0 && !search && (
                      <span className="text-muted">No custom words yet. Use the input above to add.</span>
                    )}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
