import { describe, it, expect } from 'vitest'
import { webcrypto } from 'node:crypto'
import { verifyArtifact } from './exportService'
import { validBridge } from '../components/map/StructureMap'
import type { MapArtifact } from '../types/v1'
const artifact = {view_id: 'view', html: 'validated artifact', graph: {snapshot_id: 'snapshot',entities: [{id: 'canonical-id'}]}} as MapArtifact
describe('validated export boundary', () => {
  it('rejects an altered HTML artifact', async () => {
    Object.defineProperty(globalThis, 'crypto', {value: webcrypto, configurable: true})
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(artifact.html))
    const hash = [...new Uint8Array(digest)].map(n => n.toString(16).padStart(2,'0')).join('')
    expect(await verifyArtifact({...artifact,html_sha256: hash})).toBe(true)
    expect(await verifyArtifact({...artifact,html_sha256: hash,html: 'tampered'})).toBe(false)
  })
  it('accepts canonical selection and rejects forged bridge messages', () => {
    const message = {channel: 'codecanopy-archify',version: '1.1',nonce: 'nonce',snapshotId: 'snapshot',viewId: 'view',type: 'select',entityId: 'canonical-id'}
    expect(validBridge(message,'nonce',artifact)).toBe(true)
    for (const patch of [{nonce:'wrong'},{snapshotId:'old'},{viewId:'old'},{entityId:'outside'},{type:'execute'},{version:'9'}]) expect(validBridge({...message,...patch},'nonce',artifact)).toBe(false)
  })
})
