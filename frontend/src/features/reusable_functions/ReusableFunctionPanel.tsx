import type { SlotProps } from '../../contexts/SlotRegistry'
import type { ReusableFunctionResult, ReusableGroup } from '../../types/codebase'

export function ReusableFunctionPanel(props: SlotProps<ReusableFunctionResult>) {
  const { request, files, openSource } = props

  function jumpTo(path: string, line: number) {
    const record = files.find(f => f.path === path)
    if (record) openSource(record.id, { start: line, end: line })
  }

  if (request.status === 'loading') return <p className="pad" role="status">Scanning for reusable functions…</p>
  if (request.status === 'error') return <p className="alert error" role="alert">{request.message}</p>
  if (request.status !== 'ready') return null

  const result = request.data
  if (!result.total_reusable) return <p className="pad">No reusable functions detected across multiple files.</p>

  return (
    <section aria-label="Reusable functions">
      <p className="eyebrow">{result.total_reusable} REUSABLE FUNCTION{result.total_reusable !== 1 ? 'S' : ''} FOUND</p>
      {result.groups.map(group => (
        <GroupRow key={`${group.defined_in}:${group.function_name}`} group={group} jumpTo={jumpTo} />
      ))}
    </section>
  )
}

function GroupRow({ group, jumpTo }: { group: ReusableGroup; jumpTo: (path: string, line: number) => void }) {
  return (
    <div className="reuse-group">
      <div className="reuse-group__header">
        <code>{group.function_name}</code>
        <button className="btn small" onClick={() => jumpTo(group.defined_in, group.defined_line_start)}>
          {group.defined_in}:{group.defined_line_start}
        </button>
      </div>
      <ul className="reuse-group__callers">
        {group.called_from.map(path => (
          <li key={path}>
            <button className="btn subtle" onClick={() => jumpTo(path, 1)}>{path}</button>
          </li>
        ))}
      </ul>
    </div>
  )
}
