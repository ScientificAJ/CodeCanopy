import type { HealthResponse, ProjectUploadResponse } from '../types/api'
import type { File as CodebaseFile, Project } from '../types/codebase'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? '' : 'http://localhost:8000')

async function apiError(response: Response): Promise<Error> {
  const payload: unknown = await response.json().catch(() => null)
  const detail =
    typeof payload === 'object' && payload !== null && 'detail' in payload && typeof payload.detail === 'string'
      ? payload.detail
      : `API returned ${response.status}`
  return new Error(detail)
}

export async function getHealth(signal: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/api/health`, { signal })
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`)
  }
  return response.json() as Promise<HealthResponse>
}

export async function uploadProject(file: File): Promise<ProjectUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${apiBaseUrl}/api/projects`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw await apiError(response)
  }

  return response.json() as Promise<ProjectUploadResponse>
}

export async function getProject(projectId: string): Promise<Project> {
  const response = await fetch(`${apiBaseUrl}/api/projects/${encodeURIComponent(projectId)}`)
  if (!response.ok) {
    throw await apiError(response)
  }
  return response.json() as Promise<Project>
}

export async function analyzeProject(projectId: string): Promise<CodebaseFile[]> {
  const response = await fetch(
    `${apiBaseUrl}/api/projects/${encodeURIComponent(projectId)}/analyze`,
    { method: 'POST' },
  )
  if (!response.ok) {
    throw await apiError(response)
  }
  return response.json() as Promise<CodebaseFile[]>
}
