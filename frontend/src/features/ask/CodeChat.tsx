import { useState } from 'react'
import { renderMarkdown } from './markdown'
import { useChatState } from './useChatState'
import { ChatModal } from './ChatModal'
import type { SlotProps } from '../../contexts/SlotRegistry'
import { Icon } from '../../components/ui/Icon'

export default function CodeChat({ projectId, snapshotId, selectedEntity, files }: SlotProps) {
  const [open, setOpen] = useState(false)
  const [prefill, setPrefill] = useState<string | undefined>()

  const selectedFile = selectedEntity?.fileId
    ? files.find(f => f.id === selectedEntity.fileId)
    : null

  const selectedFolderPath =
    !selectedFile && selectedEntity?.path && selectedEntity.path !== '.'
      ? selectedEntity.path
      : undefined

  const scope = selectedFile ? 'file' : selectedFolderPath ? 'folder' : 'repository'
  const scopeLabel = selectedFile
    ? selectedFile.path
    : selectedFolderPath
      ? selectedFolderPath + '/'
      : 'Entire repository'
  const scopeIcon: 'file' | 'folder' = selectedFile ? 'file' : 'folder'

  const state = useChatState({ projectId, snapshotId, fileId: selectedFile?.id, scope, folderPath: selectedFolderPath })
  const lastAssistant = state.messages.filter(m => m.role === 'assistant').at(-1)

  function openWith(prefillQuestion?: string) {
    setPrefill(prefillQuestion)
    setOpen(true)
  }

  return (
    <>
      {/* ── Ask page trigger area ── */}
      <div className="codechat-trigger">
        <div className="codechat-header-row">
          <div>
            <p className="eyebrow">AI CODE ASSISTANT</p>
            <h2 style={{ margin: 0 }}>Ask about this codebase</h2>
            <p style={{ fontSize: 13, marginTop: 6, marginBottom: 0 }}>
              Ask about code structure, imports, API design, tech stack, and logic.
              {selectedFile && <> Scoped to <strong>{selectedFile.path}</strong>.</>}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexShrink: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {selectedFile && (
              <button className="btn small" onClick={() => openWith(`Explain what ${selectedFile.path} does and its role in the codebase.`)}>
                <Icon name="file" size={14} /> Explain this file
              </button>
            )}
            {selectedFolderPath && (
              <button className="btn small" onClick={() => openWith(`Explain what the ${selectedFolderPath} folder contains and its purpose.`)}>
                <Icon name="folder" size={14} /> Explain this folder
              </button>
            )}
            <button className="btn primary" onClick={() => openWith()}>
              <Icon name="spark" /> Open Code Canopy
            </button>
          </div>
        </div>

        {lastAssistant && (
          <div className="codechat-recent">
            <p className="muted" style={{ fontSize: 12, margin: '0 0 6px' }}>Last answer:</p>
            <div className="md-body" style={{ fontSize: 13 }}>
              {renderMarkdown(
                lastAssistant.content.length > 300
                  ? lastAssistant.content.slice(0, 300) + '…'
                  : lastAssistant.content
              )}
            </div>
            <button className="btn small" style={{ marginTop: 10 }} onClick={() => openWith()}>
              Continue conversation
            </button>
          </div>
        )}
      </div>

      {open && (
        <ChatModal
          state={state}
          scopeLabel={scopeLabel}
          scopeIcon={scopeIcon}
          prefillQuestion={prefill}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  )
}
