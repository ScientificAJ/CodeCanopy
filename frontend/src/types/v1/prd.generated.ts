/* Generated from contracts/prd.schema.json. Run npm run contracts; do not edit. */

export type GrepoCoreDesignContracts10 = Graph | Answer | Finding | ChangePack | AnalysisRun | ApiError;

export interface Graph {
  schema_version: "1.0";
  snapshot_id: string;
  fixture_only: boolean;
  entities: Entity[];
  relations: Relation[];
  evidence: Evidence[];
  coverage: Coverage;
}
export interface Entity {
  id: string;
  kind: "file" | "folder" | "symbol" | "package" | "external" | "contract";
  label: string;
  path: string;
  evidence_ids: string[];
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
    | "inferred_related";
  basis: "observed" | "resolved" | "inferred";
  evidence_ids: string[];
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
}
export interface Answer {
  schema_version: "1.0";
  id: string;
  snapshot_id: string;
  status: "pending" | "draft" | "validated" | "failed" | "cancelled";
  question: string;
  claims: Claim[];
  evidence: Evidence[];
  limitations: string[];
  /**
   * @maxItems 3
   */
  follow_ups: [] | [string] | [string, string] | [string, string, string];
  model_config_id: string;
  fixture_only: boolean;
}
export interface Claim {
  text: string;
  basis: "observed" | "resolved" | "inferred" | "unknown" | "hypothetical";
  evidence_ids: string[];
}
export interface Finding {
  schema_version: "1.0";
  id: string;
  snapshot_id: string;
  kind: "reuse" | "duplicate" | "unused";
  subject_ids: string[];
  method: string;
  evidence_ids: string[];
  counter_evidence: string[];
  limitations: string[];
  recommendation: string;
  review_status: "unreviewed" | "reviewed" | "dismissed" | "intentional";
  fixture_only: boolean;
}
export interface ChangePack {
  schema_version: "1.0";
  id: string;
  snapshot_id: string;
  source: {
    kind: "github" | "zip";
    repository: string | null;
    revision: string | null;
    archive_sha256: string | null;
  };
  intent: string;
  source_is_read_only: true;
  observations: Claim[];
  existing_helpers_considered: string[];
  proposed_steps: string[];
  unknowns: string[];
  verification_steps: string[];
  evidence: Evidence[];
  fixture_only: boolean;
}
export interface AnalysisRun {
  schema_version: "1.0";
  id: string;
  snapshot_id: string | null;
  status: "queued" | "running" | "partial" | "completed" | "failed" | "cancelled";
  stage: string;
  event_sequence: number;
  diagnostics: string[];
  cancel_requested: boolean;
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
