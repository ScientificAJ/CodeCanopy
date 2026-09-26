import { useEffect, useMemo, useRef, useState } from 'react'
import type { GraphEntity, MapArtifact } from '../../types/v1'
export interface BridgeMessage {channel: 'codecanopy-archify'; version: '1.1'; nonce: string; snapshotId: string; viewId: string; type: 'ready' | 'select' | 'open'; entityId?: string}
export function validBridge(data: unknown, nonce: string, artifact: MapArtifact): data is BridgeMessage {
  if (!data || typeof data !== 'object') return false
  const m = data as BridgeMessage
  return m.channel === 'codecanopy-archify' && m.version === '1.1' && m.nonce === nonce && m.snapshotId === artifact.graph.snapshot_id && m.viewId === artifact.view_id && (m.type === 'ready' || ((m.type === 'select' || m.type === 'open') && artifact.graph.entities.some(e => e.id === m.entityId)))
}
export function StructureMap({artifact, selectedId, onSelect, onOpen}: {artifact: MapArtifact; selectedId?: string; onSelect(entity: GraphEntity): void; onOpen(entity: GraphEntity): void}) {
  const frame = useRef<HTMLIFrameElement>(null); const [ready,setReady] = useState(false)
  const nonce = useMemo(() => crypto.randomUUID(), [artifact.view_id])
  function send(type: string, entityId?: string) {frame.current?.contentWindow?.postMessage({channel: 'codecanopy-archify', version: '1.1', nonce, snapshotId: artifact.graph.snapshot_id, viewId: artifact.view_id, type, entityId}, '*')}
  useEffect(() => {
    setReady(false)
    function receive(event: MessageEvent) {
      if (event.source !== frame.current?.contentWindow || !validBridge(event.data, nonce, artifact)) return
      if (event.data.type === 'ready') setReady(true)
      else {const entity = artifact.graph.entities.find(e => e.id === event.data.entityId); if (entity) (event.data.type === 'open' ? onOpen : onSelect)(entity)}
    }
    window.addEventListener('message',receive); return () => window.removeEventListener('message',receive)
  }, [artifact,nonce,onSelect,onOpen])
  useEffect(() => {if (ready && selectedId) send('select',selectedId)}, [ready,selectedId,nonce])
  return <div className="structure-map"><div className="map-camera" aria-label="Map camera controls"><button className="btn small" aria-label="Zoom in" onClick={() => send('zoom-in')}>＋</button><button className="btn small" aria-label="Zoom out" onClick={() => send('zoom-out')}>−</button><button className="btn small" onClick={() => send('fit')}>Fit</button><button className="btn small" onClick={() => send('reset')}>Reset</button></div><iframe key={artifact.view_id} ref={frame} title="Repository structure map" sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={artifact.html} onLoad={() => send('init')}/></div>
}
