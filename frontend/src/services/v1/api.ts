/** One authenticated, abortable API client for every v1 feature. */
import type { AnalysisRun, CapabilityReport, DuplicateDetectionResult, FilePage, GitHubImportRequest, Graph, GraphEntity, ImportAccepted, MapArtifact, Snapshot, SourceSlice, UnusedDetectionResult, V1Project, ViewPreferences } from '../../types/v1'
const base = `${import.meta.env.VITE_API_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`}/api/v1`
export class ApiError extends Error {
  constructor(public readonly status: number, message: string, public readonly code?: string) { super(message); this.name = 'ApiError' }
}
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(base + path, { ...init, credentials: 'include' })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, body?.error?.message ?? (typeof body?.detail === 'string' ? body.detail : 'The request could not be completed.'), body?.error?.code)
  return body as T
}
const json = (body: unknown, signal?: AbortSignal): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal })
export const snapshotPath = (p: string, s: string) => `/projects/${encodeURIComponent(p)}/snapshots/${encodeURIComponent(s)}`
let session: Promise<{ status: string }> | null = null
export const ensureSession = () => session ??= request<{ status: string }>('/session', { method: 'POST' }).catch(error => {session = null; throw error})
export const listProjects = () => request<V1Project[]>('/projects')
export const getProject = (p: string, signal?: AbortSignal) => request<V1Project>(`/projects/${encodeURIComponent(p)}`, { signal })
export const deleteProject = (p: string) => request<void>(`/projects/${encodeURIComponent(p)}`, { method: 'DELETE' })
export const listSnapshots = (p: string, signal?: AbortSignal) => request<Snapshot[]>(`/projects/${encodeURIComponent(p)}/snapshots`, { signal })
export const getSnapshot = (p: string, s: string, signal?: AbortSignal) => request<Snapshot>(snapshotPath(p, s), { signal })
export async function importZip(file: File): Promise<ImportAccepted> {
  const body = new FormData(); body.append('file', file)
  return request('/imports/zip', { method: 'POST', body })
}
export const importGitHub = (body: GitHubImportRequest) => request<ImportAccepted>('/imports/github', json(body))
export const getRun = (id: string, signal?: AbortSignal) => request<AnalysisRun>(`/runs/${id}`, { signal })
export const cancelRun = (id: string) => request<AnalysisRun>(`/runs/${id}/cancel`, { method: 'POST' })
export const getInventory = (p: string, s: string, cursor?: string, limit = 500, signal?: AbortSignal) => request<FilePage>(`${snapshotPath(p, s)}/files?${new URLSearchParams({ limit: String(limit), ...(cursor ? { cursor } : {}) })}`, { signal })
export async function getAllFiles(p: string, s: string, signal?: AbortSignal) {
  const files: FilePage['files'] = []; let cursor: string | undefined
  do { const page = await getInventory(p, s, cursor, 500, signal); files.push(...page.files); cursor = page.cursor ?? undefined } while (cursor)
  return files
}
export const getEntities = (p: string, s: string, signal?: AbortSignal) => request<GraphEntity[]>(snapshotPath(p, s) + '/entities', { signal })
export const getCapabilities = (p: string, s: string, signal?: AbortSignal) => request<CapabilityReport>(snapshotPath(p, s) + '/capabilities', { signal })
export const getSource = (p: string, s: string, file: string, start = 1, end?: number, max = 200, signal?: AbortSignal) => request<SourceSlice>(`${snapshotPath(p, s)}/source/${encodeURIComponent(file)}?${new URLSearchParams({line_start: String(start), max_lines: String(max), ...(end ? {line_end: String(end)} : {})})}`, { signal })
export const getGraph = (p: string, s: string, max = 12, signal?: AbortSignal) => request<Graph>(`${snapshotPath(p, s)}/graph?max_entities=${max}`, { signal })
export const getPreferences = (p: string, s: string, signal?: AbortSignal) => request<ViewPreferences>(snapshotPath(p, s) + '/view', { signal })
export const savePreferences = (p: string, s: string, body: ViewPreferences) => request<ViewPreferences>(snapshotPath(p, s) + '/view', {...json(body), method: 'PATCH'})
export const renderMap = (p: string, s: string, focus: string, cursor = 0, signal?: AbortSignal) => request<MapArtifact>(snapshotPath(p, s) + '/map', json({ focus, cursor }, signal))
import type { ReusableFunctionResult } from '../../types/codebase'
export const getReusableFunctions = (p: string, s: string, minCallers = 1, signal?: AbortSignal) =>
  request<ReusableFunctionResult>(`${snapshotPath(p, s)}/findings/reuse?min_callers=${minCallers}`, { signal })
export const getDuplicateFindings = (p: string, s: string, signal?: AbortSignal) => request<DuplicateDetectionResult>(snapshotPath(p, s) + '/findings/duplicates', { signal })
export const getUnusedFindings = (p: string, s: string, signal?: AbortSignal) => request<UnusedDetectionResult>(snapshotPath(p, s) + '/findings/unused', { signal })
