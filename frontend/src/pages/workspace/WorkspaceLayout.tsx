// INTEGRATION_SLOT: summaries.context-panel
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate, useParams } from 'react-router-dom'
import { RepositoryTree } from '../../components/tree/RepositoryTree'
import { WorkspaceProvider, useWorkspace, selectionFor } from '../../contexts/WorkspaceContext'
import { ensureSession, listSnapshots, listProjects, deleteProject } from '../../services/v1/api'
import { SourceViewer } from '../../components/source/SourceViewer'
import { SlotMount } from '../../components/slots/SlotMount'
import type { V1Project } from '../../types/v1'
import { usePanelFocus } from '../../hooks/usePanelFocus'
import { Icon, type IconName } from '../../components/ui/Icon'
const items: [string, string, IconName][] = [['overview','Overview','home'],['map','Architecture','map'],['dependencies','Dependencies','layers'],['opportunities/reuse','Reusable Code','code'],['opportunities/duplicates','Issues','layers'],['ask','AI Chat','spark'],['proposals','Proposals','file'],['docs','Documentation','file']]
function Inner() {
  const {projectId = '', snapshotId = ''} = useParams(); const ws = useWorkspace(); const navigate = useNavigate()
  const [drawer, setDrawer] = useState<'navigation' | 'files' | 'context' | null>(null)
  const [projects, setProjects] = useState<V1Project[]>([])
  const [expandSource, setExpandSource] = useState(false); const [deleteError, setDeleteError] = useState('')
  const search = useRef<HTMLInputElement>(null)
  usePanelFocus(drawer, expandSource)
  const base = `/p/${projectId}/s/${snapshotId}`
  useEffect(() => {void ensureSession().then(() => ws.loadWorkspace(projectId, snapshotId))}, [projectId, snapshotId, ws.loadWorkspace])
  useEffect(() => {let live = true; ensureSession().then(listProjects).then(items => {if (live) setProjects(items)}).catch(() => {}); return () => {live = false}}, [projectId])
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {event.preventDefault(); setDrawer('files'); setTimeout(() => search.current?.focus(), 0)}
      if (event.key === 'Escape') {setDrawer(null); setExpandSource(false)}
    }
    window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key)
  }, [])
  const file = ws.files.find(f => f.id === ws.selectedEntity?.fileId)
  const entity = ws.entities.find(e => e.id === ws.selectedEntity?.entityId)
  const revision = ws.snapshot?.source.resolved_commit ?? ws.snapshot?.source.archive_digest
  const languages = new Set(ws.files.map(f => f.language).filter(l => l !== 'unknown')).size
  return <div className="workspace-app"><a className="skip-link" href="#main-content">Skip to content</a>
    <header className="topbar"><Link className="brand" to="/"><span className="brand-mark"><img src="/codecanopy-logo.png" alt=""/></span><span>CodeCanopy</span></Link><div className="project-chip"><Icon name={ws.snapshot?.source.kind === 'github' ? 'github' : 'folder'}/><select aria-label="Select repository" value={projectId} onChange={event => navigate(`/p/${event.target.value}`)}>{projects.length ? projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>) : <option value={projectId}>{ws.projectName ?? 'Repository'}</option>}</select><span className="badge">{ws.snapshot?.source.kind === 'github' ? 'Public' : 'ZIP'}</span></div><button className="global-search" onClick={() => {setDrawer('files'); setTimeout(() => search.current?.focus(), 0)}}><Icon name="search"/><span>Search repository files…</span><kbd>⌘ K</kbd></button><Link className="btn primary" to="/"><Icon name="upload"/> New import</Link></header>
    <div className="mobile-tools"><button className="btn" onClick={() => setDrawer('navigation')}><Icon name="menu"/>Navigate</button><button className="btn" onClick={() => setDrawer('files')}><Icon name="folder"/>Files</button><button className="btn" onClick={() => setDrawer('context')}><Icon name="code"/>Context</button></div>
    {drawer && <button className="drawer-scrim" aria-label="Close panel" onClick={() => setDrawer(null)}/>}
    <div className="workspace-grid">
      <nav className={`nav-rail ${drawer === 'navigation' ? 'drawer-open' : ''}`} aria-label="Workspace navigation"><button className="drawer-close btn" onClick={() => setDrawer(null)}><Icon name="close"/>Close</button>{items.map(([path,label,icon]) => <NavLink key={path} to={`${base}/${path}`} className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setDrawer(null)}><Icon name={icon}/>{label}</NavLink>)}</nav>
      <div className="workspace-main">
        <section className="repo-header"><div><p className="eyebrow">REPOSITORY WORKSPACE</p><h1>{ws.projectName ?? (ws.loading ? 'Opening repository…' : 'Repository unavailable')}</h1>{ws.run?.status === 'partial' && <span className="badge partial">Partial import · {ws.run.diagnostics.length} diagnostics</span>}<p className="revision">{revision ? `Revision ${revision.slice(0, 12)} · read-only snapshot` : 'Loading snapshot identity…'}</p></div><div className="repo-stats"><div><strong>{ws.files.length}</strong><span>Files</span></div><div><strong>{languages}</strong><span>Languages</span></div><div><strong>{ws.capabilities?.parsed_count ?? '—'}</strong><span>Syntax parsed</span></div></div></section>
        {ws.error ? <main className="card" id="main-content"><h2>Unable to open this snapshot</h2><p role="alert">{ws.error}</p><Link className="btn primary" to="/">Return to import</Link></main> : <div className="workspace-panels">
          <aside className={`tree-panel card ${drawer === 'files' ? 'drawer-open' : ''}`} aria-label="Project structure"><button className="drawer-close btn" onClick={() => setDrawer(null)}><Icon name="close"/>Close</button>{ws.loading ? <p className="pad" role="status">Loading inventory…</p> : <RepositoryTree entities={ws.entities} selectedId={ws.selectedEntity?.entityId} searchRef={search} onSelect={e => {ws.selectEntity(selectionFor(e)); setDrawer(null)}} onOpen={e => {ws.selectEntity(selectionFor(e)); if (e.kind !== 'file') void ws.updatePreferences({...ws.preferences, focus: e.path ?? '.'}); navigate(base + '/map'); setDrawer(null)}}/>}</aside>
          <main className="content-area" id="main-content">{ws.loading ? <div className="card loading" role="status">Building your workspace…</div> : <Outlet/>}</main>
          <aside className={`context-panel card ${drawer === 'context' || expandSource ? 'drawer-open' : ''} ${expandSource ? 'source-expanded' : ''}`} aria-label="Selected source and context"><div className="context-title"><h2>{file ? 'Source preview' : 'Repository context'}</h2><button className="icon-btn" aria-label={expandSource ? 'Close expanded source' : 'Expand context'} onClick={() => setExpandSource(!expandSource)}>{expandSource ? <Icon name="close"/> : '⤢'}</button></div><button className="drawer-close btn" onClick={() => setDrawer(null)}>Close</button>
            {file ? <><div className="source-identity"><strong>{file.path}</strong><span className="badge">{ws.capabilities?.files.find(f => f.file_id === file.id)?.syntax_extraction ? 'Syntax extracted' : file.excluded ? 'Excluded' : file.is_text ? 'Text only' : 'Binary'}</span><small>{file.size.toLocaleString()} bytes · SHA-256 {file.content_hash.slice(0,12)}</small></div><SourceViewer key={`${snapshotId}:${file.id}`} projectId={projectId} snapshotId={snapshotId} fileId={file.id} path={file.path} language={file.language} lineStart={ws.selectedEntity?.lineRange?.start} lineEnd={ws.selectedEntity?.lineRange?.end}/></> : <div className="context-body"><div className="context-callout"><Icon name="folder" size={26}/><h3>{entity?.label ?? 'Explore your repository'}</h3><p>{entity ? `${entity.child_count} direct children. Double-click a folder to focus its map.` : 'Select a file or folder in the tree or map to see its context here.'}</p></div><h3>What this map shows</h3><p>The structure map shows folder membership in this snapshot. The Dependencies view shows supported static imports and function calls, with source evidence and coverage limits.</p><div className="coverage-list"><span>Syntax parsed <b>{ws.capabilities?.parsed_count ?? 0}</b></span><span>Text only <b>{ws.capabilities?.text_only_count ?? 0}</b></span><span>Binary / unsupported encoding <b>{ws.capabilities?.binary_count ?? 0}</b></span><span>Excluded by source policy <b>{ws.capabilities?.excluded_count ?? 0}</b></span></div></div>}
            {file && ws.capabilities?.files.find(cap => cap.file_id === file.id)?.limitations.map((limitation,index) => <p key={index} className="file-limitation">{limitation}</p>)}
            {ws.run && ws.run.diagnostics.length > 0 && <details className="import-diagnostics"><summary>Import diagnostics ({ws.run.diagnostics.length})</summary>{ws.run.diagnostics.slice(0,50).map((item,index) => <p key={index}><strong>{item.file_path ?? item.stage}</strong><br/>{item.message}</p>)}{ws.run.diagnostics.length > 50 && <p>Select individual files for remaining capability details.</p>}</details>}
            <div className="context-slot"><SlotMount id="summaries.context-panel"/></div>
            <details className="storage-details"><summary>Snapshot storage</summary><p>Accessible until {ws.snapshot?.expires_at ? new Date(ws.snapshot.expires_at).toLocaleString() : 'expiry'}. Only this browser session can access this workspace. Source is stored on the API server.</p><p>Known secret filenames and private keys are excluded; this is not a complete secret detector.</p><button className="btn danger" onClick={async () => {if (!window.confirm('Delete this imported repository and its stored source?')) return; try {await deleteProject(projectId); navigate('/')} catch(e) {setDeleteError(e instanceof Error ? e.message : 'Delete failed.')}}}>Delete imported repository</button>{deleteError && <p role="alert">{deleteError}</p>}</details>
          </aside>
        </div>}
      </div>
    </div>
  </div>
}
export function WorkspaceLayout() {return <WorkspaceProvider><Inner/></WorkspaceProvider>}
export function ProjectRoot() {
  const {projectId = ''} = useParams(); const navigate = useNavigate(); const [error, setError] = useState('')
  useEffect(() => {const control = new AbortController(); ensureSession().then(() => listSnapshots(projectId, control.signal)).then(s => {if (control.signal.aborted) return; if (!s.length) setError('No completed snapshots were found.'); else navigate(`/p/${projectId}/s/${s.at(-1)!.id}/overview`, {replace: true})}).catch(e => {if (!control.signal.aborted) setError(e.message)}); return () => control.abort()}, [projectId,navigate])
  return <main className="standalone card"><h1>{error ? 'Repository unavailable' : 'Opening repository…'}</h1>{error && <><p role="alert">{error}</p><Link to="/">Return to import</Link></>}</main>
}
