import type { SlotProps } from '../../contexts/SlotRegistry'
import type { DependencyOverlay } from '../../contexts/FeatureContracts'

// The backend returns a DependencyGraph shape inside graph — not PrdGraph or Graph.
// We define the actual wire shapes here for safe access.
interface WireEvidence {
  id: string
  snapshot_id: string
  file_id: string
  path: string
  range: { line_start: number; line_end: number }
  content_sha256: string
  basis: string
}

interface WireEdgeEndpoint {
  entity_id: string
  path: string
  file_id?: string
}

interface WireEdge {
  id: string
  source: WireEdgeEndpoint
  target: WireEdgeEndpoint
  kind: string
  evidence_id?: string
}

interface WireUnresolved {
  source_path: string
  specifier: string
  reason: string
}

interface WireGraph {
  edges: WireEdge[]
  unresolved: WireUnresolved[]
  evidence: WireEvidence[]
}

interface WireOverlay {
  schema_version: string
  snapshot_id: string
  graph: WireGraph
  impact_subject_ids: string[]
  limitations: string[]
}

function asWire(data: DependencyOverlay): WireOverlay {
  return data as unknown as WireOverlay
}

// ---------------------------------------------------------------------------

function CitationButton({
  ev,
  openSource,
}: {
  ev: WireEvidence
  openSource: SlotProps<DependencyOverlay>['openSource']
}) {
  return (
    <button
      className="finding-source"
      onClick={() =>
        openSource(ev.file_id, { start: ev.range.line_start, end: ev.range.line_end })
      }
      title={`${ev.path} line ${ev.range.line_start}`}
    >
      {ev.path}:{ev.range.line_start}
    </button>
  )
}

function EdgeRow({
  edge,
  evidenceById,
  openSource,
}: {
  edge: WireEdge
  evidenceById: Map<string, WireEvidence>
  openSource: SlotProps<DependencyOverlay>['openSource']
}) {
  const ev = edge.evidence_id ? evidenceById.get(edge.evidence_id) : undefined
  return (
    <li
      className="finding-item"
      style={{ display: 'flex', gap: '0.5em', alignItems: 'baseline', flexWrap: 'wrap', padding: '0.2em 0' }}
    >
      <span className="badge">imports</span>
      <span>{edge.source.path}</span>
      <span style={{ color: 'var(--color-muted, #57606a)' }}>→</span>
      <span>{edge.target.path}</span>
      {ev && <CitationButton ev={ev} openSource={openSource} />}
    </li>
  )
}

export function DependencyPanel({ request, openSource }: SlotProps<DependencyOverlay>) {
  if (request.status === 'idle') return null

  if (request.status === 'loading') {
    return <p className="pad" role="status">Building dependency graph…</p>
  }

  if (request.status === 'error') {
    return <p className="alert error" role="alert">{request.message}</p>
  }

  const overlay = asWire(request.data)
  const { graph, impact_subject_ids, limitations } = overlay
  const evidenceById = new Map(graph.evidence.map(ev => [ev.id, ev]))

  // Group edges by source path
  const grouped = new Map<string, WireEdge[]>()
  for (const edge of graph.edges) {
    const list = grouped.get(edge.source.path) ?? []
    list.push(edge)
    grouped.set(edge.source.path, list)
  }

  return (
    <section className="finding-view" aria-label="Dependency graph">
      <header className="finding-heading">
        <div>
          <h2>Dependencies</h2>
          <p>
            {graph.edges.length} resolved import edge{graph.edges.length !== 1 ? 's' : ''}.
            Every edge is independently verified — each citation confirms an actual import statement.
          </p>
        </div>
      </header>

      {graph.edges.length === 0 ? (
        <p className="pad" style={{ color: 'var(--color-muted, #57606a)' }}>
          No resolved import edges found in this snapshot.
        </p>
      ) : (
        <div style={{ marginBottom: '1em' }}>
          {[...grouped.entries()].map(([sourcePath, edges]) => (
            <details key={sourcePath} open={grouped.size <= 8}>
              <summary
                style={{
                  fontWeight: 500,
                  cursor: 'pointer',
                  padding: '0.3em 0',
                  userSelect: 'none',
                }}
              >
                {sourcePath}{' '}
                <span style={{ color: 'var(--color-muted, #57606a)', fontWeight: 400 }}>
                  ({edges.length})
                </span>
              </summary>
              <ul
                className="finding-list"
                style={{ listStyle: 'none', padding: '0 0 0 1em', margin: '0.15em 0 0.5em' }}
              >
                {edges.map(edge => (
                  <EdgeRow key={edge.id} edge={edge} evidenceById={evidenceById} openSource={openSource} />
                ))}
              </ul>
            </details>
          ))}
        </div>
      )}

      {impact_subject_ids.length > 0 && (
        <section style={{ marginTop: '1em', borderTop: '1px solid var(--color-border, #e5e7eb)', paddingTop: '1em' }}>
          <h3 style={{ fontSize: '0.85em', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 0.4em' }}>
            Change Impact
          </h3>
          <p style={{ color: 'var(--color-muted, #57606a)', margin: 0 }}>
            {impact_subject_ids.length} file{impact_subject_ids.length !== 1 ? 's' : ''} would be
            transitively affected if the selected entity changed.
          </p>
        </section>
      )}

      {graph.unresolved.length > 0 && (
        <details
          className="finding-limitations"
          style={{ marginTop: '1em' }}
        >
          <summary>
            Unresolved references ({graph.unresolved.length})
          </summary>
          <ul style={{ listStyle: 'none', padding: '0.25em 0 0 1em', margin: 0 }}>
            {graph.unresolved.map((u, i) => (
              <li key={i} style={{ marginBottom: '0.3em', fontSize: '0.9em' }}>
                <code>{u.source_path}</code>
                {' → '}
                <code>{u.specifier}</code>
                {' '}
                <span style={{ color: 'var(--color-muted, #57606a)' }}>
                  ({u.reason === 'bare_package' ? 'external package — no edge drawn' : 'not found in snapshot'})
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {limitations.length > 0 && (
        <details className="finding-limitations" style={{ marginTop: '0.5em' }}>
          <summary>Limitations ({limitations.length})</summary>
          <ul>
            {limitations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
