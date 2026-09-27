/**
 * Shared chat state hook used by both CodeChat (Ask page) and ChatButton (map header).
 * Handles: persistence (localStorage 24h TTL), API calls, copy, history management.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { request, snapshotPath } from '../../services/v1/api'

import type { AskResponse, SourceCitation } from '../../types/v1/chat'
export type { SourceCitation } from '../../types/v1/chat'

export interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceCitation[]
  limitations?: string[]
  hint?: string          // context_hint stored per assistant message
}


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
  const apiHistory = history.slice(-10).map(({ role, content }) => ({ role, content: content.slice(0, 8000) }))
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
  const key = storageKey(projectId, snapshotId)
  const [chat, setChat] = useState(() => ({key, messages: projectId && snapshotId ? loadStored(projectId, snapshotId) : []}))
  const messages = chat.key === key ? chat.messages : []
  const setMessages = useCallback((messages: ChatMsg[]) => setChat({key, messages}), [key])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState<number | null>(null)  // index of copied message
  const abortRef = useRef<AbortController | null>(null)
  const requestVersion = useRef(0)

  // Re-load from storage when projectId/snapshotId change (workspace switch)
  useEffect(() => {
    if (projectId && snapshotId) {
      setMessages(loadStored(projectId, snapshotId))
    }
  }, [projectId, snapshotId, setMessages])

  // Persist messages to localStorage whenever they change
  useEffect(() => {
    if (projectId && snapshotId && chat.key === key && messages.length > 0) {
      saveStored(projectId, snapshotId, messages)
    }
  }, [messages, projectId, snapshotId, chat.key, key])

  useEffect(() => {
    setLoading(false); setError(''); setInput('')
    return () => {requestVersion.current += 1; abortRef.current?.abort()}
  }, [projectId, snapshotId, fileId, folderPath, scope])

  const submit = useCallback(async () => {
    const q = input.trim()
    if (!q || loading || !projectId || !snapshotId) return
    setInput('')
    setError('')
    const next: ChatMsg[] = [...messages, { role: 'user', content: q }]
    setMessages(next)
    setLoading(true)
    const version = ++requestVersion.current
    abortRef.current = new AbortController()
    try {
      const res = await sendQuestion(
        projectId, snapshotId, q, messages,
        fileId, scope, folderPath, abortRef.current.signal,
      )
      if (requestVersion.current !== version) return
      setMessages([...next, { role: 'assistant', content: res.answer, hint: res.context_hint, sources: res.sources, limitations: res.limitations }])
    } catch (e: unknown) {
      if (requestVersion.current !== version) return
      setMessages(messages); setInput(q)
      if (e instanceof Error && e.name === 'AbortError') return
      setError(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      if (requestVersion.current === version) setLoading(false)
    }
  }, [input, loading, projectId, snapshotId, messages, fileId, scope, folderPath, setMessages])

  const cancel = useCallback(() => abortRef.current?.abort(), [])

  const clear = useCallback(() => {
    requestVersion.current += 1; abortRef.current?.abort(); setLoading(false)
    setMessages([])
    setError('')
    clearStored(projectId, snapshotId)
  }, [projectId, snapshotId, setMessages])

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
