/** Shared identities, selection, source navigation and view-only preferences. */
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { getAllFiles, getCapabilities, getEntities, getPreferences, getProject, getSnapshot, getRun, savePreferences } from '../services/v1/api'
import type { AnalysisRun, CapabilityReport, FileRecord, Graph, GraphEntity, Snapshot, ViewPreferences } from '../types/v1'
export interface SelectedEntity { entityId: string; kind: string; path: string; fileId?: string; lineRange?: {start: number; end: number} }
export interface ViewState { focusedView: 'overview' | 'map' | 'source'; mapCamera: {x: number; y: number; scale: number} }
const defaults: ViewPreferences = {schema_version: '1.1', labels: {}, groups: [], theme: 'light', order: 'folders-first', focus: '.'}
export interface WorkspaceState {
  projectId: string | null; projectName: string | null; snapshot: Snapshot | null
  selectedEntity: SelectedEntity | null; graph: Graph | null; files: FileRecord[]; entities: GraphEntity[]
  run: AnalysisRun | null; capabilities: CapabilityReport | null; preferences: ViewPreferences; viewState: ViewState
  loading: boolean; error: string | null
}
export interface WorkspaceActions {
  loadWorkspace(project: string, snapshot: string): Promise<void>
  selectEntity(entity: SelectedEntity | null): void
  setLineRange(range: {start: number; end: number} | undefined): void
  setGraph(graph: Graph | null): void
  setFocusedView(view: ViewState['focusedView']): void
  updatePreferences(prefs: ViewPreferences): Promise<void>
}
export type WorkspaceContextValue = WorkspaceState & WorkspaceActions
const initial: WorkspaceState = {projectId: null, projectName: null, snapshot: null, selectedEntity: null, graph: null, files: [], entities: [], capabilities: null, run: null, preferences: defaults, viewState: {focusedView: 'overview', mapCamera: {x: 0, y: 0, scale: 1}}, loading: true, error: null}
const Context = createContext<WorkspaceContextValue | null>(null)
export function WorkspaceProvider({children}: {children: ReactNode}) {
  const [state, set] = useState(initial)
  const loading = useRef<AbortController | null>(null)
  const generation = useRef(0)
  useEffect(() => () => { loading.current?.abort(); generation.current++ }, [])
  const loadWorkspace = useCallback(async (p: string, s: string) => {
    loading.current?.abort(); const control = new AbortController(); loading.current = control; generation.current++
    set({...initial, projectId: p})
    try {
      const [project, snapshot, files, entities, capabilities, preferences] = await Promise.all([
        getProject(p, control.signal), getSnapshot(p, s, control.signal), getAllFiles(p, s, control.signal),
        getEntities(p, s, control.signal), getCapabilities(p, s, control.signal), getPreferences(p, s, control.signal),
      ])
      const run = snapshot.analysis_run_id ? await getRun(snapshot.analysis_run_id, control.signal).catch(() => null) : null
      if (!control.signal.aborted) set({...initial, projectId: p, projectName: project.name, snapshot, files, entities, capabilities, preferences, run, loading: false})
    } catch (e) { if (!control.signal.aborted) set({...initial, projectId: p, loading: false, error: e instanceof Error ? e.message : 'Unable to open this workspace.'}) }
  }, [])
  const selectEntity = useCallback((selectedEntity: SelectedEntity | null) => set(s => ({...s, selectedEntity})), [])
  const setLineRange = useCallback((lineRange: SelectedEntity['lineRange']) => set(s => ({...s, selectedEntity: s.selectedEntity ? {...s.selectedEntity, lineRange} : null})), [])
  const setGraph = useCallback((graph: Graph | null) => set(s => ({...s, graph})), [])
  const setFocusedView = useCallback((focusedView: ViewState['focusedView']) => set(s => ({...s, viewState: {...s.viewState, focusedView}})), [])
  const updatePreferences = useCallback(async (preferences: ViewPreferences) => {
    if (!state.projectId || !state.snapshot) return
    const version = generation.current
    const saved = await savePreferences(state.projectId, state.snapshot.id, preferences)
    if (version === generation.current) set(s => ({...s, preferences: saved}))
  }, [state.projectId, state.snapshot])
  return <Context.Provider value={{...state, loadWorkspace, selectEntity, setLineRange, setGraph, setFocusedView, updatePreferences}}>{children}</Context.Provider>
}
export function useWorkspace() { const value = useContext(Context); if (!value) throw new Error('useWorkspace requires WorkspaceProvider'); return value }
export function selectionFor(entity: GraphEntity): SelectedEntity { return {entityId: entity.id, kind: entity.kind, path: entity.path ?? entity.label, fileId: entity.file_id} }
