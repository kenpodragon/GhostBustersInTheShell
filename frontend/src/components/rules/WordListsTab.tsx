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
  words: string[]
}

export default function WordListsTab({ config, defaults, onUpdate }: Props) {
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [search, setSearch] = useState('')
  const [newWord, setNewWord] = useState('')

  const categories = useMemo(() => {
    const result: CategoryEntry[] = []
    const addSection = (sectionKey: string, label: string, data: Record<string, string[]>) => {
      for (const [cat, words] of Object.entries(data || {})) {
        result.push({ section: sectionKey, category: cat, label: `${label} > ${cat}`, words })
      }
    }
    addSection('buzzwords', 'Buzzwords', config.buzzwords)
    addSection('ai_phrases', 'AI Phrases', config.ai_phrases)
    addSection('word_lists', 'Word Lists', config.word_lists)
    return result
  }, [config.buzzwords, config.ai_phrases, config.word_lists])

  const selected = categories[selectedIdx] || null
  const defaultWords = useMemo(() => {
    if (!defaults || !selected) return new Set<string>()
    const section = (defaults as any)[selected.section] as Record<string, string[]> | undefined
    const words = section?.[selected.category]
    return new Set(Array.isArray(words) ? words : [])
  }, [defaults, selected])

  const filteredWords = useMemo(() => {
    if (!selected) return []
    if (!search) return selected.words
    const q = search.toLowerCase()
    return selected.words.filter(w => w.toLowerCase().includes(q))
  }, [selected, search])

  const searchResults = useMemo(() => {
    if (!search) return null
    const q = search.toLowerCase()
    const results: { idx: number; word: string }[] = []
    categories.forEach((cat, idx) => {
      cat.words.forEach(w => {
        if (w.toLowerCase().includes(q)) results.push({ idx, word: w })
      })
    })
    return results
  }, [search, categories])

  const toggleWord = (word: string) => {
    if (!selected) return
    const sectionData = { ...(config as any)[selected.section] } as Record<string, string[]>
    const words = [...(sectionData[selected.category] || [])]
    const idx = words.indexOf(word)
    if (idx >= 0) {
      words.splice(idx, 1)
    } else {
      words.push(word)
    }
    sectionData[selected.category] = words
    onUpdate(selected.section, sectionData)
  }

  const addWord = () => {
    const word = newWord.trim().toLowerCase()
    if (!word || !selected) return
    const sectionData = { ...(config as any)[selected.section] } as Record<string, string[]>
    const words = [...(sectionData[selected.category] || [])]
    if (!words.includes(word)) {
      words.push(word)
      sectionData[selected.category] = words
      onUpdate(selected.section, sectionData)
    }
    setNewWord('')
  }

  const removeWord = (word: string) => {
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
                <span className="category-count">{cat.words.length}</span>
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
                  placeholder="Add word..."
                  value={newWord}
                  onChange={e => setNewWord(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addWord()}
                />
                <button className="btn btn-small" onClick={addWord} disabled={!newWord.trim()}>
                  Add
                </button>
              </div>

              {search && searchResults && searchResults.length > 0 && (
                <div className="search-results-info text-muted">
                  {searchResults.length} match{searchResults.length !== 1 ? 'es' : ''} across {new Set(searchResults.map(r => r.idx)).size} categories
                </div>
              )}

              <div className="word-chips">
                {filteredWords.map(word => {
                  const isDefault = defaultWords.has(word)
                  const isActive = selected.words.includes(word)
                  return (
                    <span
                      key={word}
                      className={`word-chip ${isActive ? 'word-chip-active' : 'word-chip-disabled'}`}
                      onClick={() => isDefault ? toggleWord(word) : undefined}
                    >
                      {word}
                      {!isDefault && (
                        <button
                          className="word-chip-delete"
                          onClick={e => { e.stopPropagation(); removeWord(word) }}
                          title="Remove custom word"
                        >
                          x
                        </button>
                      )}
                    </span>
                  )
                })}
                {filteredWords.length === 0 && (
                  <span className="text-muted">No words {search ? 'match' : 'in this category'}.</span>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
