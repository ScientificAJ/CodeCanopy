import { useEffect, useRef, useState } from 'react'
import type { SlotProps } from '../../contexts/SlotRegistry'
import type { AskResponse } from '../../types/v1/chat'
import { request, snapshotPath } from '../../services/v1/api'
import { renderMarkdown } from '../ask/markdown'
import './drafts.css'

type Kind = 'proposal' | 'documentation'
interface Draft { title: string; content: string; sources: AskResponse['sources']; limitations: string[]; scope: string }
const templates = {
  overview: 'Repository overview: purpose, main components, how they connect, and a suggested reading path.',
  onboarding: 'Getting started guide: prerequisites, installation, configuration, running, and tests. Include commands only when established by the supplied source.',
  reference: 'Developer reference: important interfaces, request/data flow, extension points, and known limitations.',
}
function readDraft(key: string): Draft | null {
  try {
    const d = JSON.parse(localStorage.getItem(key) ?? 'null') as Draft | null
    return d && typeof d.title === 'string' && typeof d.content === 'string' && typeof d.scope === 'string' && Array.isArray(d.limitations) && d.limitations.every(x => typeof x === 'string') && Array.isArray(d.sources) && d.sources.every(s => typeof s.id === 'string' && typeof s.file_id === 'string' && typeof s.path === 'string' && Number.isInteger(s.line_start) && Number.isInteger(s.line_end)) ? d : null
  } catch {return null}
}
export function exportDraft(draft: Draft, revision: string): string {
  return `# ${draft.title}\n\nRevision: ${revision}\nScope: ${draft.scope}\nStatus: AI-assisted draft; review before use.\n\n${draft.content}\n\n## Sources\n${draft.sources.map(s => `- [${s.id}] ${s.path}:${s.line_start}–${s.line_end}`).join('\n') || 'No source citations returned.'}\n\n## Limitations\n${draft.limitations.map(x => `- ${x}`).join('\n') || '- Based on retrieved excerpts, not an exhaustive repository review.'}\n`
}

