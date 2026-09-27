/**
 * Shared chat state hook used by both CodeChat (Ask page) and ChatButton (map header).
 * Handles: persistence (localStorage 24h TTL), API calls, copy, history management.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { request, snapshotPath } from '../../services/v1/api'

export interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
  hint?: string          // context_hint stored per assistant message
}

interface AskResponse { answer: string; context_hint: string }

interface StoredChat {
  messages: ChatMsg[]
  expiresAt: number      // unix ms — matches snapshot 24h TTL
}

const CHAT_TTL_MS = 23 * 60 * 60 * 1000  // 23h (slightly under snapshot 24h)

function storageKey(projectId: string, snapshotId: string) {
  return `codecanopy_chat_${projectId}_${snapshotId}`
}

function loadStored(projectId: string, snapshotId: string): ChatMsg[] {
  try {
    const raw = localStorage.getItem(storageKey(projectId, snapshotId))
    if (!raw) return []
    const parsed: StoredChat = JSON.parse(raw)
    if (Date.now() > parsed.expiresAt) {
      localStorage.removeItem(storageKey(projectId, snapshotId))
      return []
    }
    return parsed.messages ?? []
  } catch { return [] }
}

function saveStored(projectId: string, snapshotId: string, messages: ChatMsg[]) {
  try {
    const data: StoredChat = { messages, expiresAt: Date.now() + CHAT_TTL_MS }
    localStorage.setItem(storageKey(projectId, snapshotId), JSON.stringify(data))
  } catch { /* storage full – silent */ }
}

function clearStored(projectId: string, snapshotId: string) {
  try { localStorage.removeItem(storageKey(projectId, snapshotId)) } catch { /* ignore */ }
}

function sendQuestion(
  projectId: string, snapshotId: string,
  question: string, history: ChatMsg[],
  fileId: string | undefined,
  scope: string,
  folderPath: string | undefined,
  signal: AbortSignal,
): Promise<AskResponse> {
  // Strip hint field before sending — backend only needs role + content
  const apiHistory = history.map(({ role, content }) => ({ role, content }))
  return request<AskResponse>(
    snapshotPath(projectId, snapshotId) + '/chat',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question, history: apiHistory,
        file_id: fileId ?? null,
        folder_path: folderPath ?? null,
        scope,
      }),
      signal,
    },
  )
}

export interface ChatStateOptions {
  projectId: string
  snapshotId: string
  fileId?: string
  scope: string
  folderPath?: string
}

export function useChatState({ projectId, snapshotId, fileId, scope, folderPath }: ChatStateOptions) {
  const [messages, setMessages] = useState<ChatMsg[]>(() =>
    projectId && snapshotId ? loadStored(projectId, snapshotId) : []
  )
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState<number | null>(null)  // index of copied message
  const abortRef = useRef<AbortController | null>(null)

  // Re-load from storage when projectId/snapshotId change (workspace switch)
  useEffect(() => {
    if (projectId && snapshotId) {
      setMessages(loadStored(projectId, snapshotId))
    }
  }, [projectId, snapshotId])

  // Persist messages to localStorage whenever they change
  useEffect(() => {
    if (projectId && snapshotId && messages.length > 0) {
      saveStored(projectId, snapshotId, messages)
    }
  }, [messages, projectId, snapshotId])

  const submit = useCallback(async () => {
    const q = input.trim()
    if (!q || loading || !projectId || !snapshotId) return
    setInput('')
    setError('')
    const next: ChatMsg[] = [...messages, { role: 'user', content: q }]
    setMessages(next)
    setLoading(true)
    abortRef.current = new AbortController()
    try {
      const res = await sendQuestion(
        projectId, snapshotId, q, messages,
        fileId, scope, folderPath, abortRef.current.signal,
      )
      setMessages([...next, { role: 'assistant', content: res.answer, hint: res.context_hint }])
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') return
      setError(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }, [input, loading, projectId, snapshotId, messages, fileId, scope, folderPath])

  const cancel = useCallback(() => abortRef.current?.abort(), [])

  const clear = useCallback(() => {
    setMessages([])
    setError('')
    clearStored(projectId, snapshotId)
  }, [projectId, snapshotId])

  const copyMessage = useCallback((index: number, content: string) => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(index)
      setTimeout(() => setCopied(null), 2000)
    }).catch(() => {/* clipboard denied */})
  }, [])

  const exportChat = useCallback(() => {
    const text = messages
      .map(m => `[${m.role.toUpperCase()}]\n${m.content}`)
      .join('\n\n---\n\n')
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `grepo-chat-${Date.now()}.txt`
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }, [messages])

  return {
    messages, input, setInput,
    loading, error, copied,
    submit, cancel, clear, copyMessage, exportChat,
  }
}
