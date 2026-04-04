import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import BaselineUpdateNotice from '../BaselineUpdateNotice'

const mockCheck = vi.fn()
const mockApply = vi.fn()

vi.mock('../../../services/voiceProfilesApi', () => ({
  voiceProfilesApi: {
    checkBaselineUpdates: (...args: any[]) => mockCheck(...args),
    applyBaselineUpdate: (...args: any[]) => mockApply(...args),
  },
}))

describe('BaselineUpdateNotice', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders current baseline version', () => {
    render(
      <BaselineUpdateNotice
        version={{ baseline_version: '1.0.0', baseline_version_date: '2026-04-04' }}
        onUpdate={() => {}}
      />
    )
    expect(screen.getByText(/1\.0\.0/)).toBeDefined()
    expect(screen.getByText(/2026-04-04/)).toBeDefined()
  })

  it('shows up-to-date message after check', async () => {
    mockCheck.mockResolvedValue({ status: 'up_to_date', current_version: '1.0.0', remote_version: '1.0.0' })

    render(
      <BaselineUpdateNotice
        version={{ baseline_version: '1.0.0', baseline_version_date: '2026-04-04' }}
        onUpdate={() => {}}
      />
    )

    fireEvent.click(screen.getByText('Check for Updates'))

    await waitFor(() => {
      expect(screen.getByText(/up to date/i)).toBeDefined()
    })
  })

  it('shows update available with changelog', async () => {
    mockCheck.mockResolvedValue({
      status: 'update_available',
      current_version: '1.0.0',
      remote_version: '1.1.0',
      remote_date: '2026-05-01',
      changelog: 'More articles added',
      app_update_required: false,
    })

    render(
      <BaselineUpdateNotice
        version={{ baseline_version: '1.0.0', baseline_version_date: '2026-04-04' }}
        onUpdate={() => {}}
      />
    )

    fireEvent.click(screen.getByText('Check for Updates'))

    await waitFor(() => {
      expect(screen.getByText(/1\.1\.0/)).toBeDefined()
      expect(screen.getByText(/More articles added/)).toBeDefined()
      expect(screen.getByText('Apply Update')).toBeDefined()
    })
  })

  it('calls onUpdate after successful apply', async () => {
    mockCheck.mockResolvedValue({
      status: 'update_available',
      current_version: '1.0.0',
      remote_version: '1.1.0',
      changelog: 'Update',
      app_update_required: false,
    })
    mockApply.mockResolvedValue({ success: true, version: '1.1.0', baseline_id: 42 })

    const onUpdate = vi.fn()

    render(
      <BaselineUpdateNotice
        version={{ baseline_version: '1.0.0', baseline_version_date: '2026-04-04' }}
        onUpdate={onUpdate}
      />
    )

    fireEvent.click(screen.getByText('Check for Updates'))
    await waitFor(() => screen.getByText('Apply Update'))

    fireEvent.click(screen.getByText('Apply Update'))
    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalled()
      expect(screen.getByText(/applied successfully/i)).toBeDefined()
    })
  })
})
