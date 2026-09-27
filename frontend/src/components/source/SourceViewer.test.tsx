import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { SourceViewer } from './SourceViewer'
import { getSource } from '../../services/v1/api'
vi.mock('../../services/v1/api', () => ({getSource: vi.fn()}))
afterEach(() => {cleanup(); vi.clearAllMocks()})
it('releases the selected range when paging and jumping after opening a finding', async () => {
  vi.mocked(getSource).mockImplementation(async (_p,_s,file,start=1,end) => ({schema_version:'1.0', file_id:file, snapshot_id:'s', path:'a.py', content_hash:'h', line_start:start, line_end:end ?? Math.min(start+199,500), total_lines:500, content:'example', truncated:true}))
  render(<SourceViewer projectId="p" snapshotId="s" fileId="f" path="a.py" language="python" lineStart={3} lineEnd={5}/> )
  await screen.findByText('3–5 / 500')
  fireEvent.click(screen.getByRole('button',{name:'Next'}))
  await waitFor(() => expect(getSource).toHaveBeenLastCalledWith('p','s','f',6,undefined,200,expect.any(AbortSignal)))
  await screen.findByText('6–205 / 500')
  fireEvent.change(screen.getByLabelText('Line'), {target:{value:'350'}})
  fireEvent.click(screen.getByRole('button',{name:'Go'}))
  await waitFor(() => expect(getSource).toHaveBeenLastCalledWith('p','s','f',350,undefined,200,expect.any(AbortSignal)))
})
