import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import type { Document, Section, ActiveView, SectionRewrite } from '../types'

interface DocumentContextValue {
  document: Document | null
  sections: Section[]
  selectedProfileId: number | null
  loading: boolean
  error: string | null
  activeView: ActiveView
  focusedSectionIndex: number | null
  rewritePanelOpen: boolean

  submitText: (text: string, title?: string) => Promise<void>
  uploadFile: (file: File) => Promise<void>
  analyzeSection: (index: number) => Promise<void>
  analyzeAll: () => Promise<void>
  rewriteSection: (index: number) => Promise<void>
  acceptRewrite: (index: number) => void
  rejectRewrite: (index: number) => void
  updateEditedText: (index: number, text: string) => void
  updateComment: (index: number, comment: string) => void
  regenerateRewrite: (index: number) => Promise<void>
  autoOptimize: (index: number, threshold: number, comment?: string) => Promise<void>
  selectProfile: (id: number | null) => void
  setView: (view: ActiveView) => void
  setFocusedSection: (index: number | null) => void
  setRewritePanelOpen: (open: boolean) => void
  exportMarkdown: () => string
  reset: () => void
}

const DocumentContext = createContext<DocumentContextValue | null>(null)

export function useDocument() {
  const ctx = useContext(DocumentContext)
  if (!ctx) throw new Error('useDocument must be used within DocumentProvider')
  return ctx
}

const emptyRewrite: SectionRewrite = {
  text: null, score: null, classification: null,
  status: 'pending', editedText: null, comment: '', iterations: 0,
}

