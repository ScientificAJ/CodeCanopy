/**
 * V1 API types — mirrors backend/app/models/v1/*.py
 * These are the canonical shared types for the GREPO v1 API.
 * Feature modules must reference these types rather than inventing
 * parallel project/snapshot/entity types.
 */

// ── Source kinds ───────────────────────────────────────────────────────────
export type SourceKind = 'zip' | 'github'

// ── Import ─────────────────────────────────────────────────────────────────
export interface ImportAccepted {
  schema_version: '1.0'
  run_id: string
  project_id: string
  status: 'accepted'
}

export interface GitHubImportRequest {
  url: string
  ref?: string
  analysis_profile?: string
  ai_policy?: string
  schema_version?: '1.0'
}

// ── Project ────────────────────────────────────────────────────────────────
export interface V1Project {
  schema_version: '1.0'
  id: string
  name: string
  created_at: string
  snapshot_ids: string[]
}

// ── Snapshot ───────────────────────────────────────────────────────────────
export interface SnapshotSource {
  kind: SourceKind
  owner?: string
  repo?: string
  resolved_commit?: string
  archive_digest?: string
  display_ref?: string
}

export interface Snapshot {
  schema_version: '1.0'
  id: string
  project_id: string
  source: SnapshotSource
  manifest_hash: string
  policy_version: string
  created_at: string
  expires_at?: string
  analysis_run_id?: string
}

// ── File inventory ─────────────────────────────────────────────────────────
export interface FileRecord {
  schema_version: '1.0'
  id: string
  snapshot_id: string
  path: string
  name: string
  size: number
  content_hash: string
  is_text: boolean
  encoding?: string
  language: string
  language_basis: string
  excluded: boolean
  exclusion_reason?: string
}

export interface FilePage {
  schema_version: '1.0'
  snapshot_id: string
  files: FileRecord[]
  total: number
  cursor?: string
  truncated: boolean
}

// ── Source slice ───────────────────────────────────────────────────────────
export interface SourceSlice {
  schema_version: '1.0'
  file_id: string
  snapshot_id: string
  path: string
  line_start: number
  line_end: number
  total_lines: number
  content: string
  truncated: boolean
  content_hash: string
}

// ── Capabilities ───────────────────────────────────────────────────────────
export interface FileCapability {
  file_id: string
  path: string
  language: string
  syntax_extraction: boolean
  reference_resolution: boolean
  summary_eligible: boolean
  level: 'full' | 'text_only' | 'binary' | 'excluded'
  parser_name?: string
  limitations: string[]
}

export interface CapabilityReport {
  schema_version: '1.0'
  snapshot_id: string
  files: FileCapability[]
  parsed_count: number
  text_only_count: number
  binary_count: number
  excluded_count: number
  limitations: string[]
}

export interface FunctionEvidence {
  id: string
  name: string
  file_id: string
  path: string
  line_start: number
  line_end: number
}

export interface DuplicateCandidate {
  id: string
  functions: FunctionEvidence[]
  structural_similarity: number
  semantic_similarity?: number | null
  confidence: 'high' | 'medium' | 'low'
  review_recommended: boolean
  method: string
}

export interface PotentiallyUnusedFunction {
  id: string
  function: FunctionEvidence
  status: 'potentially_unused'
  method: string
  explanation: string
}

export interface FindingsCoverage {
  inventoried_files: number
  parsed_files: number
  analyzed_functions: number
  unresolved_references: number
  limitations: string[]
}

export interface DuplicateDetectionResult {
  schema_version: '1.0'
  snapshot_id: string
  candidates: DuplicateCandidate[]
  coverage: FindingsCoverage
}

export interface UnusedDetectionResult {
  schema_version: '1.0'
  snapshot_id: string
  findings: PotentiallyUnusedFunction[]
  coverage: FindingsCoverage
}

// ── Graph ──────────────────────────────────────────────────────────────────
export type EntityKind = 'repository' | 'folder' | 'file' | 'virtual_group'
export type RelationKind = 'groups' | 'contains' | 'imports' | 'calls' | 'declares_dependency'
export type RelationBasis = 'observed' | 'resolved' | 'inferred' | 'unknown'

export interface GraphEntity {
  id: string
  kind: EntityKind
  label: string
  path?: string
  file_id?: string
  parent_id?: string
  child_count: number
  metadata: Record<string, unknown>
}

export interface GraphRelation {
  id: string
  source_id: string
  target_id: string
  kind: RelationKind
  basis: RelationBasis
  evidence_ids: string[]
  unresolved: boolean
}

export interface GraphCoverage {
  inventoried_files: number
  parsed_files: number
  unresolved_references: number
  excluded_paths: string[]
  limitations: string[]
  truncated: boolean
  total_entities: number
  returned_entities: number
}

export interface Graph {
  schema_version: '1.1'
  focus_path: string
  cursor: number
  next_cursor: number | null
  child_total: number
  evidence: unknown[]
  snapshot_id: string
  fixture_only: boolean
  entities: GraphEntity[]
  relations: GraphRelation[]
  coverage: GraphCoverage
}

// ── Integration slot ───────────────────────────────────────────────────────
export type SlotStatus = 'NOT_CONNECTED' | 'NOT_IMPLEMENTED' | 'UNAVAILABLE'

export interface IntegrationSlotResponse {
  schema_version: '1.0'
  slot: string
  status: SlotStatus
  title: string
  description: string
  integration_path?: string
  docs_url?: string
}

// ── Analysis run ───────────────────────────────────────────────────────────
export type RunStatus = 'queued' | 'running' | 'partial' | 'completed' | 'failed' | 'cancelled'

export interface AnalysisRun {
  schema_version: '1.1'
  id: string
  project_id: string
  snapshot_id?: string
  status: RunStatus
  stage?: string
  stage_progress?: number
  event_sequence: number
  diagnostics: Array<{ file_path?: string; stage: string; message: string; severity: 'warning' | 'error' }>
  cancel_requested: boolean
  started_at: string
  completed_at?: string
  result_snapshot_id?: string
}

export interface VirtualGroup { id: string; label: string; members: string[]; color?: 'lime' | 'blue' | 'violet' | 'amber' }
export interface ViewPreferences {
  schema_version: '1.1'
  labels: Record<string, string>
  groups: VirtualGroup[]
  theme: 'light' | 'dark'
  density?: 'auto' | 'comfortable' | 'expanded'
  order: 'folders-first' | 'alphabetical'
  focus: string
}
export interface MapArtifact {
  schema_version: '1.1'
  view_id: string
  graph: Graph
  html: string
  receipt: Record<string, unknown>
  archify_commit: string
  upstream_sha256: string
  html_sha256: string
}
