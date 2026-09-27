import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { SlotProps } from '../../contexts/SlotRegistry'
import { DraftWorkspace, exportDraft } from './DraftWorkspace'
import { request } from '../../services/v1/api'
vi.mock('../../services/v1/api', () => ({request: vi.fn(), snapshotPath: (p: string, s: string) => `/projects/${p}/snapshots/${s}`}))
const response = {answer: '## Overview\nThe client retries requests. [S1]', context_hint: 'test', sources: [{id:'S1',file_id:'file1',path:'client.py',line_start:2,line_end:8}], limitations:['Selected excerpts only.']}
function props(): SlotProps {
  return {projectId:'p',snapshotId:'s',snapshot:{schema_version:'1.0',id:'s',project_id:'p',source:{kind:'github',resolved_commit:'abcdef'},manifest_hash:'h',policy_version:'1',created_at:'2026-01-01'}, selectedEntity:null,files:[],entities:[],graph:null,capabilities:null,viewState:{focusedView:'overview',mapCamera:{x:0,y:0,scale:1}},selectEntity:vi.fn(),openSource:vi.fn(),navigate:vi.fn(),availability:'connected',request:{status:'idle'}}
}
afterEach(() => {cleanup(); localStorage.clear(); vi.resetAllMocks()})
it('generates documentation on demand, opens evidence, and preserves edits on remount', async () => {
  vi.mocked(request).mockResolvedValue(response)
  const context = props()
  const {unmount} = render(<DraftWorkspace {...context} kind="documentation"/>);
  expect(request).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'Generate documentation'}))
  await screen.findByText('The client retries requests. [S1]')
  expect(JSON.parse(vi.mocked(request).mock.calls[0][1]!.body as string)).toMatchObject({scope:'repository'})
  fireEvent.click(screen.getByRole('button',{name:'[S1] client.py:2–8'}))
  expect(context.openSource).toHaveBeenCalledWith('file1',{start:2,end:8})
  fireEvent.click(screen.getByRole('button',{name:'Edit draft'}))
  fireEvent.change(screen.getByLabelText('Draft content'),{target:{value:'My reviewed guide [S1]'}})
  unmount()
  render(<DraftWorkspace {...context} kind="documentation"/>);
  expect(screen.getByText('My reviewed guide [S1]')).toBeDefined()
})
it('proposals require a goal and request an unimplemented change plan', async () => {
  vi.mocked(request).mockResolvedValue(response)
  render(<DraftWorkspace {...props()} kind="proposal"/>);
  expect((screen.getByRole('button',{name:'Generate proposal'}) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.change(screen.getByLabelText('What would you like to change?'),{target:{value:'Improve retries'}})
  fireEvent.click(screen.getByRole('button',{name:'Generate proposal'}))
  await screen.findByText('The client retries requests. [S1]')
  const body = JSON.parse(vi.mocked(request).mock.calls[0][1]!.body as string)
  expect(body.question).toContain('Improve retries')
  expect(body.question).toContain('Do not claim to have modified files or run tests')
  expect(screen.getByRole('heading',{name:'Improve retries'})).toBeDefined()
})
it('cancelled requests cannot publish late results', async () => {
  let resolve!: (value: typeof response) => void
  vi.mocked(request).mockImplementation(() => new Promise(r => {resolve = r}))
  render(<DraftWorkspace {...props()} kind="documentation"/>);
  fireEvent.click(screen.getByRole('button',{name:'Generate documentation'}))
  const signal = vi.mocked(request).mock.calls[0][1]!.signal
  fireEvent.click(screen.getByRole('button',{name:'Cancel generation'}))
  expect(signal?.aborted).toBe(true)
  resolve(response)
  await waitFor(() => expect(screen.queryByRole('button',{name:'Export Markdown'})).toBeNull())
  expect(localStorage.length).toBe(0)
})
it('shows provider failures and allows retry', async () => {
  vi.mocked(request).mockRejectedValue(new Error('Provider rate limit reached'))
  render(<DraftWorkspace {...props()} kind="documentation"/>);
  fireEvent.click(screen.getByRole('button',{name:'Generate documentation'}))
  expect((await screen.findByRole('alert')).textContent).toContain('Provider rate limit reached')
  expect((screen.getByRole('button',{name:'Generate documentation'}) as HTMLButtonElement).disabled).toBe(false)
})
it('exports full edited content with revision, evidence, and limitations', () => {
  const md = exportDraft({title:'Plan',content:'Proposed change [S1]',sources:response.sources,limitations:response.limitations,scope:'Entire repository'},'abcdef')
  expect(md).toContain('Proposed change [S1]')
  expect(md).toContain('client.py:2–8')
  expect(md).toContain('Revision: abcdef')
  expect(md).toContain('Selected excerpts only.')
})
it('keeps proposals, documentation, and snapshots separate', () => {
  localStorage.setItem('grepo-draft:p:s:proposal',JSON.stringify({title:'Old plan',content:'Old proposal',sources:[],limitations:[],scope:'Entire repository'}))
  const {unmount} = render(<DraftWorkspace {...props()} kind="documentation"/>);
  expect(screen.queryByText('Old proposal')).toBeNull()
  unmount()
  render(<DraftWorkspace {...props()} snapshotId="other" kind="proposal"/>);
  expect(screen.queryByText('Old proposal')).toBeNull()
})
