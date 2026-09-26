import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ReusableFunctionPanel } from './ReusableFunctionPanel'
import type { SlotProps } from '../../contexts/SlotRegistry'
import type { ReusableFunctionResult } from '../../types/codebase'

afterEach(cleanup)

const openSource = vi.fn()

function makeProps(request: SlotProps<ReusableFunctionResult>['request']): SlotProps<ReusableFunctionResult> {
  return {
    projectId: 'proj', snapshotId: 'snap',
    snapshot: { schema_version: '1.0', id: 'snap', project_id: 'proj', source: { kind: 'zip' }, manifest_hash: 'h', policy_version: '1.0', created_at: '2099-01-01' },
    selectedEntity: null, files: [{ schema_version: '1.0', id: 'file-a-id', snapshot_id: 'snap', path: 'src/a.py', name: 'a.py', size: 10, content_hash: 'x', is_text: true, language: 'python', language_basis: 'extension', excluded: false }],
    entities: [], graph: null, capabilities: null,
    viewState: { focusedView: 'overview', mapCamera: { x: 0, y: 0, scale: 1 } },
    selectEntity: vi.fn(), openSource, navigate: vi.fn(),
    availability: 'connected', request,
  }
}

it('shows empty message when no reusable functions', () => {
  render(<ReusableFunctionPanel {...makeProps({ status: 'ready', data: { snapshot_id: 'snap', groups: [], total_reusable: 0 } })} />)
  expect(screen.getByText('No reusable functions detected across multiple files.')).toBeDefined()
})

it('renders function name and caller count when groups present', () => {
  const data: ReusableFunctionResult = {
    snapshot_id: 'snap',
    total_reusable: 1,
    groups: [{ function_name: 'helper', defined_in: 'src/a.py', defined_line_start: 3, defined_line_end: 5, called_from: ['src/b.py'] }],
  }
  render(<ReusableFunctionPanel {...makeProps({ status: 'ready', data })} />)
  expect(screen.getByText('helper')).toBeDefined()
  expect(screen.getByText('src/b.py')).toBeDefined()
})

it('calls openSource with correct file_id when defined_in button is clicked', () => {
  openSource.mockClear()
  const data: ReusableFunctionResult = {
    snapshot_id: 'snap',
    total_reusable: 1,
    groups: [{ function_name: 'helper', defined_in: 'src/a.py', defined_line_start: 3, defined_line_end: 5, called_from: ['src/b.py'] }],
  }
  render(<ReusableFunctionPanel {...makeProps({ status: 'ready', data })} />)
  // The defined_in button label is "src/a.py:3"
  fireEvent.click(screen.getByRole('button', { name: 'src/a.py:3' }))
  expect(openSource).toHaveBeenCalledWith('file-a-id', { start: 3, end: 3 })
})

it('shows loading state', () => {
  render(<ReusableFunctionPanel {...makeProps({ status: 'loading' })} />)
  expect(screen.getByRole('status')).toBeDefined()
})
