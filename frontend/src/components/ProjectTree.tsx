import { useState } from 'react'
import type { File as ProjectFile } from '../types/codebase'

interface TreeNode {
  name: string
  path: string
  kind: 'directory' | 'file'
  children: TreeNode[]
  file?: ProjectFile
}

interface MutableTreeNode extends Omit<TreeNode, 'children'> {
  children: Map<string, MutableTreeNode>
}

interface ProjectTreeProps {
  files: ProjectFile[]
  selectedPath: string | null
  onSelect: (path: string) => void
}

function buildTree(files: ProjectFile[]): TreeNode[] {
  const roots = new Map<string, MutableTreeNode>()

  for (const file of files) {
    const parts = file.path.split('/').filter(Boolean)
    let siblings = roots
    let currentPath = ''

    parts.forEach((part, index) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part
      const isFile = index === parts.length - 1
      let node = siblings.get(part)
      if (!node) {
        node = {
          name: part,
          path: currentPath,
          kind: isFile ? 'file' : 'directory',
          children: new Map(),
          ...(isFile ? { file } : {}),
        }
        siblings.set(part, node)
      }
      siblings = node.children
    })
  }

  function sortNodes(nodes: Map<string, MutableTreeNode>): TreeNode[] {
    return [...nodes.values()]
      .sort((left, right) => {
        if (left.kind !== right.kind) return left.kind === 'directory' ? -1 : 1
        return left.name.localeCompare(right.name)
      })
      .map((node) => ({
        name: node.name,
        path: node.path,
        kind: node.kind,
        children: sortNodes(node.children),
        ...(node.file ? { file: node.file } : {}),
      }))
  }

  return sortNodes(roots)
}

export default function ProjectTree({ files, selectedPath, onSelect }: ProjectTreeProps) {
  const tree = buildTree(files)

  return (
    <ul className="project-tree">
      {tree.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      ))}
    </ul>
  )
}

interface TreeItemProps {
  node: TreeNode
  depth: number
  selectedPath: string | null
  onSelect: (path: string) => void
}

function TreeItem({ node, depth, selectedPath, onSelect }: TreeItemProps) {
  const [isExpanded, setIsExpanded] = useState(depth === 0)
  const paddingLeft = `${10 + depth * 14}px`

  return (
    <li className="project-tree__item">
      {node.kind === 'directory' ? (
        <>
          <button
            className="project-tree__row project-tree__row--directory"
            type="button"
            style={{ paddingLeft }}
            aria-expanded={isExpanded}
            onClick={() => setIsExpanded((expanded) => !expanded)}
          >
            <span className="project-tree__chevron" aria-hidden="true">{isExpanded ? '⌄' : '›'}</span>
            <span className="project-tree__folder" aria-hidden="true" />
            <span className="project-tree__name">{node.name}</span>
          </button>
          {isExpanded && node.children.length > 0 && (
            <ul className="project-tree__children">
              {node.children.map((child) => (
                <TreeItem
                  key={child.path}
                  node={child}
                  depth={depth + 1}
                  selectedPath={selectedPath}
                  onSelect={onSelect}
                />
              ))}
            </ul>
          )}
        </>
      ) : (
        <button
          className={`project-tree__row project-tree__row--file${selectedPath === node.path ? ' is-selected' : ''}`}
          type="button"
          style={{ paddingLeft }}
          aria-current={selectedPath === node.path ? 'page' : undefined}
          onClick={() => onSelect(node.path)}
        >
          <span className="project-tree__chevron" aria-hidden="true" />
          <span className="project-tree__file-mark" aria-hidden="true">
            {node.name.includes('.') ? node.name.split('.').pop()?.slice(0, 3).toUpperCase() : 'FILE'}
          </span>
          <span className="project-tree__name">{node.name}</span>
        </button>
      )}
    </li>
  )
}