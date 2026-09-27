/* Generated from contracts/structure-1.1.schema.json. Run npm run contracts; do not edit. */

export type GREPOStructureSlice11 = Graph | AnalysisRun | ApiError;

export interface Graph {
  schema_version: "1.1";
  snapshot_id: string;
  fixture_only: boolean;
  entities: Entity[];
  relations: Relation[];
  evidence: Evidence[];
  coverage: Coverage;
  focus_path?: string;
  cursor?: number;
  next_cursor?: number | null;
  child_total?: number;
}
export interface Entity {
  id: string;
  kind: "file" | "folder" | "symbol" | "package" | "external" | "contract" | "repository" | "virtual_group";
  label: string;
  path: string | null;
  evidence_ids: string[];
  file_id?: string | null;
  parent_id?: string | null;
  child_count?: number;
  metadata?: {
    [k: string]: unknown;
  };
}
export interface Relation {
  id: string;
  source_id: string;
  target_id: string;
  kind:
    | "contains"
    | "imports"
    | "calls"
    | "references"
    | "exports"
    | "declares_dependency"
    | "implements_contract"
    | "tests"
    | "inferred_related"
    | "groups";
  basis: "observed" | "resolved" | "inferred";
  evidence_ids: string[];
  unresolved?: boolean;
}
export interface Evidence {
  id: string;
  snapshot_id: string;
  file_id: string;
  path: string;
  range: SourceRange;
  content_sha256: string;
  basis: "observed" | "resolved" | "inferred";
}
export interface SourceRange {
  line_start: number;
  line_end: number;
}
export interface Coverage {
  inventoried_files: number;
  parsed_files: number;
  unresolved_references: number;
  excluded_paths: string[];
  limitations: string[];
  truncated: boolean;
  total_entities?: number;
  returned_entities?: number;
}
export interface AnalysisRun {
  schema_version: "1.1";
  id: string;
  snapshot_id: string | null;
  status: "queued" | "running" | "partial" | "completed" | "failed" | "cancelled";
  stage: string | null;
  event_sequence: number;
  diagnostics: {
    file_path?: string | null;
    stage: string;
    message: string;
    severity: "warning" | "error";
  }[];
  cancel_requested: boolean;
  project_id?: string;
  stage_progress?: number | null;
  started_at?: string;
  completed_at?: string | null;
  result_snapshot_id?: string | null;
}
export interface ApiError {
  error: {
    code: string;
    message: string;
    retryable: boolean;
    request_id: string;
    details: {
      [k: string]: unknown;
    };
  };
}
