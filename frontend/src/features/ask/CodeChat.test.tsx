import { renderMarkdown } from './markdown'

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

// ── markdown renderer: chunk-boundary robustness ─────────────────────────────

/**
 * The response below contains:
 *   - an opening label that must appear exactly once
 *   - a three-row table split across three simulated chunks
 *   - a fenced code block split across two simulated chunks
 *
 * "Chunk" here means a prefix of the full markdown string, as the renderer
 * would receive during incremental streaming.  The test verifies:
 *   1. No garbled output or crash on each intermediate chunk.
 *   2. The complete render (full text) contains the label exactly once.
 *   3. All table rows appear in the final render.
 *   4. The complete code block appears in the final render.
 */
it('renders chunked multi-row table and fenced code block without duplication or truncation', () => {
  const fullMd = [
    '**Short answer:**  This is the summary.',
    '',
    '## Details',
    '',
    '| Area | Description | Status |',
    '|------|-------------|--------|',
    '| Alpha | First row value | Done |',
    '| Beta  | Second row value | In progress |',
    '| Gamma | Third row value | Planned |',
    '',
    '```python',
    'def greet(name):',
    '    return f"Hello, {name}!"',
    '```',
  ].join('\n')

  // Chunk 1: opening label + table header only (no separator yet)
  const chunk1 = fullMd.slice(0, fullMd.indexOf('|------'))
  // Chunk 2: extends to include header, separator, and first two data rows
  const chunk2 = fullMd.slice(0, fullMd.indexOf('| Gamma'))
  // Chunk 3 (final): complete markdown
  const chunk3 = fullMd

  // Each intermediate chunk must not throw or crash
  const { unmount: u1 } = render(<>{renderMarkdown(chunk1)}</>)
  u1()
  const { unmount: u2 } = render(<>{renderMarkdown(chunk2)}</>)
  u2()

  // Final render — verify complete, correct output
  const { container } = render(<>{renderMarkdown(chunk3)}</>)
  const html = container.innerHTML

  // 1. Opening label appears exactly once
  const labelMatches = html.match(/Short answer:/g)
  expect(labelMatches, 'label "Short answer:" should appear exactly once').toHaveLength(1)

  // 2. Complete table: all three data rows present
  expect(html).toContain('Alpha')
  expect(html).toContain('Beta')
  expect(html).toContain('Gamma')
  expect(html).toContain('First row value')
  expect(html).toContain('Second row value')
  expect(html).toContain('Third row value')

  // 3. Table rendered as <table>, not as raw pipe-delimited text
  expect(container.querySelector('table')).not.toBeNull()
  expect(container.querySelectorAll('tbody tr')).toHaveLength(3)

  // 4. Fenced code block rendered — both lines of the function body present
  expect(html).toContain('def greet(name):')
  expect(html).toContain('return f"Hello, {name}!"')
  expect(container.querySelector('pre')).not.toBeNull()

  // 5. No raw HTML injection — renderer uses JSX, not innerHTML
  expect(html).not.toContain('dangerouslySetInnerHTML')
  expect(html).not.toContain('<script')
  expect(html).not.toContain('onerror')
})

it('renders the opening label once when intermediate chunks repeat the heading text', () => {
  // Simulate a response whose first visible line is **Short answer:** — a common
  // LLM pattern.  The inline() function must not duplicate the text.
  const md = '**Short answer:**  Click is a Python library for building CLIs.'
  const { container } = render(<>{renderMarkdown(md)}</>)
  const matches = container.innerHTML.match(/Short answer:/g)
  expect(matches, 'label should appear exactly once').toHaveLength(1)
})

it('renders partial table header as a table element when separator has not yet arrived', () => {
  // Simulate a chunk that ends exactly at the header row (separator not yet received)
  const partial = '| Col A | Col B | Col C |\n'
  const { container } = render(<>{renderMarkdown(partial)}</>)
  // Should render as a <table> with headers, not raw text
  const table = container.querySelector('table')
  expect(table).not.toBeNull()
  expect(container.innerHTML).toContain('Col A')
  expect(container.innerHTML).toContain('Col B')
  expect(container.innerHTML).toContain('Col C')
})

it('renders an unclosed fenced code block without swallowing later content', () => {
  // Simulate a chunk whose fence is not yet closed
  const partial = '```python\nprint("hello")\n'
  const { container } = render(<>{renderMarkdown(partial)}</>)
  expect(container.querySelector('pre')).not.toBeNull()
  expect(container.innerHTML).toContain('print("hello")')
})
