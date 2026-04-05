import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AnalysisReport from '../AnalysisReport'
import type { EnrichedAnalyzeResponse, ClassificationBoundaries } from '../../types'

const mockBoundaries: ClassificationBoundaries = {
  clean_upper: 20,
  ghost_written_lower: 40,
}

const mockData: EnrichedAnalyzeResponse = {
  overall_score: 53.8,
  classification: { category: 'ghost_written', label: 'Ghost Written', confidence: 'high' },
  confidence: [45.0, 62.0],
  genre: 'general',
  signal_count: 12,
  tiers: {
    sentence_score: 53.8,
    paragraph_score: 53.7,
    document_score: 54.0,
    score_math: {
      sentence_weighted: 24.2,
      paragraph_weighted: 16.1,
      document_weighted: 13.5,
      convergence_bonus: 0.0,
      cross_tier_bonus: 0.0,
      genre_dampening: 0.0,
      raw_composite: 53.8,
      final_score: 53.8,
    },
  },
  document_patterns: [
    { pattern: 'hedge_cluster', name: 'hedge_cluster', display_name: 'Hedge Clustering', description: 'Groups of hedging words appear in close proximity.', severity: 'high', count: 4 },
    { pattern: 'transition_stacks', name: 'transition_stacks', display_name: 'Transition Stacking', description: 'Transition words stacked in sequence.', severity: 'medium' },
  ],
  paragraphs: [
    {
      index: 0,
      text: 'In the rapidly evolving landscape...',
      score: 68.2,
      sentence_count: 2,
      patterns: [
        { pattern: 'para_uniform_sentences', name: 'para_uniform_sentences', display_name: 'Uniform Sentences', description: 'Low structural variety.' },
      ],
      sentences: [
        { index: 0, text: 'In the rapidly evolving landscape of technology.', score: 72.1, patterns: [{ pattern: 'buzzword', name: 'buzzword', display_name: 'Buzzword', description: 'AI buzzword.' }] },
        { index: 1, text: 'Furthermore, it is essential.', score: 65.0, patterns: [{ pattern: 'ai_transition', name: 'ai_transition', display_name: 'AI Transition', description: 'Formulaic transition.' }] },
      ],
    },
    {
      index: 1,
      text: 'This paragraph is clean.',
      score: 12.4,
      sentence_count: 1,
      patterns: [],
      sentences: [
        { index: 2, text: 'This paragraph is clean.', score: 12.4, patterns: [] },
      ],
    },
  ],
  sentences: [],
  detected_patterns: [],
}

describe('AnalysisReport', () => {
  it('renders two-column layout', () => {
    const { container } = render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    expect(container.querySelector('.analysis-report__left')).toBeTruthy()
    expect(container.querySelector('.analysis-report__right')).toBeTruthy()
  })

  it('renders temperature gauge', () => {
    const { container } = render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    expect(container.querySelector('.temperature-gauge')).toBeTruthy()
    expect(container.querySelector('.temperature-gauge__needle')).toBeTruthy()
  })

  it('renders tier score boxes', () => {
    render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    expect(screen.getByText('Sentence')).toBeTruthy()
    expect(screen.getByText('Paragraph')).toBeTruthy()
    expect(screen.getByText('Document')).toBeTruthy()
  })

  it('renders document patterns', () => {
    render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    expect(screen.getByText('Hedge Clustering')).toBeTruthy()
    expect(screen.getByText('Transition Stacking')).toBeTruthy()
  })

  it('auto-expands high-score paragraphs', () => {
    render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    expect(screen.getByText(/rapidly evolving/)).toBeTruthy()
    expect(screen.getByText(/Furthermore/)).toBeTruthy()
  })

  it('collapses low-score paragraphs', () => {
    render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    expect(screen.queryByText(/This paragraph is clean/)).toBeFalsy()
  })

  it('expands collapsed paragraph on click', () => {
    render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    const para2Header = screen.getByText('Paragraph 2')
    fireEvent.click(para2Header.closest('.paragraph-accordion__header')!)
    expect(screen.getByText(/This paragraph is clean/)).toBeTruthy()
  })

  it('score math expander starts collapsed', () => {
    const { container } = render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    expect(container.querySelector('.score-math-expander__body')).toBeFalsy()
  })

  it('score math expander shows formula on click', () => {
    const { container } = render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    const expander = container.querySelector('.score-math-expander')!
    fireEvent.click(expander)
    expect(container.querySelector('.score-math-expander__body')).toBeTruthy()
    expect(screen.getByText('Final Score')).toBeTruthy()
  })

  it('pattern chips show description as title tooltip', () => {
    const { container } = render(<AnalysisReport data={mockData} boundaries={mockBoundaries} />)
    const chip = container.querySelector('.analysis-pattern-chip[title]')
    expect(chip).toBeTruthy()
    expect(chip!.getAttribute('title')).not.toBe('')
  })
})
