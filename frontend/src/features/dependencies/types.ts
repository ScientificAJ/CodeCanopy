export interface DependencyNode {
  id: string; kind: 'file' | 'function'; label: string; path: string; file_id: string; line_start: number; line_end: number
}
export interface DependencyEdge {
  id: string; source_id: string; target_id: string; kind: 'imports' | 'calls'; file_id: string
  line_start: number; line_end: number; basis: 'static_binding'
}
export interface DependencyResult {
  schema_version: '1.0'; snapshot_id: string; nodes: DependencyNode[]; edges: DependencyEdge[]
  unresolved: {source_id: string; name: string; kind: 'imports' | 'calls'; file_id: string; line_start: number; reason: string}[]
  coverage: {inventoried_files: number; analyzed_files: number; unsupported_files: number; unresolved_count: number; truncated: boolean; limitations: string[]}
}
