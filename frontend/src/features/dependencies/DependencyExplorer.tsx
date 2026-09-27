import { useMemo, useState } from 'react'
import type { SlotProps } from '../../contexts/SlotRegistry'
import type { DependencyNode, DependencyResult } from './types'
import { projectGraph, reachable } from './graph'
import './dependencies.css'

export function DependencyExplorer(props: SlotProps<DependencyResult>) {
  if (props.request.status === 'loading') return <p role="status">Resolving static dependencies…</p>
  if (props.request.status === 'error') return <p className="alert error" role="alert">{props.request.message}</p>
  if (props.request.status !== 'ready') return null
  return <Explorer key={props.snapshotId} result={props.request.data} openSource={props.openSource} initialId={props.selectedEntity?.fileId} />
}
function Explorer({result, openSource, initialId}: {result: DependencyResult; openSource: SlotProps['openSource']; initialId?: string}) {
  const [mode, setMode] = useState<'file' | 'function'>('file')
  const [picked, setPicked] = useState(initialId ?? '')
  const [search, setSearch] = useState('')
  const [direction, setDirection] = useState<'out' | 'in' | 'impact'>('out')
  const [limit, setLimit] = useState(50)
  const graph = useMemo(() => projectGraph(result, mode), [result, mode])
  const sources = new Set(graph.edges.map(e => e.source_id))
  const connectedIds = new Set([...sources, ...graph.edges.map(e => e.target_id)])
  const options = graph.nodes.filter(n => mode === 'file' || n.kind === 'function' || sources.has(n.id))
  const selected = options.find(n => n.id === picked) ?? options.find(n => connectedIds.has(n.id)) ?? options[0]
  const incoming = graph.edges.filter(e => e.target_id === selected?.id)
  const outgoing = graph.edges.filter(e => e.source_id === selected?.id)
  const impact = useMemo(() => reachable(selected?.id ?? '', graph.edges, true), [selected?.id, graph.edges])
  const dependencies = useMemo(() => reachable(selected?.id ?? '', graph.edges), [selected?.id, graph.edges])
  const connected = direction === 'impact' ? [...impact.ids] : [...new Set((direction === 'in' ? incoming : outgoing).map(e => direction === 'in' ? e.source_id : e.target_id))]
  const matches = connected.map(id => graph.byId.get(id)!).filter(Boolean).filter(n => `${n.path} ${n.label}`.toLowerCase().includes(search.toLowerCase()))
  const unresolved = result.unresolved.filter(u => mode === 'file' ? u.file_id === selected?.file_id : u.source_id === selected?.id)
  function pick(id: string) { setPicked(id); setLimit(50) }
  function label(node: DependencyNode) { return node.kind === 'function' ? `${node.label} · ${node.path}:${node.line_start}` : node.path }
  function miniNodes(ids: string[], side: string) {
    const unique = [...new Set(ids)]
    return <div className="dependency-lane"><span className="eyebrow">{side}</span>{unique.slice(0, 6).map(id => {
      const node = graph.byId.get(id)!
      return <button className="dependency-node" key={id} onClick={() => pick(id)} title={label(node)}>{node.label}<small>{node.path}</small></button>
    })}{unique.length > 6 && <small>+{unique.length - 6} more in the list</small>}{!unique.length && <p className="dependency-muted">No resolved connections</p>}</div>
  }
  return <section className="dependency-explorer" aria-label="Dependency explorer">
    <header className="finding-heading"><div><h2>Follow the connections</h2><p>Explore what depends on what, from files down to function calls.</p></div><span className="badge">Static analysis</span></header>
    <div className="dependency-stats"><div><strong>{result.coverage.analyzed_files}<small> / {result.coverage.inventoried_files}</small></strong><span>files analyzed</span></div><div><strong>{result.edges.filter(e => e.kind === 'imports').length}</strong><span>import connections</span></div><div><strong>{result.edges.filter(e => e.kind === 'calls').length}</strong><span>function calls</span></div><div><strong>{result.coverage.unresolved_count}</strong><span>unresolved references</span></div></div>
    {result.coverage.truncated && <p role="status" className="alert">Analysis reached a size limit. Counts and connections below are partial.</p>}
    {!result.coverage.analyzed_files && <p className="alert">No files have supported dependency bindings. Import Python or JavaScript/TypeScript source; older snapshots need to be imported again.</p>}
    <div className="dependency-controls"><label>Explore<select aria-label="Dependency level" value={mode} onChange={e => {setMode(e.target.value as 'file' | 'function'); setPicked(''); setLimit(50)}}><option value="file">Files</option><option value="function">Functions</option></select></label>
      <label className="dependency-subject">Focus<select aria-label="Dependency focus" value={selected?.id ?? ''} onChange={e => pick(e.target.value)}>{options.map(n => <option key={n.id} value={n.id}>{label(n)}</option>)}</select></label></div>
    {selected && <>
      <div className="dependency-map" aria-label="Direct dependency connections">
        {miniNodes(incoming.map(e => e.source_id), 'Used by')}
        <span className="dependency-arrow" aria-hidden="true">→</span>
        <div className="dependency-center"><span className="eyebrow">Selected {selected.kind}</span><strong>{selected.label}</strong><small>{selected.path}</small><button onClick={() => openSource(selected.file_id, {start: selected.line_start, end: selected.line_end})}>Open source</button></div>
        <span className="dependency-arrow" aria-hidden="true">→</span>
        {miniNodes(outgoing.map(e => e.target_id), 'Depends on')}
      </div>
      <p className="dependency-muted">Arrows point from the caller or importing file to its dependency. File view combines imports and cross-file calls.</p>
      {dependencies.cycle && <p className="alert">A dependency cycle includes this selection. Follow the connections to inspect it.</p>}
      <div className="dependency-controls"><div className="dependency-tabs" role="group" aria-label="Connection direction">{([['out', 'Depends on'], ['in', 'Used by'], ['impact', 'Potential impact']] as const).map(([id, name]) => <button key={id} aria-pressed={direction === id} onClick={() => {setDirection(id); setLimit(50)}}>{name}</button>)}</div><label>Filter connections<input aria-label="Filter connections" placeholder="File or function name" value={search} onChange={e => {setSearch(e.target.value); setLimit(50)}} /></label></div>
      {direction === 'impact' && <p>These {impact.ids.size}{impact.truncated ? '+' : ''} items can reach the selection through one or more static connections. Review them when making a change; this does not prove they will break.{impact.truncated && ' Traversal is limited to 1,000 items.'}</p>}
      <p role="status">{matches.length} matching {direction === 'impact' ? 'potentially affected items' : 'connections'}</p>
      <div className="finding-list">{matches.slice(0, limit).map(n => <article className="finding-row" key={n.id}><div className="finding-row__title"><button className="finding-source" onClick={() => pick(n.id)}>{label(n)}</button><span className="badge">{n.kind}</span></div>
        {direction !== 'impact' && (direction === 'in' ? incoming : outgoing).filter(e => e.source_id === n.id || e.target_id === n.id).slice(0, 8).map(e => <button key={e.id} className="finding-source dependency-evidence" onClick={() => openSource(e.file_id, {start: e.line_start, end: e.line_end})}>{e.kind === 'imports' ? 'Import' : 'Call'} at {graph.byId.get(e.file_id)?.path}:{e.line_start}</button>)}
        <button className="dependency-source" onClick={() => openSource(n.file_id, {start: n.line_start, end: n.line_end})}>View {n.kind === 'function' ? 'definition' : 'file'}</button>
      </article>)}</div>
      {!matches.length && <p className="dependency-muted">No matching resolved connections. Unresolved references and analysis coverage are shown below.</p>}
      {matches.length > limit && <button onClick={() => setLimit(limit + 50)}>Show 50 more</button>}
      <details className="finding-limitations"><summary>Unresolved references for this selection ({unresolved.length}{result.coverage.truncated ? '+' : ''})</summary><p>These references could not be connected safely. They do not imply missing code or unused functions.</p>{unresolved.slice(0, 100).map((u, i) => <div className="dependency-unresolved" key={i}><button className="finding-source" onClick={() => openSource(u.file_id, {start: u.line_start, end: u.line_start})}>{u.name} · line {u.line_start}</button><small>{u.reason}</small></div>)}{unresolved.length > 100 && <p>Showing the first 100 references.</p>}</details>
    </>}
    <details className="finding-limitations"><summary>Coverage and limitations</summary><p>{result.coverage.unsupported_files} files were not analyzed for dependencies, including excluded, binary, unsupported, unparsed, or older source.</p><ul>{result.coverage.limitations.map(text => <li key={text}>{text}</li>)}</ul></details>
  </section>
}
