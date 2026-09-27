import type { SlotProps } from '../../contexts/SlotRegistry'
import type { ChangePack } from '../../types/v1/prd.generated'

// The backend returns its own ProposalsResponse shape. Define the wire types
// here rather than trusting the generated ChangePack, which the endpoint does
// not actually produce.
interface WireEvidence {
  file_id: string
  path: string
  line_start: number
  line_end: number
  content_sha256: string
}

interface WireProposal {
  id: string
  kind: string
  title: string
  detail: string
  subject_path: string
  affected_paths: string[]
  affected_count: number
  impact_truncated: boolean
  evidence: WireEvidence[]
  limitations: string[]
}

interface WireProposals {
  schema_version: string
  snapshot_id: string
  proposals: WireProposal[]
  limitations: string[]
}

function asWire(data: ChangePack): WireProposals {
  return data as unknown as WireProposals
}

// ---------------------------------------------------------------------------

function CitationButton({
  ev,
  openSource,
}: {
  ev: WireEvidence
  openSource: SlotProps<ChangePack>['openSource']
}) {
  return (
    <button
      className="finding-source"
      onClick={() => openSource(ev.file_id, { start: ev.line_start, end: ev.line_end })}
      title={`${ev.path} line ${ev.line_start}`}
    >
      {ev.path}:{ev.line_start}
    </button>
  )
}

function ProposalCard({
  proposal,
  openSource,
}: {
  proposal: WireProposal
  openSource: SlotProps<ChangePack>['openSource']
}) {
  const isImpact = proposal.kind === 'change_impact'

  return (
    <article
      className="finding-item"
      style={{
        display: 'block',
        borderTop: '1px solid var(--color-border, #e5e7eb)',
        paddingTop: '0.6em',
        marginTop: '0.6em',
      }}
    >
      <div style={{ display: 'flex', gap: '0.5em', alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span className="badge">{isImpact ? 'change impact' : 'review first'}</span>
        <strong style={{ fontWeight: 500 }}>{proposal.subject_path}</strong>
        <span style={{ color: 'var(--color-muted, #57606a)', fontSize: '0.9em' }}>
          {proposal.affected_count} affected
          {proposal.impact_truncated ? '+' : ''}
        </span>
      </div>

      <p style={{ margin: '0.4em 0', fontSize: '0.92em' }}>{proposal.detail}</p>

      {proposal.evidence.length > 0 && (
        <div style={{ display: 'flex', gap: '0.4em', flexWrap: 'wrap', marginBottom: '0.3em' }}>
          {proposal.evidence.map((ev, i) => (
            <CitationButton key={i} ev={ev} openSource={openSource} />
          ))}
        </div>
      )}

      {proposal.affected_paths.length > 0 && (
        <ul
          className="finding-list"
          style={{ listStyle: 'none', padding: 0, margin: '0.2em 0 0', fontSize: '0.88em' }}
        >
          {proposal.affected_paths.map(path => (
            <li key={path} style={{ color: 'var(--color-muted, #57606a)' }}>
              {path}
            </li>
          ))}
        </ul>
      )}

      {proposal.limitations.length > 0 && (
        <ul style={{ margin: '0.4em 0 0', paddingLeft: '1.1em', fontSize: '0.85em' }}>
          {proposal.limitations.map((line, i) => (
            <li key={i} style={{ color: 'var(--color-muted, #57606a)' }}>
              {line}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

export function ProposalsPanel({ request, openSource }: SlotProps<ChangePack>) {
  if (request.status === 'idle') return null

  if (request.status === 'loading') {
    return <p className="pad" role="status">Deriving change proposals…</p>
  }

  if (request.status === 'error') {
    return <p className="alert error" role="alert">{request.message}</p>
  }

  const { proposals, limitations } = asWire(request.data)

  return (
    <section className="finding-view" aria-label="Proposals and change packs">
      <header className="finding-heading">
        <div>
          <h2>Proposals</h2>
          <p>
            {proposals.length} proposal{proposals.length !== 1 ? 's' : ''}, derived only from
            verified import edges. Each one names the file that causes the change and cites the
            import line that proves it.
          </p>
        </div>
      </header>

      {proposals.length === 0 ? (
        <p className="pad" style={{ color: 'var(--color-muted, #57606a)' }}>
          No change proposal can be derived from this snapshot.
        </p>
      ) : (
        proposals.map(proposal => (
          <ProposalCard key={proposal.id} proposal={proposal} openSource={openSource} />
        ))
      )}

      {limitations.length > 0 && (
        <details className="finding-limitations" style={{ marginTop: '1em' }}>
          <summary>Limitations ({limitations.length})</summary>
          <ul>
            {limitations.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
