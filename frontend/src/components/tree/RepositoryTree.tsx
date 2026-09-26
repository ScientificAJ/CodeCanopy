import { useEffect, useMemo, useRef, useState } from 'react'
import type { GraphEntity } from '../../types/v1'
import { Icon } from '../ui/Icon'
interface Props {entities: GraphEntity[]; selectedId?: string; onSelect(entity: GraphEntity): void; onOpen(entity: GraphEntity): void; searchRef?: React.RefObject<HTMLInputElement | null>}
export function RepositoryTree({entities, selectedId, onSelect, onOpen, searchRef}: Props) {
  const [limit, setLimit] = useState(500); const [query, setQuery] = useState(''); const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [focused, setFocused] = useState<string | null>(null)
  const list = useRef<HTMLDivElement>(null)
  const root = entities.find(e => !e.parent_id)
  const children = useMemo(() => {const map = new Map<string, GraphEntity[]>(); for (const e of entities) {const key = e.parent_id ?? ''; map.set(key, [...(map.get(key) ?? []), e])} for (const value of map.values()) value.sort((a,b) => Number(a.kind === 'file') - Number(b.kind === 'file') || a.label.localeCompare(b.label)); return map}, [entities])
  useEffect(() => {if (root) setExpanded(new Set([root.id]))}, [root?.id])
  useEffect(() => {
    if (!selectedId) return
    const ancestors: string[] = []; let entity = entities.find(e => e.id === selectedId)
    while (entity?.parent_id) {ancestors.push(entity.parent_id); entity = entities.find(e => e.id === entity?.parent_id)}
    setExpanded(previous => new Set([...previous, ...ancestors])); setFocused(selectedId)
  }, [selectedId, entities])
  const visible: {entity: GraphEntity; depth: number}[] = []
  const needle = query.trim().toLowerCase()
  function walk(parent: string, depth: number) { for (const entity of children.get(parent) ?? []) {visible.push({entity, depth}); if (expanded.has(entity.id)) walk(entity.id, depth + 1)} }
  if (needle) entities.filter(e => (e.path ?? e.label).toLowerCase().includes(needle)).forEach(entity => visible.push({entity, depth: 0}))
  else walk('', 0)
  const shown = visible.slice(0, limit)
  function focusAt(id?: string) {if (!id) return; setFocused(id); list.current?.querySelector<HTMLElement>(`[data-entity="${id}"]`)?.focus()}
  function toggle(id: string) {setExpanded(previous => {const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next})}
  return <><div className="tree-header"><h2>Project structure</h2><span>{entities.filter(e => e.kind === 'file').length}</span></div><div className="tree-search input-icon"><Icon name="search"/><input ref={searchRef} aria-label="Search repository files" placeholder="Search files…" value={query} onChange={e => setQuery(e.target.value)}/></div>
    <div role="tree" aria-label="Repository files" ref={list} className="repository-tree">
      {shown.map(({entity, depth}, i) => <div key={entity.id} role="treeitem" data-entity={entity.id} tabIndex={(focused ?? shown[0]?.entity.id) === entity.id ? 0 : -1} aria-level={depth + 1} aria-selected={selectedId === entity.id} aria-expanded={entity.kind === 'file' ? undefined : expanded.has(entity.id)} className={`tree-row ${selectedId === entity.id ? 'selected' : ''}`} style={{paddingLeft: 8 + depth * 14}} title={entity.path} onFocus={() => setFocused(entity.id)} onClick={() => onSelect(entity)} onDoubleClick={() => onOpen(entity)} onKeyDown={event => {
        if (event.key === 'ArrowDown') {event.preventDefault(); focusAt(shown[i + 1]?.entity.id)}
        if (event.key === 'ArrowUp') {event.preventDefault(); focusAt(shown[i - 1]?.entity.id)}
        if (event.key === 'ArrowRight' && entity.kind !== 'file') {event.preventDefault(); if (!expanded.has(entity.id)) toggle(entity.id); else focusAt(shown[i+1]?.entity.id)}
        if (event.key === 'ArrowLeft') {event.preventDefault(); if (expanded.has(entity.id)) toggle(entity.id); else focusAt(entity.parent_id)}
        if (event.key === 'Home') {event.preventDefault(); focusAt(shown[0]?.entity.id)}
        if (event.key === 'End') {event.preventDefault(); focusAt(shown.at(-1)?.entity.id)}
        if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); onSelect(entity)}
      }}>
        {entity.kind !== 'file' ? <button tabIndex={-1} className={`tree-toggle ${expanded.has(entity.id) ? 'expanded' : ''}`} aria-label={`Toggle ${entity.label}`} onClick={e => {e.stopPropagation(); toggle(entity.id)}}><Icon name="chevron" size={12}/></button> : <span className="tree-spacer"/>}<Icon name={entity.kind === 'file' ? 'file' : 'folder'} size={16}/><span className="tree-label">{needle ? entity.path : entity.label}</span>{entity.metadata.excluded === true && <span title="Excluded from source preview">⊘</span>}
      </div>)}
    </div>{shown.length === 0 && <p className="muted pad">No matching paths.</p>}{visible.length > limit && <p className="muted pad">Showing {limit} paths. <button className="btn small" onClick={() => setLimit(n => n+500)}>Show more</button></p>}</>
}
