import type { HealthResponse, ProjectUploadResponse } from '../types/api'
import type { File as CodebaseFile, Project } from '../types/codebase'
import { ApiError } from './v1/api'

const apiBase = `${import.meta.env.VITE_API_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`}/api`

async function legacyRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiBase + path, { ...init, credentials: 'include' })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, typeof body?.detail === 'string' ? body.detail : `API returned ${response.status}`)
  return body as T
}

export async function getHealth(signal: AbortSignal): Promise<HealthResponse> {
  return legacyRequest<HealthResponse>('/health', { signal })
}

export async function uploadProject(file: File): Promise<ProjectUploadResponse> {
  const body = new FormData()
  body.append('file', file)
  return legacyRequest<ProjectUploadResponse>('/projects', { method: 'POST', body })
}

export async function getProject(projectId: string): Promise<Project> {
  return legacyRequest<Project>(`/projects/${encodeURIComponent(projectId)}`)
}

export async function analyzeProject(projectId: string): Promise<CodebaseFile[]> {
  return legacyRequest<CodebaseFile[]>(
    `/projects/${encodeURIComponent(projectId)}/analyze`,
    { method: 'POST' },
  )
}
