export interface Pattern {
  pattern: string
  detail: string
  source?: 'ai' | 'heuristic'
}

export interface SentenceResult {
  index: number
  text: string
  score: number
  patterns: Pattern[]
}

export interface Classification {
  category: string        // clean | ghost_touched | ghost_written
  label: string           // Clean | Ghost Touched | Ghost Written
  confidence: string      // high | medium | low
}

export interface SectionRewrite {
  text: string | null
  score: number | null
  classification: Classification | null
  status: 'pending' | 'accepted' | 'rejected' | 'editing'
  editedText: string | null
  comment: string
  iterations: number
}

export interface Section {
  id: number
  heading: string
  text: string
  score: number | null
  classification: Classification | null
  patterns: Pattern[]
  sentences: SentenceResult[]
  rewrite: SectionRewrite
  loading: boolean
}

export interface Document {
  id: number | null
  title: string
  rawText: string
  sourceType: 'paste' | 'upload'
  fileName?: string
}

export type ActiveView = 'input' | 'sections' | 'focus' | 'preview'

export interface VoiceProfile {
  id: number
  name: string
  description: string
  created_at: string
}

export interface AIStatus {
  ai_enabled: boolean
  ai_provider: string
  ai_runtime_available: boolean
  ai_runtime_error: string | null
}
