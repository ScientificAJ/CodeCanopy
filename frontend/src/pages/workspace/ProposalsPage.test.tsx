import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import ProposalsPage from './ProposalsPage'
import { getSlot } from '../../contexts/SlotRegistry'
import '../../features/drafts/register'
import '../../features/onboarding/register'

vi.mock('../../components/slots/SlotMount', () => ({
  SlotMount: ({id}: {id: string}) => <div data-testid="active-proposal">{id}</div>,
}))

afterEach(cleanup)

it('keeps AI drafts and source-derived suggestions available as separate registrations', () => {
  const draft = getSlot('proposals.detail')
  const derived = getSlot('proposals.derived')
  expect(draft).toBeDefined()
  expect(derived).toBeDefined()
  expect(draft?.Component).not.toBe(derived?.Component)
  expect(draft?.load).toBeUndefined()
  expect(derived?.load).toBeTypeOf('function')
  expect(getSlot('docs.generated')).toBeDefined()
})

it('starts with the demo drafting workflow and lets the user open source-derived suggestions', () => {
  render(<ProposalsPage/>)
  expect(screen.getByTestId('active-proposal').textContent).toBe('proposals.detail')
  fireEvent.click(screen.getByRole('button', {name: 'Source-derived suggestions'}))
  expect(screen.getByTestId('active-proposal').textContent).toBe('proposals.derived')
  expect(screen.getByRole('button', {name: 'Source-derived suggestions'}).getAttribute('aria-pressed')).toBe('true')
  fireEvent.click(screen.getByRole('button', {name: 'AI-assisted plan'}))
  expect(screen.getByTestId('active-proposal').textContent).toBe('proposals.detail')
})
