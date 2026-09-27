import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from './WorkspaceContext'
import * as api from '../services/v1/api'
import type { AnalysisRun, FileRecord } from '../types/v1'

vi.mock('../services/v1/api', () => ({getProject:vi.fn(),getSnapshot:vi.fn(),getAllFiles:vi.fn(),getEntities:vi.fn(),getCapabilities:vi.fn(),getPreferences:vi.fn(),getRun:vi.fn(),savePreferences:vi.fn(),getWorkspaceBootstrap:vi.fn(),getInventory:vi.fn()}))
const bootstrap: api.WorkspaceBootstrap = {
  project: {schema_version:'1.0',id:'p',name:'Repository',created_at:'2026-01-01',snapshot_ids:['s']},
  snapshot: {schema_version:'1.0',id:'s',project_id:'p',source:{kind:'zip'},manifest_hash:'hash',policy_version:'1.0',created_at:'2026-01-01'},
  files: {schema_version:'1.0',snapshot_id:'s',files:[],total:0,truncated:false}, entities: [],
  capabilities: {schema_version:'1.0',snapshot_id:'s',files:[],parsed_count:0,text_only_count:0,binary_count:0,excluded_count:0,limitations:[]},
  preferences: {schema_version:'1.1',labels:{},groups:[],focus:'.',theme:'light',order:'folders-first'},
}
const run: AnalysisRun = {schema_version:'1.1',id:'run',project_id:'p',snapshot_id:'s',status:'completed',event_sequence:1,diagnostics:[],cancel_requested:false,started_at:'2026-01-01'}
const separate = [api.getProject,api.getSnapshot,api.getAllFiles,api.getEntities,api.getCapabilities,api.getPreferences]
function Consumer() {
  const ws = useWorkspace()
  return <>
    <button onClick={() => void ws.loadWorkspace('p','s')}>Open</button>
    <button onClick={() => void ws.loadWorkspace('new','new-s')}>Switch</button>
    <button onClick={() => ws.selectEntity({entityId:'file',kind:'file',path:'app.py'})}>Select</button>
    <p data-testid="state">{ws.loading ? 'loading' : ws.error || `${ws.projectName}:${ws.snapshot?.id}:${ws.files.length}`}</p>
    <p data-testid="selection">{ws.selectedEntity?.path}</p><p data-testid="run">{ws.run?.id}</p>
  </>
}
function open() {render(<WorkspaceProvider><Consumer/></WorkspaceProvider>); fireEvent.click(screen.getByText('Open'))}
beforeEach(() => {
  vi.resetAllMocks(); vi.stubEnv('VITE_HOSTED','true')
  vi.mocked(api.getWorkspaceBootstrap).mockResolvedValue(bootstrap)
  vi.mocked(api.getProject).mockResolvedValue(bootstrap.project)
  vi.mocked(api.getSnapshot).mockResolvedValue(bootstrap.snapshot)
  vi.mocked(api.getAllFiles).mockResolvedValue([]); vi.mocked(api.getEntities).mockResolvedValue([])
  vi.mocked(api.getCapabilities).mockResolvedValue(bootstrap.capabilities)
  vi.mocked(api.getPreferences).mockResolvedValue(bootstrap.preferences)
})
afterEach(() => {cleanup(); vi.unstubAllEnvs()})
it('opens hosted workspace with one bootstrap request without waiting for optional diagnostics', async () => {
  let finishRun!: (value: AnalysisRun) => void
  vi.mocked(api.getWorkspaceBootstrap).mockResolvedValue({...bootstrap,snapshot:{...bootstrap.snapshot,analysis_run_id:'run'}})
  vi.mocked(api.getRun).mockImplementation(() => new Promise(resolve => {finishRun=resolve}))
  open()
  await waitFor(() => expect(screen.getByTestId('state').textContent).toBe('Repository:s:0'))
  expect(api.getWorkspaceBootstrap).toHaveBeenCalledTimes(1)
  separate.forEach(request => expect(request).not.toHaveBeenCalled())
  expect(api.getRun).toHaveBeenCalledWith('run',expect.any(AbortSignal))
  fireEvent.click(screen.getByText('Select'))
  await act(async () => finishRun(run))
  expect(screen.getByTestId('selection').textContent).toBe('app.py')
  expect(screen.getByTestId('run').textContent).toBe('run')
})
it('continues the bootstrap inventory cursor so large inventories are complete', async () => {
  const file: FileRecord = {schema_version:'1.0',id:'f',snapshot_id:'s',path:'app.py',name:'app.py',size:20,content_hash:'hash',is_text:true,language:'python',language_basis:'extension',excluded:false}
  vi.mocked(api.getWorkspaceBootstrap).mockResolvedValue({...bootstrap,files:{...bootstrap.files,total:1,cursor:'next',truncated:true}})
  vi.mocked(api.getInventory).mockResolvedValue({...bootstrap.files,files:[file],total:1})
  open()
  await waitFor(() => expect(screen.getByTestId('state').textContent).toBe('Repository:s:1'))
  expect(api.getInventory).toHaveBeenCalledWith('p','s','next',2000,expect.any(AbortSignal))
  expect(api.getAllFiles).not.toHaveBeenCalled()
})
it('falls back to separate endpoints only when the combined response is too large', async () => {
  vi.mocked(api.getWorkspaceBootstrap).mockRejectedValue(Object.assign(new Error('Too large'),{code:'BOOTSTRAP_TOO_LARGE'}))
  open()
  await waitFor(() => expect(screen.getByTestId('state').textContent).toBe('Repository:s:0'))
  separate.forEach(request => expect(request).toHaveBeenCalledTimes(1))
})
it.each(['ACCESS_DENIED','INTERNAL_ERROR'])('does not retry bootstrap %s failures through other endpoints', async code => {
  vi.mocked(api.getWorkspaceBootstrap).mockRejectedValue(Object.assign(new Error('Cannot open this repository'),{code}))
  open()
  await screen.findByText('Cannot open this repository')
  separate.forEach(request => expect(request).not.toHaveBeenCalled())
})
it('ignores and aborts diagnostics from a previous hosted workspace', async () => {
  let finishRun!: (value: AnalysisRun) => void
  let signal!: AbortSignal
  vi.mocked(api.getWorkspaceBootstrap).mockResolvedValueOnce({...bootstrap,snapshot:{...bootstrap.snapshot,analysis_run_id:'run'}})
    .mockResolvedValueOnce({...bootstrap,project:{...bootstrap.project,id:'new',name:'New repository'},snapshot:{...bootstrap.snapshot,id:'new-s',project_id:'new'}})
  vi.mocked(api.getRun).mockImplementation((_id, abort) => {signal=abort!; return new Promise(resolve => {finishRun=resolve})})
  open()
  await waitFor(() => expect(screen.getByTestId('state').textContent).toBe('Repository:s:0'))
  fireEvent.click(screen.getByText('Switch'))
  await waitFor(() => expect(screen.getByTestId('state').textContent).toBe('New repository:new-s:0'))
  expect(signal.aborted).toBe(true)
  await act(async () => finishRun(run))
  expect(screen.getByTestId('state').textContent).toBe('New repository:new-s:0')
  expect(screen.getByTestId('run').textContent).toBe('')
})
it('retains the separate endpoints and diagnostics completion gate for local workspaces', async () => {
  vi.stubEnv('VITE_HOSTED','false')
  let finishRun!: (value: AnalysisRun) => void
  vi.mocked(api.getSnapshot).mockResolvedValue({...bootstrap.snapshot,analysis_run_id:'run'})
  vi.mocked(api.getRun).mockImplementation(() => new Promise(resolve => {finishRun=resolve}))
  open()
  await waitFor(() => expect(api.getRun).toHaveBeenCalledTimes(1))
  expect(screen.getByTestId('state').textContent).toBe('loading')
  expect(api.getWorkspaceBootstrap).not.toHaveBeenCalled()
  separate.forEach(request => expect(request).toHaveBeenCalledTimes(1))
  await act(async () => finishRun(run))
  expect(screen.getByTestId('state').textContent).toBe('Repository:s:0')
})
