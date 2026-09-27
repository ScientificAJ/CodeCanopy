import { useState } from 'react'
import type { DuplicateDetectionResult, PotentiallyUnusedFunction, UnusedDetectionResult } from '../../types/v1'
import { registerFeature } from '../../contexts/FeatureContracts'
import type { SlotProps } from '../../contexts/SlotRegistry'
import { getDuplicateFindings, getUnusedFindings } from '../../services/v1/api'

function Status({request}: {request: SlotProps['request']}) {
  if (request.status === 'loading') return <p role="status">Comparing parsed functions…</p>
  if (request.status === 'error') return <p role="alert">{request.message}</p>
  return null
}

function Limitations({items}: {items: string[]}) {
  return items.length ? <details className="finding-limitations"><summary>Coverage and limitations</summary><ul>{items.map(item => <li key={item}>{item}</li>)}</ul></details> : null
}

function DuplicateFindings(props: SlotProps<DuplicateDetectionResult>) {
  const result = props.request.status === 'ready' ? props.request.data : null
  return <section className="finding-view" aria-label="Duplicate functionality findings">
    <header className="finding-heading"><div><h2>Possible duplicate functionality</h2><p>Structural matches are ranked for review; similarity is not proof of identical behavior.</p></div>{result && <span className="badge">{result.candidates.length} candidates</span>}</header>
    <Status request={props.request}/>
    {result && (result.candidates.length ? <div className="finding-list">{result.candidates.map(candidate => <article className="finding-row" key={candidate.id}>
      <div className="finding-row__title"><strong>{candidate.functions.map(item => item.name).join(' · ')}</strong><span className={`badge confidence-${candidate.confidence}`}>{candidate.confidence} similarity</span></div>
      <p className="finding-score">AST structure {Math.round(candidate.structural_similarity * 100)}%{candidate.semantic_similarity != null ? ` · AI semantic ${Math.round(candidate.semantic_similarity * 100)}%` : ''} · Review recommended</p>
      <div className="finding-evidence">{candidate.functions.map(item => <button className="finding-source" key={item.id} onClick={() => props.openSource(item.file_id, {start: item.line_start, end: item.line_end})}><span>{item.path}</span><small>{item.name} · line {item.line_start}</small></button>)}</div>
    </article>)}</div> : <p>No duplicate candidates were found in the parsed functions.</p>)}
    {result && <Limitations items={result.coverage.limitations}/ >}
  </section>
}

function UnusedFindings(props: SlotProps<UnusedDetectionResult>) {
  const [limit, setLimit] = useState(50)
  const result = props.request.status === 'ready' ? props.request.data : null
  return <section className="finding-view" aria-label="Potentially unused functions">
    <header className="finding-heading"><div><h2>Potentially unused functions</h2><p>Static references are incomplete; review each candidate before removing it.</p></div>{result && <span className="badge">{result.findings.length} candidates</span>}</header>
    <Status request={props.request}/>
    {result && (result.findings.length ? <div className="finding-list">{result.findings.slice(0, limit).map((finding: PotentiallyUnusedFunction) => <article className="finding-row" key={finding.id}>
      <div className="finding-row__title"><strong>{finding.function.name}</strong><span className="badge confidence-low">Potentially unused</span></div>
      <p className="finding-score">{finding.explanation}</p>
      <button className="finding-source" onClick={() => props.openSource(finding.function.file_id, {start: finding.function.line_start, end: finding.function.line_end})}><span>{finding.function.path}</span><small>{finding.function.name} · line {finding.function.line_start}</small></button>
    </article>)}</div> : <p>No potentially unused functions were found in the parsed source files.</p>)}
    {result && result.findings.length > limit && <button className="btn small" onClick={() => setLimit(limit + 50)}>Show 50 more unused candidates</button>}
    {result && <Limitations items={result.coverage.limitations}/ >}
  </section>
}

registerFeature('duplicates.compare', {
  Component: DuplicateFindings,
  load: (context, signal) => getDuplicateFindings(context.projectId, context.snapshotId, signal),
})

registerFeature('unused.review', {
  Component: UnusedFindings,
  load: (context, signal) => getUnusedFindings(context.projectId, context.snapshotId, signal),
})