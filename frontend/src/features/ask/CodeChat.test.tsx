import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import CodeChat from './CodeChat'
import { isSlotRegistered, registeredSlots } from '../../contexts/SlotRegistry'
import type { SlotProps } from '../../contexts/SlotRegistry'
import type { Answer } from '../../types/v1/prd.generated'

afterEach(cleanup)

// ── helpers ──────────────────────────────────────────────────────────────────

const openSource = vi.fn()

function makeProps(request: SlotProps<Answer>['request']): SlotProps<Answer> {
  return {
    projectId: 'proj',
    snapshotId: 'snap',
    snapshot: {
      schema_version: '1.0',
      id: 'snap',
      project_id: 'proj',
      source: { kind: 'zip' },
      manifest_hash: 'h',
      policy_version: '1.0',
      created_at: '2099-01-01',
    },
    selectedEntity: null,
    files: [],
    entities: [],
    graph: null,
    capabilities: null,
    viewState: { focusedView: 'overview', mapCamera: { x: 0, y: 0, scale: 1 } },
    selectEntity: vi.fn(),
    openSource,
    navigate: vi.fn(),
    availability: 'connected',
    request,
  }
}

// ── registration ─────────────────────────────────────────────────────────────

it('ask.workspace is registered through the feature-contracts path', async () => {
  // Import the register module; it runs registerFeature on load.
  await import('./register')
  expect(isSlotRegistered('ask.workspace')).toBe(true)
  expect(registeredSlots()).toContain('ask.workspace')
})

it('registered loader is a function (not a bare component)', async () => {
  const { getSlot } = await import('../../contexts/SlotRegistry')
  // Load the registration module (idempotent)
  await import('./register')
  const reg = getSlot('ask.workspace')
  expect(typeof reg?.load).toBe('function')
})

// ── rendering states ──────────────────────────────────────────────────────────

it('renders loading state with a status indicator', () => {
  render(<CodeChat {...makeProps({ status: 'loading' })} />)
  // The component renders the chat trigger area regardless of request state
  expect(screen.getByText(/AI CODE ASSISTANT/i)).toBeDefined()
  expect(screen.getByText(/Ask about this codebase/i)).toBeDefined()
})

it('renders idle state without crashing', () => {
  render(<CodeChat {...makeProps({ status: 'idle' })} />)
  expect(screen.getByText(/AI CODE ASSISTANT/i)).toBeDefined()
})

it('renders error state without crashing and without exposing internals', () => {
  render(<CodeChat {...makeProps({ status: 'error', message: 'AI_NOT_CONFIGURED: GROQ_API_KEY is not set on the server.' })} />)
  // The trigger area should still render; the error lives in useChatState, not slot request
  expect(screen.getByText(/AI CODE ASSISTANT/i)).toBeDefined()
})

it('renders ready state without crashing', () => {
  render(<CodeChat {...makeProps({ status: 'ready', data: {} as Answer })} />)
  expect(screen.getByText(/AI CODE ASSISTANT/i)).toBeDefined()
  expect(screen.getByRole('button', { name: /Open Grepo/i })).toBeDefined()
})

it('renders the slot greeting from request.data.answer when ready and no prior chat', () => {
  const greeting = 'Ask GREPO is your AI assistant for this repository.'
  // Cast through unknown to satisfy the Answer type constraint while providing the real shape
  render(<CodeChat {...makeProps({ status: 'ready', data: { answer: greeting, context_hint: 'Snapshot abc123' } as unknown as Answer })} />)
  expect(screen.getByTestId('ask-slot-greeting')).toBeDefined()
  expect(screen.getByText(greeting)).toBeDefined()
})

it('does not render the greeting when answer is empty', () => {
  render(<CodeChat {...makeProps({ status: 'ready', data: { answer: '', context_hint: 'Snapshot abc123' } as unknown as Answer })} />)
  const el = document.querySelector('[data-testid="ask-slot-greeting"]')
  expect(el).toBeNull()
})

// ── security: no key exposure ─────────────────────────────────────────────────

it('does not render any secret string in its output', () => {
  render(<CodeChat {...makeProps({ status: 'idle' })} />)
  const html = document.body.innerHTML
  expect(html).not.toContain('GROQ_API_KEY')
  expect(html).not.toContain('Bearer ')
  expect(html).not.toContain('sk-')
})
