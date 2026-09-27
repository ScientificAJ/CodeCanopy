import { useEffect, useMemo, useRef, useState } from 'react'
import type { GraphEntity, MapArtifact } from '../../types/v1'
import { readCamera, saveCamera, validCamera, type MapCamera } from './camera'
export interface BridgeMessage {channel:'codecanopy-archify'; version:'1.1'; nonce:string; snapshotId:string; viewId:string; type:'ready'|'select'|'open'|'camera'; entityId?:string; camera?:MapCamera}
export function validBridge(data: unknown, nonce: string, artifact: MapArtifact): data is BridgeMessage {
  if (!data || typeof data !== 'object') return false
  const m = data as BridgeMessage
  return m.channel === 'codecanopy-archify' && m.version === '1.1' && m.nonce === nonce && m.snapshotId === artifact.graph.snapshot_id && m.viewId === artifact.view_id && (m.type === 'ready' || (m.type === 'camera' && validCamera(m.camera)) || ((m.type === 'select' || m.type === 'open') && artifact.graph.entities.some(e => e.id === m.entityId)))
}
export function StructureMap({artifact,selectedId,onSelect,onOpen,historyKey='default'}: {artifact:MapArtifact; selectedId?:string; onSelect(entity:GraphEntity):void; onOpen(entity:GraphEntity):void; historyKey?:string}) {
  const frame = useRef<HTMLIFrameElement>(null); const [ready,setReady] = useState(false)
  const callbacks = useRef({onSelect,onOpen}); callbacks.current = {onSelect,onOpen}
  const nonce = useMemo(() => crypto.randomUUID(), [artifact.view_id,historyKey])
  const storageKey = `codecanopy-camera:${artifact.graph.snapshot_id}:${historyKey}:${artifact.view_id}`
  const restored = useRef(false)
  const latestKey = `codecanopy-camera:${artifact.graph.snapshot_id}:latest:${artifact.view_id}`
  const initialCamera = useMemo(() => readCamera(storageKey) ?? readCamera(latestKey), [storageKey,latestKey])
  function send(type:string, entityId?:string, camera?:MapCamera) {frame.current?.contentWindow?.postMessage({channel:'codecanopy-archify',version:'1.1',nonce,snapshotId:artifact.graph.snapshot_id,viewId:artifact.view_id,type,entityId,camera},'*')}
  useEffect(() => {
    setReady(false); restored.current = false
    function receive(event:MessageEvent) {
      if (event.source !== frame.current?.contentWindow || !validBridge(event.data,nonce,artifact)) return
      if (event.data.type === 'ready') setReady(true)
      else if (event.data.type === 'camera' && event.data.camera) {saveCamera(storageKey,event.data.camera);saveCamera(latestKey,event.data.camera)}
      else {const entity = artifact.graph.entities.find(e => e.id === event.data.entityId); if (entity) (event.data.type === 'open' ? callbacks.current.onOpen : callbacks.current.onSelect)(entity)}
    }
    window.addEventListener('message',receive); return () => window.removeEventListener('message',receive)
  }, [artifact,nonce,storageKey,latestKey])
  useEffect(() => {
    if (!ready) return
    if (selectedId) send('select',selectedId)
    if (!restored.current) {restored.current = true; if(initialCamera) send('restore-camera',undefined,initialCamera)}
  }, [ready,selectedId,nonce,initialCamera])
  return <div className="structure-map"><div className="map-camera" aria-label="Map camera controls"><button className="btn small" aria-label="Zoom in" disabled={!ready} onClick={() => send('zoom-in')}>＋</button><button className="btn small" aria-label="Zoom out" disabled={!ready} onClick={() => send('zoom-out')}>−</button><button className="btn small" disabled={!ready} onClick={() => send('fit')}>Fit</button><button className="btn small" disabled={!ready} onClick={() => send('reset')}>Reset</button></div><iframe key={nonce} ref={frame} title="Repository structure map" sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={artifact.html} onLoad={() => send('init')}/></div>
}
