import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ProposalsPanel } from './ProposalsPanel'
import type { SlotProps } from '../../contexts/SlotRegistry'
import type { ChangePack } from '../../types/v1/prd.generated'

afterEach(cleanup)

const openSource = vi.fn()

function makeProps(request: SlotProps<ChangePack>['request']): SlotProps<ChangePack> {
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

const ready = (data: unknown) => ({ status: 'ready', data }) as SlotProps<ChangePack>['request']

const payload = {
  schema_version: '1.1',
  snapshot_id: 'snap',
  proposals: [
    {
      id: 'proposal_1',
      kind: 'change_impact',
      title: 'Review before changing pkg/utils.py',
      detail: 'pkg/utils.py is transitively imported by 2 other file(s).',
      subject_path: 'pkg/utils.py',
      affected_paths: ['pkg/main.py', 'pkg/app.py'],
      affected_count: 2,
      impact_truncated: false,
      evidence: [
        {
          file_id: 'f1',
          path: 'pkg/main.py',
          line_start: 1,
          line_end: 1,
          content_sha256: 'abc',
        },
      ],
      limitations: [],
    },
  ],
  limitations: ['Change impact requires a specific file or folder.'],
}

it('renders a proposal with its affected files and count', () => {
  render(<ProposalsPanel {...makeProps(ready(payload))} />)
  expect(screen.getByText('pkg/utils.py')).toBeTruthy()
  expect(screen.getByText('2 affected')).toBeTruthy()
  expect(screen.getByText('pkg/main.py')).toBeTruthy()
  expect(screen.getByText('pkg/app.py')).toBeTruthy()
})

it('opens the cited source line when the citation is clicked', () => {
  openSource.mockClear()
  render(<ProposalsPanel {...makeProps(ready(payload))} />)
  screen.getByTitle('pkg/main.py line 1').click()
  expect(openSource).toHaveBeenCalledWith('f1', { start: 1, end: 1 })
})

it('marks a truncated impact count rather than presenting it as exact', () => {
  const truncated = {
    ...payload,
    proposals: [{ ...payload.proposals[0], impact_truncated: true, limitations: ['The impact walk was capped.'] }],
  }
  render(<ProposalsPanel {...makeProps(ready(truncated))} />)
  expect(screen.getByText('2 affected+')).toBeTruthy()
  expect(screen.getByText('The impact walk was capped.')).toBeTruthy()
})

it('says so plainly when no proposal can be derived', () => {
  render(
    <ProposalsPanel
      {...makeProps(ready({ ...payload, proposals: [], limitations: ['No verified import edge exists in this snapshot.'] }))}
    />,
  )
  expect(screen.getByText(/No change proposal can be derived/)).toBeTruthy()
})

it('surfaces limitations rather than hiding them', () => {
  render(<ProposalsPanel {...makeProps(ready(payload))} />)
  expect(screen.getByText('Limitations (1)')).toBeTruthy()
})
