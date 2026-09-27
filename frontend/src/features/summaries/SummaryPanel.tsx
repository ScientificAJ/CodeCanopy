import type { SlotProps } from '../../contexts/SlotRegistry'
import type { SummaryPayload } from '../../contexts/FeatureContracts'
import type { Evidence } from '../../types/v1/prd.generated'

function BasisBadge({ basis }: { basis: Evidence['basis'] }) {
  const label = basis === 'observed' ? 'observed' : basis === 'resolved' ? 'resolved' : 'inferred'
  return <span className="badge" title={`Basis: ${label}`}>{label}</span>
}

function CitationButton({
  ev,
  openSource,
}: {
  ev: Evidence
  openSource: SlotProps<SummaryPayload>['openSource']
}) {
  return (
    <button
      className="finding-source"
      onClick={() => openSource(ev.file_id, { start: ev.range.line_start, end: ev.range.line_end })}
      title={`${ev.path} lines ${ev.range.line_start}–${ev.range.line_end}`}
    >
      {ev.path}:{ev.range.line_start}
      {ev.range.line_end !== ev.range.line_start ? `–${ev.range.line_end}` : ''}
    </button>
  )
}

/** Parse claim sentences from `text`.  Each sentence may end with [evidence-id]. */
function parseClaimLines(text: string, evidenceById: Map<string, Evidence>) {
  return text.split('\n').filter(Boolean).map((line, i) => {
    const match = line.match(/\[([a-f0-9]{32})\]\.?$/)
    const evidenceId = match ? match[1] : null
    const ev = evidenceId ? evidenceById.get(evidenceId) ?? null : null
    const cleanLine = match ? line.slice(0, match.index).trimEnd() : line
    return { key: i, text: cleanLine, ev }
  })
}

export function SummaryPanel({ request, openSource }: SlotProps<SummaryPayload>) {
  if (request.status === 'idle') return null

  if (request.status === 'loading') {
    return <p className="pad" role="status">Building summary…</p>
  }

  if (request.status === 'error') {
    return <p className="alert error" role="alert">{request.message}</p>
  }

  const { data } = request
  const evidenceById = new Map(data.evidence.map(ev => [ev.id, ev]))
  const claims = parseClaimLines(data.text, evidenceById)

  return (
    <section className="finding-view" aria-label="File/folder summary">
      <header className="finding-heading">
        <div>
          <h2>Summary</h2>
          <p>Every claim is derived from AST facts; citations are true by construction.</p>
        </div>
      </header>

      <ul className="finding-list" style={{ listStyle: 'none', padding: 0 }}>
        {claims.map(({ key, text, ev }) => (
          <li key={key} style={{ marginBottom: '0.5em' }}>
            <span>{text}</span>
            {ev && (
              <>
                {' '}
                <BasisBadge basis={ev.basis} />
                {' '}
                <CitationButton ev={ev} openSource={openSource} />
              </>
            )}
          </li>
        ))}
      </ul>

      {data.limitations.length > 0 && (
        <details className="finding-limitations">
          <summary>Unverified claims and limitations ({data.limitations.length})</summary>
          <ul>
            {data.limitations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
