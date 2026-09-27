import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SlotMount } from './SlotMount'
import { registerSlot, type SlotContext, type SlotProps } from '../../contexts/SlotRegistry'
import type { WorkspaceContextValue } from '../../contexts/WorkspaceContext'

vi.mock('../../contexts/WorkspaceContext', () => ({useWorkspace: () => workspace,selectionFor: vi.fn()}))
function makeWorkspace(): Pick<WorkspaceContextValue,'projectId'|'snapshot'|'selectedEntity'|'files'|'entities'|'graph'|'capabilities'|'viewState'|'selectEntity'> {
  return {projectId:'project',snapshot:{schema_version:'1.0',id:'snapshot',project_id:'project',source:{kind:'zip'},manifest_hash:'hash',policy_version:'1',created_at:'2026-01-01'},selectedEntity:null,files:[],entities:[],graph:null,capabilities:null,viewState:{focusedView:'map',mapCamera:{x:0,y:0,scale:1}},selectEntity:vi.fn()}
}
let workspace = makeWorkspace()
let unregister: (() => void) | undefined
const element = () => <MemoryRouter><SlotMount id="summaries.context-panel"/></MemoryRouter>
function Panel(props: SlotProps) {return <p>{props.request.status}:{props.selectedEntity?.path}:{props.selectedEntity?.lineRange?.start}</p>}
beforeEach(() => {workspace=makeWorkspace(); vi.stubEnv('VITE_HOSTED','true')})
afterEach(() => {cleanup(); unregister?.(); vi.unstubAllEnvs()})
it('keeps snapshot-wide requests stable through map, selection, and camera updates while refreshing displayed context', async () => {
  const load = vi.fn(async () => 'result')
  unregister = registerSlot('summaries.context-panel',{Component:Panel,load,loadKey:() => 'snapshot'})
  const view = render(element())
  await screen.findByText('ready::')
  workspace={...workspace,graph:{schema_version:'1.1',snapshot_id:'snapshot',focus_path:'.',cursor:0,next_cursor:null,child_total:0,evidence:[],fixture_only:false,entities:[],relations:[],coverage:{inventoried_files:0,parsed_files:0,unresolved_references:0,excluded_paths:[],limitations:[],truncated:false,total_entities:0,returned_entities:0}},selectedEntity:{entityId:'f',kind:'file',path:'app.py',lineRange:{start:6,end:8}},viewState:{...workspace.viewState,mapCamera:{x:50,y:25,scale:1.5}}}
  view.rerender(element())
  await screen.findByText('ready:app.py:6')
  expect(load).toHaveBeenCalledTimes(1)
})
it('reloads a path-sensitive feature only on path change and aborts its previous request', async () => {
  const load = vi.fn((context: SlotContext, signal: AbortSignal) => {void context; void signal; return new Promise(() => {})})
  unregister = registerSlot('summaries.context-panel',{Component:Panel,load,loadKey:context => context.selectedEntity?.path || '.'})
  const view = render(element())
  await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
  workspace={...workspace,selectedEntity:{entityId:'root',kind:'folder',path:'.'}}
  view.rerender(element())
  expect(load).toHaveBeenCalledTimes(1)
  workspace={...workspace,selectedEntity:{entityId:'f',kind:'file',path:'app.py',lineRange:{start:1,end:5}}}
  view.rerender(element())
  await waitFor(() => expect(load).toHaveBeenCalledTimes(2))
  expect(load.mock.calls[0][1].aborted).toBe(true)
  expect(load.mock.calls[1][0].selectedEntity?.path).toBe('app.py')
  workspace={...workspace,selectedEntity:{...workspace.selectedEntity!,lineRange:{start:12,end:20}}}
  view.rerender(element())
  expect(load).toHaveBeenCalledTimes(2)
  expect(load.mock.calls[1][1].aborted).toBe(false)
})
it.each([{hosted:'true',keyed:false},{hosted:'false',keyed:true}])('preserves context-driven reloads for hosted=$hosted keyed=$keyed', async ({hosted,keyed}) => {
  vi.stubEnv('VITE_HOSTED',hosted)
  const load = vi.fn(async () => 'result')
  unregister=registerSlot('summaries.context-panel',{Component:Panel,load,...(keyed ? {loadKey:() => 'snapshot'} : {})})
  const view=render(element())
  await screen.findByText('ready::')
  workspace={...workspace,selectedEntity:{entityId:'f',kind:'file',path:'app.py'}}
  view.rerender(element())
  await waitFor(() => expect(load).toHaveBeenCalledTimes(2))
})
it('reloads a snapshot-wide feature when workspace identity changes', async () => {
  const load=vi.fn(async () => 'result')
  unregister=registerSlot('summaries.context-panel',{Component:Panel,load,loadKey:() => 'snapshot'})
  const view=render(element())
  await screen.findByText('ready::')
  workspace={...workspace,snapshot:{...workspace.snapshot!,id:'next'}}
  view.rerender(element())
  await waitFor(() => expect(load).toHaveBeenCalledTimes(2))
})
