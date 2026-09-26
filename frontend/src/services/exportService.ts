/** Export only the backend's validated Archify artifact. No fallback renderer. */
import type { MapArtifact } from '../types/v1'
export async function verifyArtifact(artifact: MapArtifact): Promise<boolean> {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(artifact.html))
  return [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2,'0')).join('') === artifact.html_sha256
}
export async function downloadStructuralExport(artifact: MapArtifact) {
  if (!await verifyArtifact(artifact)) throw new Error('Export integrity check failed. Reload the map and try again.')
  const url = URL.createObjectURL(new Blob([artifact.html], {type: 'text/html;charset=utf-8'}))
  const link = document.createElement('a'); link.href = url; link.download = `codecanopy-map-${artifact.graph.snapshot_id.slice(0,8)}-${artifact.view_id.slice(0,8)}.html`
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
