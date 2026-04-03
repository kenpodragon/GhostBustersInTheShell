import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import CompletenessBar from '../CompletenessBar'
import type { CompletenessData } from '../../types'

function makeStarterData(overrides: Partial<CompletenessData> = {}): CompletenessData {
  return {
    tier: 'starter',
    tier_label: 'Starter',
    pct: 0,
    total_words: 0,
    words_to_next_tier: '~20,000',
    next_tier: 'bronze',
    next_tier_label: 'Bronze',
    elements_converged: 0,
    elements_total: 65,
    categories: {},
    starter_progress: {
      milestone: 0,
      milestone_label: null,
      words_current: 0,
      words_next: 2000,
      milestone_pct: 0,
    },
    guidance: 'Getting started! Submit more writing samples to build your voice profile.',
    ...overrides,
  }
}

describe('CompletenessBar', () => {
  it('renders empty state when data is null', () => {
    render(<CompletenessBar data={null} />)
    expect(screen.getByText(/No convergence data/)).toBeTruthy()
  })

  it('renders Starter with zero words', () => {
    render(<CompletenessBar data={makeStarterData()} />)
    expect(screen.getByText('Starter')).toBeTruthy()
    expect(screen.getByText('0 words')).toBeTruthy()
    expect(screen.getByText(/Getting started/)).toBeTruthy()
  })

  it('renders Starter ½ milestone', () => {
    render(<CompletenessBar data={makeStarterData({
      tier_label: 'Starter ½',
      starter_progress: {
        milestone: 2,
        milestone_label: '½',
        words_current: 7200,
        words_next: 10000,
        milestone_pct: 44,
      },
      guidance: 'Making progress — your voice patterns are beginning to emerge.',
    })} />)
    expect(screen.getByText('Starter ½')).toBeTruthy()
    expect(screen.getByText('7,200 words')).toBeTruthy()
    expect(screen.getByText(/Making progress/)).toBeTruthy()
  })

  it('renders Starter (complete) with convergence info', () => {
    render(<CompletenessBar data={makeStarterData({
      tier_label: 'Starter (complete)',
      pct: 35,
      total_words: 25000,
      starter_progress: {
        milestone: 4,
        milestone_label: 'complete',
        words_current: 25000,
        words_next: 20000,
        milestone_pct: 100,
      },
      guidance: 'Submit diverse writing to reach Bronze.',
    })} />)
    expect(screen.getByText('Starter (complete)')).toBeTruthy()
    expect(screen.getByText(/35% voice convergence/)).toBeTruthy()
  })

  it('renders Bronze tier without starter_progress', () => {
    render(<CompletenessBar data={{
      tier: 'bronze',
      tier_label: 'Bronze',
      pct: 55,
      total_words: 25000,
      words_to_next_tier: '~150,000',
      next_tier: 'silver',
      next_tier_label: 'Silver',
      elements_converged: 36,
      elements_total: 65,
      categories: {},
      guidance: 'Your voice profile is usable. More text will refine accuracy.',
    }} />)
    expect(screen.getByText('Bronze')).toBeTruthy()
    expect(screen.getByText(/55% complete/)).toBeTruthy()
    expect(screen.getByText(/usable/)).toBeTruthy()
  })

  it('renders Gold tier', () => {
    render(<CompletenessBar data={{
      tier: 'gold',
      tier_label: 'Gold',
      pct: 92,
      total_words: 400000,
      words_to_next_tier: null,
      next_tier: null,
      next_tier_label: null,
      elements_converged: 60,
      elements_total: 65,
      categories: {},
      guidance: 'Your voice profile is fully converged. High-fidelity rewrites.',
    }} />)
    expect(screen.getByText('Gold')).toBeTruthy()
    expect(screen.getByText(/92% complete/)).toBeTruthy()
  })

  it('shows starter milestone markers', () => {
    const { container } = render(<CompletenessBar data={makeStarterData()} />)
    const markers = container.querySelectorAll('.completeness-marker')
    expect(markers.length).toBe(4)
    expect(markers[0].getAttribute('title')).toBe('2K words')
  })

  it('shows convergence markers for Bronze+', () => {
    const { container } = render(<CompletenessBar data={{
      tier: 'bronze',
      tier_label: 'Bronze',
      pct: 55,
      total_words: 25000,
      words_to_next_tier: '~150,000',
      next_tier: 'silver',
      next_tier_label: 'Silver',
      elements_converged: 36,
      elements_total: 65,
      categories: {},
    }} />)
    const markers = container.querySelectorAll('.completeness-marker')
    expect(markers.length).toBe(3)
    expect(markers[0].getAttribute('title')).toBe('Bronze (50%)')
  })
})
