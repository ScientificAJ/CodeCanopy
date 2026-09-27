/**
 * Standalone chat trigger for use anywhere in the workspace (e.g. map header).
 * Reads context from WorkspaceContext — no prop drilling needed.
 */
import { useState } from 'react'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { Icon } from '../ui/Icon'
import { useChatState } from '../../features/ask/useChatState'
import { ChatModal } from '../../features/ask/ChatModal'

export function ChatButton({ label = 'GREPO' }: { label?: string }) {
  const ws = useWorkspace()
  const [open, setOpen] = useState(false)
  const [prefill, setPrefill] = useState<string | undefined>()

  const projectId = ws.projectId ?? ''
  const snapshotId = ws.snapshot?.id ?? ''

  const selectedFile = ws.selectedEntity?.fileId
    ? ws.files.find(f => f.id === ws.selectedEntity?.fileId)
    : null

  const selectedFolderPath =
    !selectedFile && ws.selectedEntity?.path && ws.selectedEntity.path !== '.'
      ? ws.selectedEntity.path
      : undefined

  const scope = selectedFile ? 'file' : selectedFolderPath ? 'folder' : 'repository'
  const scopeLabel = selectedFile
    ? selectedFile.path
    : selectedFolderPath
      ? selectedFolderPath + '/'
      : 'Entire repository'
  const scopeIcon: 'file' | 'folder' = selectedFile ? 'file' : 'folder'

  const state = useChatState({ projectId, snapshotId, fileId: selectedFile?.id, scope, folderPath: selectedFolderPath })

  function openWith(prefillQuestion?: string) {
    setPrefill(prefillQuestion)
    setOpen(true)
  }

  return (
    <>
      <button
        className="btn small"
        onClick={() => openWith()}
        disabled={!projectId || !snapshotId}
      >
        <Icon name="spark" size={14} /> {label}
      </button>

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
