/**
 * Standalone chat trigger for use anywhere in the workspace (e.g. map header).
 * Reads context from WorkspaceContext — no prop drilling needed.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkspace, selectionFor } from '../../contexts/WorkspaceContext'
import { Icon } from '../ui/Icon'
import { useChatState } from '../../features/ask/useChatState'
import { ChatModal } from '../../features/ask/ChatModal'

export function ChatButton({ label = 'GREPO' }: { label?: string }) {
  const ws = useWorkspace()
  const navigate = useNavigate()
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
          onOpenSource={source => {
            const entity = ws.entities.find(e => e.file_id === source.file_id)
            if (!entity || source.line_start < 1 || source.line_end < source.line_start) return
            ws.selectEntity({...selectionFor(entity), lineRange: {start: source.line_start, end: source.line_end}})
            navigate(`/p/${projectId}/s/${snapshotId}/map`)
          }}
        />
      )}
    </>
  )
}
