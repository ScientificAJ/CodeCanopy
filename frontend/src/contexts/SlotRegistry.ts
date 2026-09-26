/** Public teammate extension surface. Registration is separate from request state. */
import type { ComponentType } from 'react'
import type { CapabilityReport, FileRecord, Graph, GraphEntity, Snapshot } from '../types/v1'
import type { SelectedEntity, ViewState } from './WorkspaceContext'
export type SlotId = 'summaries.context-panel' | 'dependencies.workspace' | 'reuse.findings' | 'duplicates.compare' | 'unused.review' | 'ask.workspace' | 'proposals.detail' | 'docs.generated' | 'map.overlay'
export type FeatureAvailability = 'connected' | 'not-connected' | 'unavailable'
export type RequestState<T = unknown> = {status: 'idle'} | {status: 'loading'} | {status: 'ready'; data: T} | {status: 'error'; message: string}
export interface SlotContext {
  projectId: string; snapshotId: string; snapshot: Snapshot
  selectedEntity: SelectedEntity | null; files: FileRecord[]; entities: GraphEntity[]; graph: Graph | null
  capabilities: CapabilityReport | null; viewState: ViewState
  selectEntity(entity: SelectedEntity | null): void
  openSource(fileId: string, range?: {start: number; end: number}): void
  navigate(path: string): void
}
export interface SlotProps<T = unknown> extends SlotContext { availability: FeatureAvailability; request: RequestState<T> }
export interface SlotRegistration {
  Component: ComponentType<SlotProps>
  availability?: FeatureAvailability
  load?: (context: SlotContext, signal: AbortSignal) => Promise<unknown>
}
const registry = new Map<SlotId, SlotRegistration>()
const listeners = new Set<() => void>()
let revision = 0
function notify() { revision++; listeners.forEach(fn => fn()) }
/** Call from the feature entry module. Returns teardown for tests/hot reload. */
export function registerSlot(id: SlotId, feature: ComponentType<SlotProps> | SlotRegistration): () => void {
  const registration = typeof feature === 'function' ? {Component: feature} : feature as SlotRegistration
  registry.set(id, registration); notify()
  return () => {if (registry.get(id) === registration) {registry.delete(id); notify()}}
}
export const getSlot = (id: SlotId) => registry.get(id)
export const getSlotComponent = (id: SlotId) => registry.get(id)?.Component ?? null
export const isSlotRegistered = (id: SlotId) => registry.has(id)
export const registeredSlots = () => [...registry.keys()]
export const subscribeSlots = (listener: () => void) => { listeners.add(listener); return () => {listeners.delete(listener)} }
export const slotRevision = () => revision
