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

// --- Scoring & AI Extraction Types ---

export interface FidelityScoreResult {
  mode: 'quantitative' | 'qualitative' | 'both'
  quantitative?: {
    aggregate_similarity: number
    per_element: ElementScore[]
    matched: number
    missing: number
  }
  qualitative?: {
    matches: string[]
    gaps: string[]
    overall_assessment: string
  }
}

export interface ElementScore {
  name: string
  profile_value: number
  generated_value: number
  similarity: number
  weight: number
}

export interface AIExtraction {
  status: 'success' | 'skipped' | 'error'
  qualitative_prompts: QualitativePrompt[]
  metric_descriptions: MetricDescription[]
  discovered_patterns: DiscoveredPattern[]
}

export interface QualitativePrompt {
  prompt: string
  confidence: number
}

export interface MetricDescription {
  element: string
  value: number
  description: string
  ai_assessment: 'accurate' | 'misleading' | 'insufficient_data'
}

export interface DiscoveredPattern {
  pattern: string
  suggested_element_name: string
  description: string
}

export interface ConsolidatedPrompt {
  prompt: string
  source_prompts: string[]
  frequency: number
  confidence: number
}

export interface ConsolidationResult {
  consolidated_prompts: ConsolidatedPrompt[]
  metric_consensus: MetricConsensus[]
  discovered_patterns: DiscoveredPatternAgg[]
  observation_count: number
  document_count: number
}

export interface MetricConsensus {
  element: string
  consensus_description: string
  agreement_count: number
  disagreement_count: number
  flagged_misleading: boolean
}

export interface DiscoveredPatternAgg {
  suggested_element_name: string
  pattern: string
  description: string
  occurrences: number
}

export interface CorpusDocument {
  id: number
  filename: string
  word_count: number
  created_at: string
  has_ai_observations: boolean
}

export interface CorpusInfo {
  documents: CorpusDocument[]
  stats: {
    total_documents: number
    total_words: number
    ai_observations_count: number
  }
}

export interface ReparseResult {
  old_profile_id: number
  new_profile_id: number
  parsed_count: number
  total_documents: number
  errors: { document_id: number; filename: string; error: string }[]
  old_elements: ProfileElement[]
  new_elements: ProfileElement[]
  snapshot_name: string
}

export interface ParseResult {
  elements: ProfileElement[]
  findings: string[]
  parse_count: number
  document_id: number
  ai_extraction: AIExtraction
  same_name_warning?: string
}

export interface CategoryConvergenceStatus {
  converged: number
  total: number
  status: 'complete' | 'good' | 'needs_more'
}

export interface StarterProgress {
  milestone: number
  milestone_label: string | null
  words_current: number
  words_next: number
  milestone_pct: number
}

export interface BaselineUpdateCheckResult {
  status: 'up_to_date' | 'update_available'
  current_version: string
  remote_version: string
  remote_date?: string
  changelog?: string
  min_app_version?: string
  app_version?: string
  app_update_required?: boolean
}

export interface BaselineUpdateApplyResult {
  success: boolean
  version?: string
  baseline_id?: number
  error?: string
}

export interface CompletenessData {
  tier: 'starter' | 'bronze' | 'silver' | 'gold' | null
  tier_label: string | null
  pct: number
  total_words: number
  words_to_next_tier: string | null
  next_tier: string | null
  next_tier_label: string | null
  elements_converged: number
  elements_total: number
  newly_converged?: string[]
  categories: Record<string, CategoryConvergenceStatus>
  starter_progress?: StarterProgress
  guidance?: string
}
