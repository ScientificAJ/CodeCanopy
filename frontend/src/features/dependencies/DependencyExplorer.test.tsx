import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { SlotProps } from '../../contexts/SlotRegistry'
import { DependencyExplorer } from './DependencyExplorer'
import { projectGraph, reachable } from './graph'
import type { DependencyResult, DependencyEdge } from './types'

const nodes: DependencyResult['nodes'] = [
  {id:'a',kind:'file',label:'a.py',path:'a.py',file_id:'a',line_start:1,line_end:1},
  {id:'b',kind:'file',label:'b.py',path:'b.py',file_id:'b',line_start:1,line_end:1},
  {id:'f',kind:'function',label:'start',path:'a.py',file_id:'a',line_start:2,line_end:4},
  {id:'g',kind:'function',label:'helper',path:'b.py',file_id:'b',line_start:3,line_end:5},
]
function edge(source: string, target: string, id = source + target): DependencyEdge {
  return {id,source_id:source,target_id:target,kind:'calls',file_id:'a',line_start:4,line_end:4,basis:'static_binding'}
}
const result: DependencyResult = {schema_version:'1.0',snapshot_id:'snap',nodes,edges:[edge('f','g')],unresolved:[],coverage:{inventoried_files:2,analyzed_files:2,unsupported_files:0,unresolved_count:0,truncated:false,limitations:['Static bindings only.']}}
function props(request: SlotProps<DependencyResult>['request'], openSource = vi.fn()) {
  return {
    snapshotId:'snap',projectId:'project',request,openSource,availability:'connected',
    snapshot:{schema_version:'1.0',id:'snap',project_id:'project',source:{kind:'zip'},manifest_hash:'hash',policy_version:'1.0',created_at:'2099-01-01'},
    selectedEntity:null,files:[],entities:[],graph:null,capabilities:null,
    viewState:{focusedView:'overview',mapCamera:{x:0,y:0,scale:1}},
    selectEntity:vi.fn(),navigate:vi.fn(),
  } satisfies SlotProps<DependencyResult>
}
describe('dependency graph', () => {
  it('projects function calls to file connections and hides same-file calls', () => {
    const graph = projectGraph({...result,edges:[...result.edges,edge('f','f')]}, 'file')
    expect(graph.edges.map(e => [e.source_id,e.target_id])).toEqual([['a','b']])
  })
  it('finds indirect impact and terminates cycles without including the selected item', () => {
    const reached = reachable('c',[edge('a','b'),edge('b','c'),edge('c','a')],true)
    expect([...reached.ids].sort()).toEqual(['a','b'])
    expect(reached.cycle).toBe(true)
  })
  it('bounds traversal and reports incomplete impact', () => {
    const reached = reachable('c',[edge('a','b'),edge('b','c')],true,1)
    expect([...reached.ids]).toEqual(['b'])
    expect(reached.truncated).toBe(true)
  })
})
describe('dependency explorer', () => {
  it('opens evidence at the actual call site and changes direction', () => {
    const open = vi.fn()
    render(<DependencyExplorer {...props({status:'ready',data:result},open)} />)
    fireEvent.click(screen.getByRole('button',{name:'Call at a.py:4'}))
    expect(open).toHaveBeenCalledWith('a',{start:4,end:4})
    fireEvent.change(screen.getByLabelText('Dependency level'),{target:{value:'function'}})
    fireEvent.change(screen.getByLabelText('Dependency focus'),{target:{value:'g'}})
    fireEvent.click(screen.getByRole('button',{name:'Potential impact'}))
    expect(screen.getByText('1 matching potentially affected items')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Filter connections'),{target:{value:'nothing'}})
    expect(screen.getByText('0 matching potentially affected items')).toBeTruthy()
  })
  it('explains unavailable coverage instead of claiming no dependencies', () => {
    render(<DependencyExplorer {...props({status:'ready',data:{...result,nodes:[],edges:[],coverage:{...result.coverage,analyzed_files:0}}})} />)
    expect(screen.getByText(/No files have supported dependency bindings/)).toBeTruthy()
  })
  it('renders request failure without stale results', () => {
    render(<DependencyExplorer {...props({status:'error',message:'Snapshot expired'})} />)
    expect(screen.getByRole('alert').textContent).toBe('Snapshot expired')
    expect(screen.queryByText('Follow the connections')).toBeNull()
  })
})
