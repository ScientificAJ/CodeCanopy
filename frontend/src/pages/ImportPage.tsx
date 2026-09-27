import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { cancelRun, ensureSession, getRun, importGitHub, importZip, listProjects, listSnapshots } from '../services/v1/api'
import type { AnalysisRun } from '../types/v1'
interface Recent {id: string; name: string; created: string; snapshot?: string; revision?: string; status: string}
export default function ImportPage() {
  const navigate = useNavigate()
  const [source, setSource] = useState<'github' | 'zip'>('github')
  const [url, setUrl] = useState(''); const [ref, setRef] = useState(''); const [file, setFile] = useState<File | null>(null)
  const [ready, setReady] = useState(false); const [busy, setBusy] = useState(false)
  const [error, setError] = useState(''); const [recent, setRecent] = useState<Recent[]>([]); const [recentError, setRecentError] = useState('')
  const [runId, setRunId] = useState<string | null>(() => sessionStorage.getItem('codecanopy-import'))
  const [run, setRun] = useState<AnalysisRun | null>(null)
  useEffect(() => {
    let live = true
    ensureSession().then(async () => {
      if (live) setReady(true)
      const projects = await listProjects()
      const entries = await Promise.all(projects.slice().sort((a,b) => b.created_at.localeCompare(a.created_at)).slice(0,8).map(async p => {
        try {
          const snapshots = await listSnapshots(p.id); const snapshot = snapshots.at(-1)
          const run = snapshot?.analysis_run_id ? await getRun(snapshot.analysis_run_id).catch(() => null) : null
          return {id:p.id,name:p.name,created:snapshot?.created_at ?? p.created_at,snapshot:snapshot?.id,revision:(snapshot?.source.resolved_commit ?? snapshot?.source.archive_digest)?.slice(0,12),status:snapshot ? run?.status === 'partial' ? 'Partial — review diagnostics' : 'Structure ready' : 'No completed snapshot'}
        } catch {return {id:p.id,name:p.name,created:p.created_at,status:'Unavailable or expired — import again'}}
      }))
      if (live) setRecent(entries)
    }).catch(e => {if (live) setRecentError(e.message)})
    return () => {live = false}
  }, [])
  useEffect(() => {
    if (!runId || !ready) return
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const result = await getRun(runId, controller.signal)
        if (controller.signal.aborted) return
        setRun(result)
        if (['completed','partial','failed','cancelled'].includes(result.status)) {
          sessionStorage.removeItem('codecanopy-import'); setRunId(null); setBusy(false)
          if (result.result_snapshot_id) navigate(`/p/${result.project_id}/s/${result.result_snapshot_id}/overview`)
          else if (result.status === 'failed') setError(result.diagnostics.map(d => d.message).join(' ') || 'Import failed. Try again.')
        } else timer = setTimeout(poll, 600)
      } catch (e) {
        if (!controller.signal.aborted) {setError(e instanceof Error ? e.message : 'Unable to check import. Try again.'); setBusy(false); setRunId(null); sessionStorage.removeItem('codecanopy-import')}
      }
    }
    setBusy(true); void poll()
    return () => {controller.abort(); clearTimeout(timer)}
  }, [runId,ready,navigate])
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError(''); setRun(null)
    if (source === 'zip' && (!file || !file.name.toLowerCase().endsWith('.zip') || file.size > 50 * 1024 * 1024)) {setError('Choose a ZIP archive up to 50 MiB.'); return}
    if (source === 'github') {
      try {const parsed = new URL(url.trim()); if (parsed.protocol !== 'https:' || parsed.hostname !== 'github.com' || parsed.username || parsed.password || !/^\/[^/]+\/[^/]+\/?$/.test(parsed.pathname)) throw new Error()} catch {setError('Enter a public GitHub repository URL: https://github.com/owner/repository.'); return}
    }
    setBusy(true)
    try {
      const result = source === 'zip' ? await importZip(file!) : await importGitHub({url:url.trim(), ...(ref.trim() ? {ref:ref.trim()} : {})})
      sessionStorage.setItem('codecanopy-import',result.run_id); setRunId(result.run_id)
    } catch(e) {setError(e instanceof Error ? e.message : 'Import failed.'); setBusy(false)}
  }
  return <div className="import-page codecanopy-import">
    <a className="skip-link" href="#import-form">Skip to import</a>
    <header className="topbar codecanopy-topbar"><Link className="brand" to="/"><span className="brand-mark"><img src="/codecanopy-logo.png" alt=""/></span><span>CodeCanopy</span></Link></header>
    <main className="codecanopy-import-main"><section className="codecanopy-import-content">
      <img className="codecanopy-mascot" src="/codecanopy-logo.png" alt="CodeCanopy gecko"/>
      <h1>Find your way through the code.</h1><p className="import-intro">Import a repository. Explore its structure. Plan where to start.</p>
      <div className="import-card"><div role="group" aria-label="Import source" className="source-switch"><button disabled={busy} aria-pressed={source === 'github'} onClick={() => setSource('github')}>Public GitHub</button><button disabled={busy} aria-pressed={source === 'zip'} onClick={() => setSource('zip')}>Upload ZIP</button></div>
      <form id="import-form" onSubmit={submit}>
        {source === 'github' ? <><label htmlFor="repository-url">GitHub repository URL</label><input id="repository-url" type="url" required placeholder="https://github.com/owner/repository" value={url} disabled={busy} onChange={e => setUrl(e.target.value)}/><details className="import-advanced"><summary>Branch or tag (optional)</summary><label htmlFor="repository-ref">Branch, tag, or commit</label><input id="repository-ref" value={ref} maxLength={255} disabled={busy} placeholder="Repository default branch" onChange={e => setRef(e.target.value)}/><small>A branch or tag is resolved to an immutable commit before import.</small></details></> : <><label htmlFor="repository-zip">Repository ZIP archive</label><input id="repository-zip" type="file" accept=".zip,application/zip" required disabled={busy} onChange={e => setFile(e.target.files?.[0] ?? null)}/><p className="muted">Up to 50 MiB compressed. Source files are inspected without running their code.</p></>}
        <p className="import-policy">Source is stored on this API server for up to 24 hours, accessible through this browser workspace. You can delete the import. Importing runs static analysis; it does not send source to an AI provider.</p>
        <details className="import-advanced"><summary>What is excluded?</summary><p>Known credential files, private keys, and generated dependency/build directories are excluded. This is not a complete secret detector. Review your archive before uploading it.</p></details>
        <button className="btn primary import-submit" type="submit" disabled={!ready || busy || (source === 'github' ? !url.trim() : !file)}>{busy ? 'Importing…' : 'Explore repository'}</button>
      </form>
      {busy && <div className="import-progress" role="status"><strong>{run?.stage ? run.stage.replaceAll('_',' ') : source === 'zip' ? 'Uploading archive…' : 'Starting import…'}</strong><p>Preparing a read-only snapshot. Large repositories can take a little longer.</p>{runId && <button type="button" className="btn" onClick={() => cancelRun(runId).then(setRun).catch(e => setError(e.message))}>Cancel import</button>}</div>}
      {error && <p className="alert error" role="alert">{error}</p>}{run?.status === 'cancelled' && <p role="status">Import cancelled. You can start another import.</p>}</div>
      <section className="recent-imports" aria-label="Recent imports"><h2>Recent imports</h2>{recentError && <p role="status">Recent imports could not be loaded. Refresh to retry. {recentError}</p>}{!recent.length && !recentError && <p className="muted">Your completed imports will appear here in this browser workspace.</p>}{recent.map(item => <article key={item.id}><div>{item.snapshot ? <Link to={`/p/${item.id}/s/${item.snapshot}/overview`}>{item.name}</Link> : <strong>{item.name}</strong>}<small>{new Date(item.created).toLocaleString()} {item.revision && `· ${item.revision}`}</small></div><span className="badge">{item.status}</span></article>)}</section>
    </section></main>
  </div>
}
