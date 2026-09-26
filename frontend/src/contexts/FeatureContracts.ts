/** Teammate payloads reuse the PRD's generated evidence and result contracts. */
import type { ComponentType } from 'react'
import type { Answer, ChangePack, Evidence, Finding, Graph as PrdGraph } from '../types/v1/prd.generated'
import type { Graph } from '../types/v1'
import { registerSlot, type SlotContext, type SlotId, type SlotProps, type SlotRegistration } from './SlotRegistry'
export interface SummaryPayload {schema_version: '1.1'; snapshot_id: string; entity_id: string; text: string; evidence: Evidence[]; limitations: string[]}
export interface DependencyOverlay {schema_version: '1.1'; snapshot_id: string; graph: PrdGraph | Graph; impact_subject_ids: string[]; limitations: string[]}
export interface FindingPage {schema_version: '1.1'; snapshot_id: string; findings: Finding[]; evidence: Evidence[]; cursor: string | null}
export interface GeneratedDocument {schema_version: '1.1'; snapshot_id: string; title: string; markdown: string; evidence: Evidence[]; limitations: string[]}
export interface FeaturePayloads {
  'summaries.context-panel': SummaryPayload
  'dependencies.workspace': DependencyOverlay
  'map.overlay': DependencyOverlay
  'reuse.findings': FindingPage
  'duplicates.compare': FindingPage
  'unused.review': FindingPage
  'ask.workspace': Answer
  'proposals.detail': ChangePack
  'docs.generated': GeneratedDocument
}
export function registerFeature<K extends SlotId>(id: K, feature: {
  Component: ComponentType<SlotProps<FeaturePayloads[K]>>
  availability?: SlotRegistration['availability']
  load: (context: SlotContext, signal: AbortSignal) => Promise<FeaturePayloads[K]>
}) {
  // The registry erases the payload parameter at one boundary; the ID-specific
  // registration above keeps each component paired with its own adapter type.
  return registerSlot(id, feature as unknown as SlotRegistration)
}
