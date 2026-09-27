import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useWorkspace, selectionFor } from '../../contexts/WorkspaceContext'
import { StructureMap } from '../../components/map/StructureMap'
import { GroupEditor } from '../../components/map/GroupEditor'
import { renderMap } from '../../services/v1/api'
import { downloadStructuralExport } from '../../services/exportService'
import { SlotMount } from '../../components/slots/SlotMount'
import { isSlotRegistered, slotRevision, subscribeSlots } from '../../contexts/SlotRegistry'
import { Icon } from '../../components/ui/Icon'
import { ChatButton } from '../../components/ui/ChatButton'
import type { GraphEntity, MapArtifact } from '../../types/v1'
// INTEGRATION_SLOT: map.overlay
export default function MapPage() {
  const ws = useWorkspace(); const location = useLocation(); const navigate = useNavigate()
  const container = useRef<HTMLElement>(null); const [width,setWidth] = useState(0)
  const params = new URLSearchParams(location.search)
  const focus = params.get('focus') ?? ws.preferences.focus
  const rawCursor = Number(params.get('page') ?? 0)
  const pageSize:3|8 = ws.preferences.density === 'comfortable' || (ws.preferences.density !== 'expanded' && width < 640) ? 3 : 8
  const cursor = Number.isSafeInteger(rawCursor) && rawCursor >= 0 && rawCursor <= 10000 ? Math.floor(rawCursor/pageSize)*pageSize : 0
  const [artifact,setArtifact] = useState<MapArtifact|null>(null); const [error,setError] = useState(''); const [loading,setLoading] = useState(true)
  const [retry,setRetry] = useState(0); const [saving,setSaving] = useState(false); const [label,setLabel] = useState('')
  const lastSelection = useRef<string|undefined>(undefined)
  const selectionKey = (id:string,range?:{start:number;end:number}) => `${id}:${range?.start??''}:${range?.end??''}`
  const historyRestored = useRef<string>('')
  useSyncExternalStore(subscribeSlots,slotRevision)
  useEffect(() => {const element=container.current;if(!element)return; const resize=new ResizeObserver(entries => setWidth(entries[0].contentRect.width));resize.observe(element);return () => resize.disconnect()}, [])
  function go(nextFocus:string,nextCursor=0,node?:string,replace=false) {
    const range=node===ws.selectedEntity?.entityId?ws.selectedEntity?.lineRange:undefined
    const search=new URLSearchParams({focus:nextFocus,page:String(nextCursor),...(node ? {node} : {}),...(range?{start:String(range.start),end:String(range.end)}:{})})
    navigate({pathname:location.pathname,search:'?'+search.toString()},{replace,state:replace?{mapHistoryKey:location.state?.mapHistoryKey??location.key}:undefined})
  }
  useEffect(() => {try {sessionStorage.setItem(`codecanopy-map:${ws.snapshot?.id}`,new URLSearchParams({focus,page:String(cursor),...(ws.selectedEntity?{node:ws.selectedEntity.entityId}:{}),...(ws.selectedEntity?.lineRange?{start:String(ws.selectedEntity.lineRange.start),end:String(ws.selectedEntity.lineRange.end)}:{})}).toString())}catch{/* Optional browser persistence. */}},[focus,cursor,ws.snapshot?.id,ws.selectedEntity?.entityId,ws.selectedEntity?.lineRange?.start,ws.selectedEntity?.lineRange?.end])
  useEffect(() => {setLabel(ws.selectedEntity ? ws.preferences.labels[ws.selectedEntity.entityId] ?? ws.entities.find(e=>e.id===ws.selectedEntity?.entityId)?.label ?? '' : '')},[ws.selectedEntity?.entityId,ws.preferences.labels])
  useEffect(() => {
    if (historyRestored.current === location.key) return
    historyRestored.current=location.key
    const query = new URLSearchParams(location.search)
    const id = query.get('node')
    const entity = ws.entities.find(e => e.id === id)
    const start=Number(query.get('start')),end=Number(query.get('end'))
    const range=Number.isSafeInteger(start)&&Number.isSafeInteger(end)&&start>=1&&end>=start?{start,end}:undefined
    if(entity){lastSelection.current=selectionKey(entity.id,range);if(ws.selectedEntity?.entityId!==entity.id||ws.selectedEntity?.lineRange?.start!==range?.start||ws.selectedEntity?.lineRange?.end!==range?.end)ws.selectEntity({...selectionFor(entity),lineRange:range})}
  },[location.key,location.search,ws.entities,ws.selectEntity])
  useEffect(() => {
    const id=ws.selectedEntity?.entityId
    if(!id)return
    const key=selectionKey(id,ws.selectedEntity?.lineRange)
    if(lastSelection.current===key)return
    lastSelection.current=key
    const selected=ws.entities.find(e => e.id===id)
    setLabel(selected ? ws.preferences.labels[id] ?? selected.label : '')
    if(!selected)return
    if(artifact?.graph.entities.some(e=>e.id===id)){go(focus,cursor,id,true);return}
    const parent=ws.entities.find(e=>e.id===selected.parent_id)
    const peers=ws.entities.filter(e=>e.parent_id===selected.parent_id).sort((a,b)=>(ws.preferences.order==='folders-first'?Number(a.kind==='file')-Number(b.kind==='file'):0)||a.label.toLowerCase().localeCompare(b.label.toLowerCase())||a.id.localeCompare(b.id))
    go(parent?.path ?? '.',Math.max(0,Math.floor(peers.findIndex(e=>e.id===id)/pageSize)*pageSize),id,true)
  },[ws.selectedEntity?.entityId,ws.selectedEntity?.lineRange?.start,ws.selectedEntity?.lineRange?.end])
  useEffect(() => {
    if(!ws.projectId || !ws.snapshot || !width)return
    const control=new AbortController();setLoading(true);setArtifact(null);setError('');ws.setGraph(null)
    renderMap(ws.projectId,ws.snapshot.id,focus,cursor,control.signal,pageSize).then(result=>{if(!control.signal.aborted){setArtifact(result);ws.setGraph(result.graph);setLoading(false)}}).catch(e=>{if(!control.signal.aborted){setError(e.message);setLoading(false)}})
    return ()=>control.abort()
  },[ws.projectId,ws.snapshot?.id,ws.preferences,focus,cursor,pageSize,Boolean(width),retry,ws.setGraph])
  const select=useCallback((entity:GraphEntity)=>ws.selectEntity(selectionFor(entity)),[ws.selectEntity])
  function open(entity:GraphEntity) {lastSelection.current=selectionKey(entity.id);ws.selectEntity(selectionFor(entity));if(entity.kind!=='file')go(entity.path ?? entity.id,0,entity.id)}
  async function save(update:Partial<typeof ws.preferences>) {setSaving(true);setError('');try{await ws.updatePreferences({...ws.preferences,...update})}catch(e){setError(e instanceof Error?e.message:'Unable to save view.')}finally{setSaving(false)}}
  const graph=artifact?.graph
  return <section ref={container} className="map-page card"><div className="map-header"><div><h2>Repository map</h2><span className="muted">Structure · observed containment</span></div><div className="map-header-actions"><ChatButton label="Code Canopy Chat"/><button className="btn small" disabled={!artifact||loading} onClick={()=>artifact&&downloadStructuralExport(artifact).catch(e=>setError(e.message))}><Icon name="download"/>Export HTML</button></div></div>
    <div className="map-breadcrumb"><button className="btn small" onClick={()=>go('.')}>Repository</button><span>/</span><strong title={focus}>{ws.preferences.groups.find(g=>g.id===focus)?.label??(focus==='.'?'All folders':focus)}</strong>{focus!=='.'&&<button className="btn small" onClick={()=>go(focus.includes('/')?focus.slice(0,focus.lastIndexOf('/')):'.')}>Up one level</button>}</div>
    <details className="view-settings"><summary>Customize view <span className="muted">Labels, groups & appearance</span></summary><div className="settings-grid"><label>Theme<select value={ws.preferences.theme} disabled={saving} onChange={e=>void save({theme:e.target.value as 'light'|'dark'})}><option value="light">Light</option><option value="dark">Dark</option></select></label><label>Layout order<select value={ws.preferences.order} disabled={saving} onChange={e=>{go(focus);void save({order:e.target.value as 'folders-first'|'alphabetical'})}}><option value="folders-first">Folders first</option><option value="alphabetical">Alphabetical</option></select></label><label>Map density<select value={ws.preferences.density??'auto'} disabled={saving} onChange={e=>{go(focus);void save({density:e.target.value as 'auto'|'comfortable'|'expanded'})}}><option value="auto">Automatic · fits available space</option><option value="comfortable">Comfortable · 3 children</option><option value="expanded">Expanded · 8 children</option></select></label></div>
      <form className="inline-form" onSubmit={e=>{e.preventDefault();if(ws.selectedEntity)void save({labels:{...ws.preferences.labels,[ws.selectedEntity.entityId]:label.trim()}})}}><label>Selected entity label<input value={label} maxLength={60} disabled={!ws.selectedEntity||saving} placeholder="Select an entity first" onChange={e=>setLabel(e.target.value)}/></label><button className="btn small" disabled={!ws.selectedEntity||!label.trim()||saving}>Save label</button></form>
      <GroupEditor entities={ws.entities} preferences={ws.preferences} save={ws.updatePreferences} focus={id=>go(id)}/>
      <p className="muted">Preferences belong to this snapshot. Source paths and contents stay unchanged.</p><button className="btn small" disabled={saving} onClick={()=>{go('.');void save({labels:{},groups:[],theme:'light',order:'folders-first',focus:'.',density:'auto'})}}>Reset view preferences</button>
    </details>
    {loading&&<div className="map-loading" role="status"><span className="spinner"/>Rendering your structure with Archify…</div>}{error&&<div className="alert error" role="alert">{error}<button className="btn small" onClick={()=>setRetry(n=>n+1)}>Retry map</button><button className="btn small" onClick={()=>go('.')}>Return to repository</button></div>}
    {artifact&&<><StructureMap artifact={artifact} selectedId={ws.selectedEntity?.entityId} onSelect={select} onOpen={open} historyKey={location.state?.mapHistoryKey??location.key}/><div className="map-paging"><button className="btn small" disabled={cursor===0} onClick={()=>go(focus,Math.max(0,cursor-pageSize))}>Previous</button><span>{graph!.child_total?`${cursor+1}–${Math.min(cursor+pageSize,graph!.child_total)} of ${graph!.child_total} children`:'No children in this view'}</span><button className="btn small" disabled={graph!.next_cursor===null} onClick={()=>go(focus,graph!.next_cursor!)}>Next</button></div><div className="map-entity-list" aria-label="Entities in map">{graph!.entities.map((entity,i)=><div key={entity.id}><button className={`entity-button ${ws.selectedEntity?.entityId===entity.id?'selected':''}`} onClick={()=>select(entity)}><Icon name={entity.kind==='file'?'file':'folder'}/><span>{entity.label}</span><small>{i?graph!.relations[0]?.kind==='groups'?'member':'contains':entity.kind.replace('_',' ')}</small></button>{entity.kind!=='file'&&<button className="icon-btn" aria-label={`Open ${entity.label}`} onClick={()=>open(entity)}><Icon name="arrow"/></button>}</div>)}</div><p className="map-disclosure">{graph!.coverage.inventoried_files} inventoried files · {graph!.entities.length} entities in this view. Arrows mean {graph!.relations[0]?.kind==='groups'?'explicit group membership':'folder containment'}. Export saves this view to your device, with provenance and preferences; it includes no source excerpts.</p></>}
    {isSlotRegistered('map.overlay')&&<SlotMount id="map.overlay"/>}
  </section>
}
