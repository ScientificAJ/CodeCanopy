import { Component, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkspace, selectionFor } from '../../contexts/WorkspaceContext'
import { getSlot, slotRevision, subscribeSlots, type RequestState, type SlotContext, type SlotId } from '../../contexts/SlotRegistry'
import { Icon } from '../ui/Icon'
export const slotNames: Record<SlotId, string> = {'summaries.context-panel': 'File & folder summaries', 'dependencies.workspace': 'Dependencies & change impact', 'reuse.findings': 'Reusable code', 'duplicates.compare': 'Duplicate code', 'unused.review': 'Unused code', 'ask.workspace': 'Ask CodeCanopy', 'proposals.detail': 'Proposals & change packs', 'docs.generated': 'Generated documentation', 'map.overlay': 'Map insights'}
export function Unavailable({id, message}: {id: SlotId; message?: string}) {
  return <section className="slot-placeholder" aria-label={slotNames[id]}><div className="slot-icon"><Icon name="spark" size={24}/></div><span className="badge">Not connected</span><h2>{slotNames[id]}</h2><p>{message ?? 'This feature is not connected in this workspace yet. You can explore the repository map and read source files now.'}</p><details><summary>Integration details</summary><p>Extension: <code>{id}</code></p><p>Register a component and optional data adapter through SlotRegistry. See INTEGRATION_GUIDE.md.</p></details></section>
}
class Boundary extends Component<{children: ReactNode; id: SlotId}, {failed: boolean}> {
  state = {failed: false}
  static getDerivedStateFromError() {return {failed: true}}
  render() {return this.state.failed ? <Unavailable id={this.props.id} message="This extension could not be displayed. The repository and source browser are still available."/> : this.props.children}
}
export function SlotMount({id}: {id: SlotId}) {
  const ws = useWorkspace(); const navigate = useNavigate()
  useSyncExternalStore(subscribeSlots, slotRevision)
  const feature = getSlot(id)
  const [request, setRequest] = useState<RequestState>({status: 'idle'})
  const context = useMemo<SlotContext | null>(() => !ws.projectId || !ws.snapshot ? null : ({
    projectId: ws.projectId, snapshotId: ws.snapshot.id, snapshot: ws.snapshot, selectedEntity: ws.selectedEntity,
    files: ws.files, entities: ws.entities, graph: ws.graph, capabilities: ws.capabilities, viewState: ws.viewState,
    selectEntity: ws.selectEntity, navigate,
    openSource(fileId, range) {
      const entity = ws.entities.find(e => e.file_id === fileId)
      if (!entity || (range && (range.start < 1 || range.end < range.start || !Number.isInteger(range.start) || !Number.isInteger(range.end)))) return
      ws.selectEntity({...selectionFor(entity), lineRange: range}); navigate(`/p/${ws.projectId}/s/${ws.snapshot!.id}/map`)
    },
  }), [ws.projectId, ws.snapshot, ws.selectedEntity, ws.files, ws.entities, ws.graph, ws.capabilities, ws.viewState, ws.selectEntity, navigate])
  useEffect(() => {
    const controller = new AbortController()
    setRequest({status: 'idle'})
    if (context && feature?.load && (feature.availability ?? 'connected') === 'connected') {
      setRequest({status: 'loading'})
      feature.load(context, controller.signal).then(data => {if (!controller.signal.aborted) setRequest({status: 'ready', data})}).catch(e => {if (!controller.signal.aborted) setRequest({status: 'error', message: e instanceof Error ? e.message : 'Extension request failed.'})})
    }
    return () => controller.abort()
  }, [feature, context])
  if (!feature || !context || feature.availability === 'not-connected' || feature.availability === 'unavailable') return <Unavailable id={id}/>
  const View = feature.Component
  return <Boundary key={`${id}:${ws.snapshot?.id}`} id={id}><View {...context} availability="connected" request={request}/></Boundary>
}
