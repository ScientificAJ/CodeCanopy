export interface HealthResponse {
  status: string
}

export interface ProjectUploadResponse {
  project_id: string
  name: string
  status: string
  file_count: number
}

export type ApiHealthState =
  | { status: 'loading' }
  | { status: 'connected'; detail: string }
  | { status: 'unavailable'; message: string }