export function DocumentProvider({ children }: { children: ReactNode }) {
  const [document, setDocument] = useState<Document | null>(null)
  const [sections, setSections] = useState<Section[]>([])
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<ActiveView>('input')
  const [focusedSectionIndex, setFocusedSectionIndex] = useState<number | null>(null)
  const [rewritePanelOpen, setRewritePanelOpen] = useState(false)

  const updateSection = useCallback((index: number, updates: Partial<Section>) => {
    setSections(prev => prev.map((s, i) => i === index ? { ...s, ...updates } : s))
  }, [])

  const submitText = useCallback(async (text: string, title?: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, title, voice_profile_id: selectedProfileId }),
      })
      if (!res.ok) throw new Error((await res.json()).error || 'Failed to create document')
      const data = await res.json()
      setDocument({ id: data.id, title: data.title || title || 'Untitled', rawText: text, sourceType: 'paste' })
      setSections(data.sections.map((s: any) => ({
        id: s.id,
        heading: s.heading,
        text: s.original_text || s.text,
        score: null,
        classification: null,
        patterns: [],
        sentences: [],
        rewrite: { ...emptyRewrite },
        loading: false,
      })))
      setActiveView('sections')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [selectedProfileId])

  const uploadFile = useCallback(async (file: File) => {
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (selectedProfileId) formData.append('voice_profile_id', String(selectedProfileId))
      const res = await fetch('/api/documents', { method: 'POST', body: formData })
      if (!res.ok) throw new Error((await res.json()).error || 'Failed to upload')
      const data = await res.json()
      setDocument({ id: data.id, title: file.name, rawText: '', sourceType: 'upload', fileName: file.name })
      setSections(data.sections.map((s: any) => ({
        id: s.id,
        heading: s.heading,
        text: s.original_text || s.text,
        score: null,
        classification: null,
        patterns: [],
        sentences: [],
        rewrite: { ...emptyRewrite },
        loading: false,
      })))
      setActiveView('sections')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [selectedProfileId])

  const analyzeSection = useCallback(async (index: number) => {
    updateSection(index, { loading: true })
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: sections[index].text }),
      })
      if (!res.ok) throw new Error('Analysis failed')
      const data = await res.json()
      updateSection(index, {
        score: data.overall_score,
        classification: data.classification || null,
        patterns: data.detected_patterns || data.patterns || [],
        sentences: data.sentences || [],
        loading: false,
      })
    } catch {
      updateSection(index, { loading: false })
    }
  }, [sections, updateSection])

  const analyzeAll = useCallback(async () => {
    setLoading(true)
    const promises = sections.map((_, i) => analyzeSection(i))
    await Promise.allSettled(promises)
    setLoading(false)
  }, [sections, analyzeSection])

  const rewriteSection = useCallback(async (index: number) => {
    updateSection(index, { loading: true })
    try {
      const section = sections[index]
      const textToRewrite = section.rewrite.editedText || section.text
      const res = await fetch('/api/rewrite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToRewrite,
          voice_profile_id: selectedProfileId,
          comment: section.rewrite.comment || undefined,
        }),
      })
      if (!res.ok) throw new Error('Rewrite failed')
      const data = await res.json()
      updateSection(index, {
        loading: false,
        rewrite: {
          ...section.rewrite,
          text: data.rewritten_text,
          score: data.score ?? data._after_score ?? null,
          classification: data.classification || null,
          status: 'pending',
          iterations: section.rewrite.iterations + 1,
        },
      })
    } catch {
      updateSection(index, { loading: false })
    }
  }, [sections, selectedProfileId, updateSection])

  const acceptRewrite = useCallback((index: number) => {
    setSections(prev => prev.map((s, i) =>
      i === index ? { ...s, rewrite: { ...s.rewrite, status: 'accepted' as const } } : s
    ))
  }, [])

  const rejectRewrite = useCallback((index: number) => {
    setSections(prev => prev.map((s, i) =>
      i === index ? { ...s, rewrite: { ...s.rewrite, status: 'editing' as const } } : s
    ))
  }, [])

  const updateEditedText = useCallback((index: number, text: string) => {
    setSections(prev => prev.map((s, i) =>
      i === index ? { ...s, rewrite: { ...s.rewrite, editedText: text } } : s
    ))
  }, [])

  const updateComment = useCallback((index: number, comment: string) => {
    setSections(prev => prev.map((s, i) =>
      i === index ? { ...s, rewrite: { ...s.rewrite, comment } } : s
    ))
  }, [])

  const regenerateRewrite = useCallback(async (index: number) => {
    await rewriteSection(index)
  }, [rewriteSection])

  const autoOptimize = useCallback(async (index: number, threshold: number, comment?: string) => {
    updateSection(index, { loading: true })
    try {
      const section = sections[index]
      const textToOptimize = section.rewrite.text || section.text
      const res = await fetch('/api/rewrite/auto-optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToOptimize,
          voice_profile_id: selectedProfileId,
          target_score: threshold,
          max_iterations: 3,
          comment: comment || section.rewrite.comment || undefined,
        }),
      })
      if (!res.ok) throw new Error('Auto-optimize failed')
      const data = await res.json()
      const last = data.iterations[data.iterations.length - 1]
      updateSection(index, {
        loading: false,
        rewrite: {
          ...section.rewrite,
          text: last.rewritten_text,
          score: last.score,
          classification: last.classification || null,
          status: 'pending',
          iterations: section.rewrite.iterations + data.iterations.length,
        },
      })
    } catch {
      updateSection(index, { loading: false })
    }
  }, [sections, selectedProfileId, updateSection])

  const exportMarkdown = useCallback(() => {
    return sections.map((s, i) => {
      const heading = s.heading !== `Section ${i + 1}` ? `# ${s.heading}\n\n` : ''
      const text = s.rewrite.status === 'accepted' && s.rewrite.text ? s.rewrite.text : s.text
      return heading + text
    }).join('\n\n---\n\n')
  }, [sections])

  const reset = useCallback(() => {
    setDocument(null)
    setSections([])
    setError(null)
    setActiveView('input')
    setFocusedSectionIndex(null)
    setRewritePanelOpen(false)
  }, [])

  return (
    <DocumentContext.Provider value={{
      document, sections, selectedProfileId, loading, error,
      activeView, focusedSectionIndex, rewritePanelOpen,
      submitText, uploadFile, analyzeSection, analyzeAll,
      rewriteSection, acceptRewrite, rejectRewrite,
      updateEditedText, updateComment, regenerateRewrite, autoOptimize,
      selectProfile: setSelectedProfileId, setView: setActiveView,
      setFocusedSection: setFocusedSectionIndex,
      setRewritePanelOpen, exportMarkdown, reset,
    }}>
      {children}
    </DocumentContext.Provider>
  )
}
