import { useState } from 'react'
import { renderMarkdown } from './markdown'
import { useChatState } from './useChatState'
import { ChatModal } from './ChatModal'
import type { SlotProps } from '../../contexts/SlotRegistry'
import { Icon } from '../../components/ui/Icon'

/**
 * Slice `text` for the preview panel, cutting at the last newline that falls within
 * `maxChars`.  This avoids mid-line truncation that would break table or code-fence
 * detection in the markdown renderer.
 */
function previewContent(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text
  const slice = text.slice(0, maxChars)
  const lastNl = slice.lastIndexOf('\n')
  return (lastNl > 0 ? slice.slice(0, lastNl) : slice) + '…'
}

/** Extract the greeting text from the slot response, if it was set. */
function slotGreeting(request: SlotProps['request']): string {
  if (request.status !== 'ready') return ''
  const d = request.data as { answer?: string } | null
  return (d && typeof d.answer === 'string') ? d.answer : ''
}

export default function CodeChat({ projectId, snapshotId, selectedEntity, files, request }: SlotProps) {
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
              <Icon name="spark" /> Open Grepo
            </button>
          </div>
        </div>

        {/* Greeting from the slot endpoint — shown only before the first conversation */}
        {!lastAssistant && slotGreeting(request) && (
          <div className="codechat-greeting" data-testid="ask-slot-greeting">
            <p style={{ fontSize: 13, marginTop: 14, marginBottom: 0, color: 'var(--color-muted, #57606a)' }}>
              {slotGreeting(request)}
            </p>
          </div>
        )}

        {lastAssistant && (
          <div className="codechat-recent">
            <p className="muted" style={{ fontSize: 12, margin: '0 0 6px' }}>Last answer:</p>
            <div className="md-body" style={{ fontSize: 13 }}>
              {renderMarkdown(previewContent(lastAssistant.content, 300))}
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