export function DraftWorkspace({ kind, ...context }: SlotProps & {kind: Kind}) {
  const { projectId, snapshotId, snapshot, files, selectedEntity, openSource } = context
  const key = `grepo-draft:${projectId}:${snapshotId}:${kind}`
  const [draft, setDraft] = useState<Draft | null>(() => readDraft(key))
  const [goal, setGoal] = useState('')
  const [template, setTemplate] = useState<keyof typeof templates>('overview')
  const [scope, setScope] = useState('repository')
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const current = useRef<AbortController | null>(null)
  const proposal = kind === 'proposal'
  const selected = files.find(f => f.id === selectedEntity?.fileId && f.is_text && !f.excluded)
  const scopedFile = scope !== 'repository' ? files.find(f => f.id === scope && f.is_text && !f.excluded) : undefined
  const revision = snapshot.source.resolved_commit ?? snapshot.source.archive_digest ?? snapshotId
  useEffect(() => () => current.current?.abort(), [])
  function save(next: Draft) {
    setDraft(next)
    try {localStorage.setItem(key, JSON.stringify(next)); setNotice('Draft saved in this browser.')}
    catch {setNotice('Browser storage is unavailable. Export your draft to keep it.')}
  }
  async function generate() {
    if (busy || (proposal && !goal.trim())) return
    const controller = new AbortController(); current.current = controller
    setBusy(true); setError(''); setNotice('')
    const intent = proposal
      ? `Create a proposed change plan for this goal: ${goal.trim()}. Use sections: Goal, Current behavior, Proposed changes, Affected files, Validation plan, Risks and open questions. Cite evidence for existing behavior. Clearly label proposed behavior and suggested tests as unimplemented. Do not claim to have modified files or run tests. Do not produce a patch.`
      : `Write documentation for developers. ${templates[template]} Use clear Markdown sections. Cite repository facts. Explicitly mark unknown details; do not invent setup commands or interfaces.`
    try {
      const result = await request<AskResponse>(snapshotPath(projectId, snapshotId) + '/chat', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, signal: controller.signal,
        body: JSON.stringify({question: intent + ' Keep the complete draft under 650 words. Finish every section. Use plain headings without emoji.', purpose: kind, scope: scopedFile ? 'file' : 'repository', ...(scopedFile ? {file_id: scopedFile.id} : {})}),
      })
      if (controller.signal.aborted) return
      if (!result.answer?.trim()) throw new Error('No draft was returned. Please try again.')
      save({title: proposal ? goal.trim() : {overview: 'Repository overview', onboarding: 'Getting started', reference: 'Developer reference'}[template], content: result.answer, sources: result.sources, limitations: result.limitations, scope: scopedFile?.path ?? 'Entire repository'})
      setEditing(false)
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Generation failed. Try again.')
    } finally {if (current.current === controller) {setBusy(false); current.current = null}}
  }
  function cancel() {current.current?.abort(); current.current = null; setBusy(false); setNotice('Generation cancelled.')}
  function download() {
    if (!draft) return
    const url = URL.createObjectURL(new Blob([exportDraft(draft, revision)], {type: 'text/markdown;charset=utf-8'}))
    const a = document.createElement('a'); a.href = url; a.download = `grepo-${kind}-${snapshotId.slice(0,8)}.md`; a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <section className="draft-workspace" aria-label={proposal ? 'Change proposals' : 'Repository documentation'}>
    <div className="draft-heading"><div><h2>{proposal ? 'Plan a change with the code in view.' : 'Turn source into a useful guide.'}</h2><p>{proposal ? 'Describe your goal to draft a source-backed plan, affected files, and checks to perform.' : 'Generate a guide grounded in the imported revision, then review and edit it.'}</p></div><span className="badge">{proposal ? 'Change planning' : 'Documentation'}</span></div>
    <form className="draft-form" onSubmit={e => {e.preventDefault(); void generate()}}>
      {proposal ? <label>What would you like to change?<textarea value={goal} maxLength={2800} rows={3} disabled={busy} required placeholder="For example: improve retry handling for temporary API failures" onChange={e => setGoal(e.target.value)}/></label>
        : <label>Document type<select value={template} disabled={busy} onChange={e => setTemplate(e.target.value as keyof typeof templates)}><option value="overview">Repository overview</option><option value="onboarding">Getting started</option><option value="reference">Developer reference</option></select></label>}
      <label>Source scope<select value={scope} disabled={busy} onChange={e => setScope(e.target.value)}><option value="repository">Entire repository</option>{selected && <option value={selected.id}>{selected.path}</option>}{scopedFile && scopedFile.id !== selected?.id && <option value={scopedFile.id}>{scopedFile.path}</option>}</select></label>
      <p className="muted">Generation sends relevant source excerpts to the configured AI provider. {proposal ? 'A proposal does not modify your repository.' : 'Check cited evidence before publishing.'}</p>
      <div className="draft-actions"><button className="btn primary" type="submit" disabled={busy || (proposal && !goal.trim())}>{busy ? 'Generating draft…' : draft ? 'Regenerate draft' : proposal ? 'Generate proposal' : 'Generate documentation'}</button>{busy && <button type="button" className="btn" onClick={cancel}>Cancel generation</button>}</div>
    </form>
    {busy && <p role="status">Reading relevant source and preparing your draft…</p>}
    {error && <p className="alert error" role="alert">{error}</p>}
    {notice && <p role="status" className="muted">{notice}</p>}
    {draft ? <div className="draft-result">
      <div className="draft-heading"><div><span className="badge">Draft · review required</span><h3>{draft.title}</h3><p className="muted">{draft.scope} · Revision {revision.slice(0,12)}</p></div><div className="draft-actions"><button className="btn" disabled={busy} onClick={() => setEditing(!editing)}>{editing ? 'Preview draft' : 'Edit draft'}</button><button className="btn" onClick={download}>Export Markdown</button></div></div>
      {editing ? <label className="draft-editor">Draft content<textarea aria-label="Draft content" rows={22} value={draft.content} onChange={e => save({...draft, content: e.target.value})}/><small>Edits are saved locally. Check that citations still support your changes.</small></label> : <article className="draft-preview">{renderMarkdown(draft.content)}</article>}
      {draft.limitations.length > 0 && <aside className="draft-limitations" aria-label="Draft limitations"><h4>Coverage & limitations</h4><ul>{draft.limitations.map((item,i) => <li key={i}>{item}</li>)}</ul></aside>}
      <section className="draft-sources" aria-label="Draft sources"><h4>Source evidence</h4>{draft.sources.length ? draft.sources.map(s => <button className="btn small" key={s.id} onClick={() => openSource(s.file_id, {start:s.line_start,end:s.line_end})}>[{s.id}] {s.path}:{s.line_start}–{s.line_end}</button>) : <p>No source citations returned. Treat this draft as unverified.</p>}</section>
    </div> : <div className="draft-empty"><h3>{proposal ? 'Start with one concrete improvement.' : 'Choose the guide your team needs.'}</h3><p>{proposal ? 'Your plan will appear here with evidence you can open and review.' : 'Your generated document will appear here with source references and an editable preview.'}</p></div>}
  </section>
}
