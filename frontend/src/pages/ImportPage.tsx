import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { cancelRun, ensureSession, getRun, importGitHub, importZip, listProjects } from '../services/v1/api'
import type { AnalysisRun, V1Project } from '../types/v1'
import { Icon } from '../components/ui/Icon'
export default function ImportPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<'github' | 'zip' | 'recent'>('github')
  const [url, setUrl] = useState(''); const [ref, setRef] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [ready, setReady] = useState(false); const [busy, setBusy] = useState(false)
  const [error, setError] = useState(''); const [projects, setProjects] = useState<V1Project[]>([])
  const [runId, setRunId] = useState<string | null>(() => sessionStorage.getItem('codecanopy-import'))
  const [run, setRun] = useState<AnalysisRun | null>(null)
  useEffect(() => { let live = true; ensureSession().then(() => listProjects()).then(p => {if (live) {setProjects(p); setReady(true)}}).catch(e => {if (live) setError(e.message)}); return () => {live = false} }, [])
  useEffect(() => {
    if (!runId || !ready) return
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const result = await getRun(runId, controller.signal)
        if (controller.signal.aborted) return
        setRun(result)
        if (['completed', 'partial', 'failed', 'cancelled'].includes(result.status)) {
          sessionStorage.removeItem('codecanopy-import'); setRunId(null); setBusy(false)
          if (result.result_snapshot_id) navigate(`/p/${result.project_id}/s/${result.result_snapshot_id}/overview`)
          else if (result.status === 'failed') setError(result.diagnostics.map(d => d.message).join(' ') || 'Import failed.')
        } else timer = setTimeout(poll, 600)
      } catch (e) { if (!controller.signal.aborted) {setError(e instanceof Error ? e.message : 'Unable to check import status.'); setBusy(false)} }
    }
    setBusy(true); void poll()
    return () => {controller.abort(); clearTimeout(timer)}
  }, [runId, ready, navigate])
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setRun(null)
    try {
      const result = tab === 'zip' && file ? await importZip(file) : await importGitHub({url: url.trim(), ref: ref.trim() || 'HEAD'})
      sessionStorage.setItem('codecanopy-import', result.run_id); setRunId(result.run_id)
    } catch (e) {setError(e instanceof Error ? e.message : 'Import failed.'); setBusy(false)}
  }
  return <div className="import-page">
    <a className="skip-link" href="#import-form">Skip to import</a>
    <header className="topbar"><Link className="brand" to="/"><span className="brand-mark"><img src="/codecanopy-logo.png" alt=""/></span><span>CodeCanopy</span></Link><span className="pill active"><Icon name="upload"/> Import</span><span className="topbar-note">Your repository, a clearer view.</span><a className="btn subtle" href="https://github.com/ScientificAJ/CodeCanopy#readme" target="_blank" rel="noreferrer">Documentation <Icon name="arrow"/></a></header>
    <main className="import-main">
      <div className="import-grid">
        <section className="import-intro"><p className="eyebrow">FROM CODEBASE TO CLARITY</p><h1>Understand your repository.<br/><span>Find your path.</span></h1><p className="lead">Connect a repository, explore its structure, and open the source. A clear starting point for your next change.</p>
          <div className="import-card" id="import-form"><div className="tabs" aria-label="Import method">
            {(['github', 'zip', 'recent'] as const).map(t => <button type="button" key={t} disabled={busy} className={tab === t ? 'active' : ''} aria-pressed={tab === t} onClick={() => setTab(t)}><Icon name={t === 'github' ? 'github' : t === 'zip' ? 'upload' : 'folder'}/>{t === 'github' ? 'GitHub URL' : t === 'zip' ? 'Upload ZIP' : 'Recent'}</button>)}
          </div>
          {tab === 'recent' ? <div className="recent-list">{projects.length ? projects.map(p => <Link className="recent-item" key={p.id} to={`/p/${p.id}`}><Icon name="folder"/>{p.name}<Icon name="arrow"/></Link>) : <p>No repositories in this browser session yet.</p>}</div> : <form onSubmit={submit}>
            {tab === 'github' ? <><label htmlFor="repository-url">Public repository URL</label><div className="input-icon"><Icon name="github"/><input id="repository-url" type="url" required placeholder="https://github.com/owner/repository" value={url} disabled={busy} onChange={e => setUrl(e.target.value)}/></div><label className="ref-label" htmlFor="repository-ref">Branch, tag or commit <span>optional · default branch if empty</span></label><input id="repository-ref" placeholder="main" maxLength={256} value={ref} disabled={busy} onChange={e => setRef(e.target.value)}/></> : <><label htmlFor="repository-zip">Repository archive</label><div className="upload-zone"><Icon name="upload" size={30}/><p>Choose a ZIP to explore</p><input id="repository-zip" type="file" accept=".zip,application/zip" required disabled={busy} onChange={e => setFile(e.target.files?.[0] ?? null)}/><small>50 MiB upload · 250 MiB extracted · up to 10,000 entries</small></div></>}
            <button className="btn primary wide" type="submit" disabled={!ready || busy || (tab === 'zip' && !file)}><Icon name={busy ? 'layers' : 'spark'}/>{busy ? (run ? `${run.status} · ${run.stage ?? 'import'}` : 'Preparing import…') : 'Explore repository'}<Icon name="arrow"/></button>
          </form>}
          {busy && runId && <button type="button" className="btn subtle wide" onClick={() => cancelRun(runId).then(setRun).catch(e => setError(e.message))}>Cancel import</button>}
          {error && <p className="alert error" role="alert">{error} {!ready && 'Start the API server, then reload.'}</p>}
          {run?.status === 'cancelled' && <p role="status" className="alert">Import cancelled. You can start again.</p>}
          <p className="privacy"><Icon name="code"/>Read-only import. Source is stored on this server for 24 hours (cleanup runs every minute); you can delete it sooner. No code execution or AI calls.</p></div>
        </section>
        <aside className="import-visual" aria-label="What you can explore"><div className="mascot-halo"><img src="/codecanopy-logo.png" alt="CodeCanopy gecko"/></div><div className="preview-card"><div className="preview-title"><span className="window-dots">● ● ●</span><span>A place to get your bearings</span></div><div className="preview-body"><div className="preview-symbol"><Icon name="map" size={46}/></div><h2>See how it fits together.</h2><p>Move from folders to files with an interactive map and the original source side by side.</p><div className="feature-row"><Icon name="folder"/><span>Explore the complete file tree</span></div><div className="feature-row"><Icon name="map"/><span>Focus on one part at a time</span></div><div className="feature-row"><Icon name="code"/><span>Read source, with its exact revision</span></div><div className="feature-row"><Icon name="download"/><span>Take your map offline</span></div></div><div className="preview-foot">Your source stays unchanged.</div></div></aside>
      </div>
      <ol className="steps"><li><span>1</span><div><h3>Connect your source</h3><p>Public GitHub or a local ZIP.</p></div></li><li><span>2</span><div><h3>Explore the structure</h3><p>Search, focus, and read the source.</p></div></li><li><span>3</span><div><h3>Make it your own</h3><p>Group your view and export a map.</p></div></li></ol>
      <footer className="import-footer"><span>Built for finding your way through code.</span><span>Immutable snapshots</span><span>View-only organization</span><span>No repository code execution</span></footer>
    </main>
  </div>
}
