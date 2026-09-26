import { useCallback, useEffect, useState } from 'react'
import { useWorkspace, selectionFor } from '../../contexts/WorkspaceContext'
import { StructureMap } from '../../components/map/StructureMap'
import { renderMap } from '../../services/v1/api'
import { downloadStructuralExport } from '../../services/exportService'
import { SlotMount } from '../../components/slots/SlotMount'
import { isSlotRegistered, slotRevision, subscribeSlots } from '../../contexts/SlotRegistry'
import { useSyncExternalStore } from 'react'
import { Icon } from '../../components/ui/Icon'
import type { GraphEntity, MapArtifact } from '../../types/v1'
// INTEGRATION_SLOT: map.overlay
export default function MapPage() {
  const ws = useWorkspace()
  const [focus,setFocus] = useState(ws.preferences.focus); const [cursor,setCursor] = useState(0)
  const [artifact,setArtifact] = useState<MapArtifact | null>(null); const [error,setError] = useState(''); const [loading,setLoading] = useState(true)
  const [retry,setRetry] = useState(0); const [saving,setSaving] = useState(false); const [label,setLabel] = useState(''); const [groupName,setGroupName] = useState(''); const [members,setMembers] = useState<string[]>([])
  useSyncExternalStore(subscribeSlots,slotRevision)
  useEffect(() => {setFocus(ws.preferences.focus); setCursor(0)}, [ws.preferences.focus])
  useEffect(() => {
    const selected = ws.entities.find(e => e.id === ws.selectedEntity?.entityId)
    setLabel(selected ? ws.preferences.labels[selected.id] ?? selected.label : '')
    if (selected && !ws.graph?.entities.some(e => e.id === selected.id)) {const parent = ws.entities.find(e => e.id === selected.parent_id); setFocus(parent?.path ?? '.'); const peers = ws.entities.filter(e => e.parent_id === selected.parent_id).sort((a,b) => (ws.preferences.order === 'folders-first' ? Number(a.kind === 'file') - Number(b.kind === 'file') : 0) || a.label.toLowerCase().localeCompare(b.label.toLowerCase())); setCursor(Math.max(0, Math.floor(peers.findIndex(e => e.id === selected.id)/3)*3))}
  // Selection updates reveal the matching folder page; renderer updates must not move it again.
  }, [ws.selectedEntity?.entityId])
  useEffect(() => {
    if (!ws.projectId || !ws.snapshot) return
    const control = new AbortController(); setLoading(true); setArtifact(null); setError(''); ws.setGraph(null)
    renderMap(ws.projectId,ws.snapshot.id,focus,cursor,control.signal).then(result => {if (!control.signal.aborted) {setArtifact(result); ws.setGraph(result.graph); setLoading(false)}}).catch(e => {if (!control.signal.aborted) {setError(e.message); setLoading(false)}})
    return () => control.abort()
  }, [ws.projectId,ws.snapshot?.id,ws.preferences,focus,cursor,retry,ws.setGraph])
  const select = useCallback((entity: GraphEntity) => ws.selectEntity(selectionFor(entity)), [ws.selectEntity])
  const open = useCallback((entity: GraphEntity) => {ws.selectEntity(selectionFor(entity)); if (entity.kind !== 'file') {setFocus(entity.path ?? entity.id); setCursor(0); void ws.updatePreferences({...ws.preferences,focus: entity.path ?? entity.id}).catch(e => setError(e.message))}}, [ws.selectEntity,ws.updatePreferences,ws.preferences])
  async function save(update: Partial<typeof ws.preferences>) {setSaving(true); setError(''); try {await ws.updatePreferences({...ws.preferences,...update})} catch(e) {setError(e instanceof Error ? e.message : 'Unable to save view.')} finally {setSaving(false)}}
  const graph = artifact?.graph
  return <section className="map-page card"><div className="map-header"><div><h2>Repository map</h2><span className="muted">Structure · observed containment</span></div><button className="btn small" disabled={!artifact || loading} onClick={() => artifact && downloadStructuralExport(artifact).catch(e => setError(e.message))}><Icon name="download"/> Export HTML</button></div>
    <div className="map-breadcrumb"><button className="btn small" onClick={() => {setFocus('.'); setCursor(0)}}>Repository</button><span>/</span><strong title={focus}>{ws.preferences.groups.find(g => g.id === focus)?.label ?? (focus === '.' ? 'All folders' : focus)}</strong>{focus !== '.' && <button className="btn small" onClick={() => {setFocus(focus.includes('/') ? focus.slice(0,focus.lastIndexOf('/')) : '.'); setCursor(0)}}>Up one level</button>}</div>
    <details className="view-settings"><summary>Customize view <span className="muted">Labels, groups & appearance</span></summary><div className="settings-grid"><label>Theme<select value={ws.preferences.theme} disabled={saving} onChange={e => void save({theme: e.target.value as 'light' | 'dark'})}><option value="light">Light</option><option value="dark">Dark</option></select></label><label>Layout order<select value={ws.preferences.order} disabled={saving} onChange={e => {setCursor(0); void save({order: e.target.value as 'folders-first' | 'alphabetical'})}}><option value="folders-first">Folders first</option><option value="alphabetical">Alphabetical</option></select></label></div>
      <form className="inline-form" onSubmit={e => {e.preventDefault(); if (ws.selectedEntity) void save({labels: {...ws.preferences.labels,[ws.selectedEntity.entityId]: label}})}}><label>Selected entity label<input value={label} maxLength={60} disabled={!ws.selectedEntity || saving} placeholder="Select an entity first" onChange={e => setLabel(e.target.value)}/></label><button className="btn small" disabled={!ws.selectedEntity || !label.trim() || saving}>Save label</button></form>
      <form onSubmit={e => {e.preventDefault(); void save({groups: [...ws.preferences.groups,{id: 'group_' + crypto.randomUUID(),label: groupName.trim(),members}]}).then(() => {setGroupName(''); setMembers([])})}}><label>New virtual group<input value={groupName} maxLength={60} placeholder="e.g. Reading list" onChange={e => setGroupName(e.target.value)}/></label><div className="member-options">{graph?.entities.filter(e => e.kind !== 'virtual_group').map(e => <label key={e.id}><input type="checkbox" checked={members.includes(e.id)} onChange={() => setMembers(m => m.includes(e.id) ? m.filter(id => id !== e.id) : [...m,e.id])}/>{e.label}</label>)}</div><button className="btn small" disabled={!groupName.trim() || !members.length || saving}>Create group from selected members</button></form>
      {ws.preferences.groups.map(group => <div className="group-row" key={group.id}><button className="btn small" onClick={() => {setFocus(group.id); setCursor(0)}}>{group.label} · {group.members.length}</button><button className="btn small" disabled={!ws.selectedEntity || ws.selectedEntity.kind === 'virtual_group' || group.members.includes(ws.selectedEntity.entityId) || saving} onClick={() => void save({groups: ws.preferences.groups.map(g => g.id === group.id ? {...g,members: [...g.members,ws.selectedEntity!.entityId]} : g)})}>Add selected entity</button><button className="btn small" aria-label={`Remove group ${group.label}`} onClick={() => {if(focus === group.id) setFocus('.'); void save({focus: ws.preferences.focus === group.id ? '.' : ws.preferences.focus,groups: ws.preferences.groups.filter(g => g.id !== group.id)})}}>Remove</button></div>)}
      <p className="muted">Preferences belong to this snapshot. Source paths and contents stay unchanged.</p><button className="btn small" disabled={saving} onClick={() => {setFocus('.'); setCursor(0); void save({labels: {},groups: [],theme: 'light',order: 'folders-first',focus: '.'})}}>Reset view preferences</button>
    </details>
    {loading && <div className="map-loading" role="status"><span className="spinner"/>Rendering your structure with Archify…</div>}{error && <div className="alert error" role="alert">{error}<button className="btn small" onClick={() => setRetry(n => n+1)}>Retry map</button></div>}
    {artifact && <><StructureMap artifact={artifact} selectedId={ws.selectedEntity?.entityId} onSelect={select} onOpen={open}/><div className="map-paging"><button className="btn small" disabled={cursor === 0} onClick={() => setCursor(Math.max(0,cursor-3))}>Previous</button><span>{graph!.child_total ? `${cursor+1}–${Math.min(cursor+3,graph!.child_total)} of ${graph!.child_total} children` : 'No children in this view'}</span><button className="btn small" disabled={graph!.next_cursor === null} onClick={() => setCursor(graph!.next_cursor!)}>Next</button></div><div className="map-entity-list" aria-label="Entities in map">{graph!.entities.map(entity => <div key={entity.id}><button className={`entity-button ${ws.selectedEntity?.entityId === entity.id ? 'selected' : ''}`} onClick={() => select(entity)}><Icon name={entity.kind === 'file' ? 'file' : 'folder'}/><span>{entity.label}</span><small>{entity.kind.replace('_',' ')}</small></button>{entity.kind !== 'file' && <button className="icon-btn" aria-label={`Open ${entity.label}`} onClick={() => open(entity)}><Icon name="arrow"/></button>}</div>)}</div><p className="map-disclosure">{graph!.coverage.inventoried_files} inventoried files · This chapter shows {graph!.entities.length} entities. Explore folders or use the complete tree. HTML exports this view, its provenance and preferences; source code is excluded.</p></>}
    {isSlotRegistered('map.overlay') && <SlotMount id="map.overlay"/>}
  </section>
}
