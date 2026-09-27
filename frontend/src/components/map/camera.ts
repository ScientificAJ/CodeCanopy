export interface MapCamera {x: number; y: number; scale: number}
export function validCamera(value: unknown): value is MapCamera {
  if (!value || typeof value !== 'object') return false
  const camera = value as MapCamera
  return Number.isFinite(camera.x) && Math.abs(camera.x) < 1000000 && Number.isFinite(camera.y) && Math.abs(camera.y) < 1000000 && Number.isFinite(camera.scale) && camera.scale >= 1 && camera.scale <= 3
}
export function readCamera(key: string): MapCamera | undefined {
  try {const value: unknown = JSON.parse(sessionStorage.getItem(key) ?? 'null'); return validCamera(value) ? value : undefined} catch {return undefined}
}
export function saveCamera(key: string, camera: MapCamera) {
  try {
    sessionStorage.setItem(key, JSON.stringify(camera))
    const keys = Object.keys(sessionStorage).filter(k => k.startsWith('codecanopy-camera:'))
    keys.slice(0, Math.max(0, keys.length - 80)).forEach(k => sessionStorage.removeItem(k))
  } catch { /* Navigation remains usable when browser storage is unavailable. */ }
}
