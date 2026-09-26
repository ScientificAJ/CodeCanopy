import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { cancelRun, ensureSession, getRun, importGitHub } from '../services/v1/api'
import type { AnalysisRun } from '../types/v1'
export default function ImportPage() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [ready, setReady] = useState(false); const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [runId, setRunId] = useState<string | null>(() => sessionStorage.getItem('codecanopy-import'))
  const [run, setRun] = useState<AnalysisRun | null>(null)
  useEffect(() => { let live = true; ensureSession().then(() => {if (live) setReady(true)}).catch(e => {if (live) setError(e.message)}); return () => {live = false} }, [])
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
      const result = await importGitHub({url: url.trim(), ref: 'HEAD'})
      sessionStorage.setItem('codecanopy-import', result.run_id); setRunId(result.run_id)
    } catch (e) {setError(e instanceof Error ? e.message : 'Import failed.'); setBusy(false)}
  }
  return <div className="import-page codecanopy-import">
    <a className="skip-link" href="#import-form">Skip to import</a>
    <header className="topbar codecanopy-topbar"><Link className="brand" to="/"><span className="brand-mark"><img src="/codecanopy-logo.png" alt=""/></span><span>CodeCanopy</span></Link></header>
    <main className="codecanopy-import-main">
      <section className="codecanopy-import-content">
        <img className="codecanopy-mascot" src="/codecanopy-logo.png" alt="CodeCanopy gecko"/>
        <h1>Copy a GitHub repo link, paste it here, and summarize.</h1>
        <form className="codecanopy-form" id="import-form" onSubmit={submit}>
          <label className="sr-only" htmlFor="repository-url">GitHub repository URL</label>
          <input id="repository-url" type="url" required placeholder="https://github.com/owner/repository" value={url} disabled={busy} onChange={event => setUrl(event.target.value)}/>
          <button className="btn primary" type="submit" disabled={!ready || busy}>{busy ? (run?.stage ? `${run.stage}…` : 'Summarizing…') : 'Summarize'}</button>
        </form>
        {busy && runId && <button type="button" className="codecanopy-cancel" onClick={() => cancelRun(runId).then(setRun).catch(error => setError(error.message))}>Cancel</button>}
        {error && <p className="alert error" role="alert">{error}</p>}
        {run?.status === 'cancelled' && <p role="status" className="alert">Summarization cancelled.</p>}
      </section>
    </main>
  </div>
}
