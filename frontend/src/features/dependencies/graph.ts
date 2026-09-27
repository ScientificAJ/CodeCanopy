import type { DependencyResult, DependencyEdge } from './types'

export function projectGraph(result: DependencyResult, mode: 'file' | 'function') {
  const byId = new Map(result.nodes.map(node => [node.id, node]))
  const nodes = result.nodes.filter(node => mode === 'file' ? node.kind === 'file' : true)
  const edges: DependencyEdge[] = []
  for (const edge of result.edges) {
    if (mode === 'function' && edge.kind !== 'calls') continue
    const source = byId.get(edge.source_id), target = byId.get(edge.target_id)
    if (!source || !target) continue
    if (mode === 'file') {
      if (source.file_id === target.file_id) continue
      edges.push({...edge, source_id: source.file_id, target_id: target.file_id})
    } else edges.push(edge)
  }
  return {nodes, edges, byId}
}

/** Reverse reachability is potential impact, never a claim of runtime breakage. */
export function reachable(start: string, edges: DependencyEdge[], reverse = false, max = 1000) {
  const adjacency = new Map<string, Set<string>>()
  for (const edge of edges) {
    const a = reverse ? edge.target_id : edge.source_id, b = reverse ? edge.source_id : edge.target_id
    const set = adjacency.get(a) ?? new Set<string>(); set.add(b); adjacency.set(a, set)
  }
  const visited = new Set([start]), queue = [start]
  let cycle = false, truncated = false
  for (let i = 0; i < queue.length; i++) {
    for (const next of adjacency.get(queue[i]) ?? []) {
      if (next === start) cycle = true
      if (visited.has(next)) continue
      if (visited.size >= max + 1) { truncated = true; continue }
      visited.add(next); queue.push(next)
    }
  }
  visited.delete(start)
  return {ids: visited, cycle, truncated}
}
