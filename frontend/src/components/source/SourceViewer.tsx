import { useEffect, useState } from 'react'
import { getSource } from '../../services/v1/api'
import type { SourceSlice } from '../../types/v1'
interface Props {projectId: string; snapshotId: string; fileId: string; path: string; language: string; lineStart?: number; lineEnd?: number}
export function SourceViewer({projectId,snapshotId,fileId,path,language,lineStart = 1,lineEnd}: Props) {
  const [start,setStart] = useState(lineStart); const [input,setInput] = useState(String(lineStart))
  const [slice,setSlice] = useState<SourceSlice | null>(null); const [error,setError] = useState(''); const [loading,setLoading] = useState(true)
  useEffect(() => {setStart(lineStart); setInput(String(lineStart))}, [lineStart,lineEnd])
  useEffect(() => {
    const control = new AbortController(); setLoading(true); setSlice(null); setError('')
    getSource(projectId,snapshotId,fileId,start,lineEnd,200,control.signal).then(s => {if (!control.signal.aborted) {setSlice(s); setLoading(false)}}).catch(e => {if (!control.signal.aborted) {setError(e.message); setLoading(false)}})
    return () => control.abort()
  }, [projectId,snapshotId,fileId,start,lineStart,lineEnd])
  return <section className="source-viewer" aria-label={`Source: ${path}`}><div className="source-toolbar"><span className="badge">{language}</span><form onSubmit={e => {e.preventDefault(); const n = Number(input); if (Number.isInteger(n) && n >= 1 && (!slice || n <= slice.total_lines)) {setStart(n); setError('')} else setError('Choose a line number within this file.')}}><label htmlFor="source-line">Line</label><input id="source-line" type="number" min="1" max={slice?.total_lines || undefined} value={input} onChange={e => setInput(e.target.value)}/><button className="btn small" type="submit">Go</button></form></div>
    {loading && <p className="pad" role="status">Loading source…</p>}{error && <p className="alert error" role="alert">{error}</p>}
    {slice && <><div className="source-code" tabIndex={0} aria-label={`Read-only source lines ${slice.line_start} to ${slice.line_end}`}><table><tbody>{slice.total_lines === 0 ? <tr><td>Empty file.</td></tr> : slice.content.split('\n').map((text,i) => <tr key={i}><th scope="row">{slice.line_start + i}</th><td><code>{text || ' '}</code></td></tr>)}</tbody></table></div><div className="source-paging"><button className="btn small" disabled={slice.line_start <= 1} onClick={() => {const n = Math.max(1,slice.line_start-200); setStart(n); setInput(String(n))}}>Previous</button><span>{slice.line_start}–{slice.line_end} / {slice.total_lines}</span><button className="btn small" disabled={slice.line_end >= slice.total_lines} onClick={() => {setStart(slice.line_end+1); setInput(String(slice.line_end+1))}}>Next</button></div>{slice.truncated && <p className="muted pad">Bounded preview. Use Next or jump to a line to continue.</p>}</>}
  </section>
}
