import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SlotMount } from '../components/slots/SlotMount'
import { registerSlot, type SlotProps } from './SlotRegistry'
const selectEntity = vi.fn()
vi.mock('./WorkspaceContext', () => ({useWorkspace: () => context,selectionFor: (e: {id: string; file_id: string; path: string}) => ({entityId: e.id,fileId: e.file_id,path: e.path,kind: 'file'})}))
const context = {projectId:'project',snapshot:{id:'snapshot'},selectedEntity:null,files:[],entities:[{id:'canonical',file_id:'canonical',path:'src/app.py'}],graph:null,capabilities:null,viewState:{focusedView:'map'},selectEntity}
afterEach(cleanup)
it('mounts an isolated future feature and adapter with canonical source navigation', async () => {
  const load = vi.fn(async () => ({message:'Isolated extension test'}))
  function Example(props: SlotProps) {return <div>{props.request.status === 'ready' ? (props.request.data as {message:string}).message : props.request.status}<button onClick={() => props.openSource('canonical',{start:3,end:5})}>Open evidence</button></div>}
  const unregister = registerSlot('dependencies.workspace',{Component:Example,load})
  render(<MemoryRouter><SlotMount id="dependencies.workspace"/></MemoryRouter>)
  await screen.findByText('Isolated extension test')
  screen.getByRole('button',{name:'Open evidence'}).click()
  expect(selectEntity).toHaveBeenCalledWith({entityId:'canonical',fileId:'canonical',path:'src/app.py',kind:'file',lineRange:{start:3,end:5}})
  expect(load.mock.calls.length).toBeGreaterThan(0)
  unregister()
  await waitFor(() => expect(screen.getByText('Dependencies & change impact')).toBeDefined())
})
it('does not call an unavailable feature adapter', () => {
  const load = vi.fn(); const unregister = registerSlot('ask.workspace',{Component:() => <p>Should not render</p>,availability:'unavailable',load})
  render(<MemoryRouter><SlotMount id="ask.workspace"/></MemoryRouter>)
  expect(screen.getByText('Ask CodeCanopy')).toBeDefined(); expect(load).not.toHaveBeenCalled(); unregister()
})
