import { afterEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from './WorkspaceContext'
import * as api from '../services/v1/api'
import type { V1Project } from '../types/v1'
vi.mock('../services/v1/api', () => ({getProject:vi.fn(),getSnapshot:vi.fn(),getAllFiles:vi.fn(),getEntities:vi.fn(),getCapabilities:vi.fn(),getPreferences:vi.fn(),getRun:vi.fn(),savePreferences:vi.fn()}))
afterEach(cleanup)
it('ignores a late response from the previous workspace and aborts its requests', async () => {
  const projects = new Map<string,(value: V1Project) => void>()
  const signals: AbortSignal[] = []
  vi.mocked(api.getProject).mockImplementation((id,signal) => {signals.push(signal!); return new Promise(resolve => projects.set(id,resolve))})
  vi.mocked(api.getSnapshot).mockImplementation(async (p,s) => ({schema_version:'1.0',id:s,project_id:p,source:{kind:'zip'},manifest_hash:'hash',policy_version:'1.0',created_at:'2026-01-01'}))
  vi.mocked(api.getAllFiles).mockResolvedValue([]); vi.mocked(api.getEntities).mockResolvedValue([])
  vi.mocked(api.getCapabilities).mockResolvedValue({schema_version:'1.0',snapshot_id:'s',files:[],parsed_count:0,text_only_count:0,binary_count:0,excluded_count:0,limitations:[]})
  vi.mocked(api.getPreferences).mockResolvedValue({schema_version:'1.1',labels:{},groups:[],focus:'.',theme:'light',order:'folders-first'})
  function Consumer() {const ws = useWorkspace(); return <><button onClick={() => void ws.loadWorkspace('old','old-s')}>Old</button><button onClick={() => void ws.loadWorkspace('new','new-s')}>New</button><p data-testid="identity">{ws.projectName}:{ws.snapshot?.id}</p></>}
  render(<WorkspaceProvider><Consumer/></WorkspaceProvider>)
  fireEvent.click(screen.getByText('Old')); fireEvent.click(screen.getByText('New'))
  expect(signals[0].aborted).toBe(true)
  await act(async () => projects.get('new')!({schema_version:'1.0',id:'new',name:'Current repository',created_at:'2026-01-01',snapshot_ids:['new-s']}))
  await waitFor(() => expect(screen.getByTestId('identity').textContent).toBe('Current repository:new-s'))
  await act(async () => projects.get('old')!({schema_version:'1.0',id:'old',name:'Stale repository',created_at:'2026-01-01',snapshot_ids:['old-s']}))
  expect(screen.getByTestId('identity').textContent).toBe('Current repository:new-s')
})
