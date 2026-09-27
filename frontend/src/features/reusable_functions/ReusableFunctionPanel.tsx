import { useState } from 'react'
import type { SlotProps } from '../../contexts/SlotRegistry'
import type { ReusableFunctionResult } from '../../types/codebase'

export function ReusableFunctionPanel({request, openSource}: SlotProps<ReusableFunctionResult>) {
  const [limit, setLimit] = useState(50)
  const [callLimits, setCallLimits] = useState<Record<string, number>>({})
  if (request.status === 'loading') return <p className="pad" role="status">Scanning for reuse candidates…</p>
  if (request.status === 'error') return <p className="alert error" role="alert">{request.message}</p>
  if (request.status !== 'ready') return null
  const result = request.data
  return <section className="finding-view" aria-label="Reuse candidates">
    <header className="finding-heading"><div><h2>Possible cross-file reuse</h2>
      <p>Call-name matches are candidates for review, not confirmed dependencies.</p></div>
      <span className="badge">{result.total_reusable} candidates</span></header>
    <p>{result.analyzed_files} files assessed · {result.ambiguous_names} ambiguous names omitted</p>
    {!result.total_reusable && <p>{result.analyzed_files ? 'No cross-file reuse candidates found in the assessed files.' : 'No files have call-site evidence. Import a supported repository to run this analysis.'}</p>}
    <div className="finding-list">{result.groups.slice(0, limit).map(group => <article className="finding-row" key={`${group.defined_file_id}:${group.defined_line_start}`}>
      <div className="finding-row__title"><strong>{group.function_name}</strong><span className="badge">{group.called_from.length} caller files</span></div>
      <button className="finding-source" onClick={() => openSource(group.defined_file_id, {start: group.defined_line_start, end: group.defined_line_end})}>
        {group.defined_in}:{group.defined_line_start}
      </button>
      <ul>{group.call_sites.slice(0, callLimits[group.function_name] ?? 10).map((call, i) => <li key={`${call.file_id}:${call.line_start}:${i}`}>
        <button className="finding-source" onClick={() => openSource(call.file_id, {start: call.line_start, end: call.line_end})}>{call.path}:{call.line_start}</button>
      </li>)}</ul>
      {group.call_sites.length > (callLimits[group.function_name] ?? 10) && <button className="btn small" onClick={() => setCallLimits(current => ({...current, [group.function_name]: (current[group.function_name] ?? 10) + 20}))}>Show more call sites for {group.function_name}</button>}
    </article>)}</div>
    {result.groups.length > limit && <button className="btn small" onClick={() => setLimit(limit + 50)}>Show 50 more reuse candidates</button>}
    <details className="finding-limitations"><summary>Coverage and limitations</summary><ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul></details>
  </section>
}
