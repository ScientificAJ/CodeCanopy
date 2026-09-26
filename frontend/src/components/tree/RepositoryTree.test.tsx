import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { RepositoryTree } from './RepositoryTree'
import type { GraphEntity } from '../../types/v1'
afterEach(cleanup)
const entities: GraphEntity[] = [{id:'root',kind:'repository',label:'repo',path:'.',child_count:1,metadata:{}},{id:'folder',kind:'folder',label:'src',path:'src',parent_id:'root',child_count:1,metadata:{}},{id:'file',file_id:'file',kind:'file',label:'app.py',path:'src/app.py',parent_id:'folder',child_count:0,metadata:{}}]
it('reveals a deep selection and preserves canonical identity when searched', () => {
  const select = vi.fn(); render(<RepositoryTree entities={entities} selectedId="file" onSelect={select} onOpen={vi.fn()}/>)
  expect(screen.getByRole('treeitem',{name:'app.py'}).getAttribute('aria-selected')).toBe('true')
  fireEvent.change(screen.getByRole('textbox'),{target:{value:'app.py'}})
  const item = screen.getByRole('treeitem',{name:'src/app.py'}); fireEvent.keyDown(item,{key:'Enter'})
  expect(select).toHaveBeenCalledWith(entities[2])
})
it('supports keyboard folder expansion', () => {
  render(<RepositoryTree entities={entities} onSelect={vi.fn()} onOpen={vi.fn()}/>)
  const folder = screen.getByRole('treeitem',{name:'src'}); fireEvent.keyDown(folder,{key:'ArrowRight'})
  expect(screen.getByRole('treeitem',{name:'app.py'})).toBeDefined()
})
