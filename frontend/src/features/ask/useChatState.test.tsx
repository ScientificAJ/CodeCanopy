import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useChatState } from './useChatState'
import { request } from '../../services/v1/api'
vi.mock('../../services/v1/api', () => ({request: vi.fn(), snapshotPath: (p: string, s: string) => `/projects/${p}/snapshots/${s}`}))
const options = {projectId:'project', snapshotId:'snapshot', scope:'repository'}
afterEach(() => {cleanup(); localStorage.clear(); vi.clearAllMocks()})

it('keeps long conversations usable by sending only the last ten messages', async () => {
  const messages = Array.from({length:14}, (_, i) => ({role:i % 2 ? 'assistant' : 'user', content:`message ${i}`}))
  localStorage.setItem('codecanopy_chat_project_snapshot', JSON.stringify({messages, expiresAt:Date.now()+60000}))
  vi.mocked(request).mockResolvedValue({answer:'Answer [S1]', context_hint:'Searched 1 file', sources:[{id:'S1',file_id:'file',path:'main.py',line_start:50,line_end:60}]})
  const {result} = renderHook(() => useChatState(options))
  act(() => result.current.setInput('Continue'))
  await act(async () => {await result.current.submit()})
  const body = JSON.parse(vi.mocked(request).mock.calls[0][1]!.body as string)
  expect(body.history).toHaveLength(10)
  expect(body.history[0].content).toBe('message 4')
  expect(result.current.messages.at(-1)?.sources?.[0].line_start).toBe(50)
})

it('does not resurrect cleared messages when an in-flight request resolves', async () => {
  let finish: (value: unknown) => void = () => {}
  vi.mocked(request).mockReturnValue(new Promise(resolve => {finish=resolve}))
  const {result} = renderHook(() => useChatState(options))
  act(() => result.current.setInput('Explain'))
  let pending: Promise<void>
  act(() => {pending=result.current.submit()})
  act(() => result.current.clear())
  await act(async () => {finish({answer:'Stale answer',context_hint:''}); await pending})
  expect(result.current.messages).toEqual([])
  expect(result.current.loading).toBe(false)
  expect(localStorage.getItem('codecanopy_chat_project_snapshot')).toBeNull()
})

it('never stores the previous snapshot conversation under a new snapshot', async () => {
  localStorage.setItem('codecanopy_chat_project_snapshot', JSON.stringify({messages:[{role:'user',content:'old source'}],expiresAt:Date.now()+60000}))
  const {result, rerender} = renderHook(props => useChatState(props), {initialProps:options})
  rerender({...options,snapshotId:'new-snapshot'})
  await waitFor(() => expect(result.current.messages).toEqual([]))
  expect(localStorage.getItem('codecanopy_chat_project_new-snapshot')).toBeNull()
})
