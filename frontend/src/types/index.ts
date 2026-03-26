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
  profile_type: 'baseline' | 'overlay'
  parse_count: number
  is_active: boolean
  stack_order: number
  created_at: string
  updated_at: string
}

export interface ProfileElement {
  id: number
  name: string
  category: 'lexical' | 'character' | 'syntactic' | 'structural' | 'content' | 'idiosyncratic'
  element_type: 'directional' | 'metric'
  direction?: 'more' | 'less'
  weight: number
  target_value?: number
  tags: string[]
  source: 'parsed' | 'manual'
}

export interface ProfilePrompt {
  id?: number
  prompt_text: string
  sort_order: number
}

export interface ProfileSnapshot {
  id: number
  snapshot_name: string
  created_at: string
}

export interface ActiveStack {
  baseline: { id: number; name: string } | null
  overlays: { id: number; name: string }[]
  resolved_elements: ProfileElement[]
  prompts: ProfilePrompt[]
}

export interface VoiceProfileFull extends VoiceProfile {
  elements: ProfileElement[]
  prompts: ProfilePrompt[]
}

export interface AIStatus {
  ai_enabled: boolean
  ai_provider: string
  ai_runtime_available: boolean
  ai_runtime_error: string | null
}

export interface RulesConfig {
  heuristic_weights: Record<string, number>
  buzzwords: Record<string, string[]>
  ai_phrases: Record<string, string[]>
  word_lists: Record<string, string[]>
  thresholds: Record<string, any>
  classification: Record<string, number>
  severity: Record<string, any>
  pipeline: Record<string, number>
  ai_prompt: string
}

export interface ConfigSnapshot {
  id: number
  name: string
  created_at: string
}

export interface UpdateCheckResult {
  status: 'update_available' | 'up_to_date' | 'error'
  current_version: string
  current_date: string | null
  remote_version: string
  remote_date: string
  changelog: string
  app_update_required: boolean
  min_app_version: string
  app_version: string
  error?: string
}

export interface VersionInfo {
  app_version: string
  rules_version: string
  rules_version_date: string | null
}
