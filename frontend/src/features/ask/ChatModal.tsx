/**
 * Shared chat modal UI used by CodeChat (Ask page slot) and ChatButton (map header).
 * Features: localStorage persistence, copy button, context_hint pill, starter chips,
 *           "Explain this file" pre-fill, export, clear.
 */
import { useRef, useEffect, useState } from 'react'
import { Icon } from '../../components/ui/Icon'
import { renderMarkdown } from './markdown'
import type { useChatState } from './useChatState'

// Starter question chips shown when chat is empty
const STARTERS = [
  'What does this repository do?',
  'Where is the API defined?',
  'What tech stack and packages are used?',
  'How are files uploaded or imported?',
]

interface Props {
  state: ReturnType<typeof useChatState>
  scopeLabel: string
  scopeIcon: 'file' | 'folder'
  prefillQuestion?: string
  onClose(): void
}

export function ChatModal({ state, scopeLabel, scopeIcon, prefillQuestion, onClose }: Props) {
  const { messages, input, setInput, loading, error, copied, submit, cancel, clear, copyMessage, exportChat } = state
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [hintExpanded, setHintExpanded] = useState(false)

  useEffect(() => {
    setTimeout(() => textareaRef.current?.focus(), 60)
  }, [])

  // Pre-fill input when a prefill question is provided (e.g. "Explain this file")
  useEffect(() => {
    if (prefillQuestion && messages.length === 0) {
      setInput(prefillQuestion)
    }
  }, [prefillQuestion])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void submit() }
  }

  // Latest context hint from the most recent assistant message
  const lastHint = [...messages].reverse().find(m => m.role === 'assistant' && m.hint)?.hint

  return (
    <div
      className="codechat-backdrop"
      role="presentation"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="codechat-modal" role="dialog" aria-modal="true" aria-label="Grepo">

        {/* ── Header ── */}
        <div className="codechat-modal-header">
          <span className="codechat-modal-title">
            <Icon name="spark" size={16} /> Grepo
          </span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {messages.length > 0 && (
              <button className="btn small" onClick={exportChat}>
                <Icon name="download" size={14} /> Export
              </button>
            )}
            {messages.length > 0 && (
              <button className="btn small" onClick={clear}>Clear</button>
            )}
            <button className="icon-btn" aria-label="Close chat" onClick={onClose}>
              <Icon name="close" />
            </button>
          </div>
        </div>

        {/* ── Scope bar + context hint pill ── */}
        <div className="codechat-scope-bar">
          <Icon name={scopeIcon} size={13} />
          <span>{scopeLabel}</span>
          {lastHint && (
            <button
              className="codechat-hint-pill"
              onClick={() => setHintExpanded(x => !x)}
              aria-expanded={hintExpanded}
            >
              <Icon name="file" size={11} />
              {lastHint.split(':')[0]}
              <span className="codechat-hint-chevron">{hintExpanded ? '▴' : '▾'}</span>
            </button>
          )}
        </div>
        {hintExpanded && lastHint && (
          <div className="codechat-hint-expanded">{lastHint}</div>
        )}

        {/* ── Messages ── */}
        <div className="codechat-messages" aria-live="polite" aria-atomic="false">
          {messages.length === 0 && !loading && (
            <div className="codechat-empty">
              <Icon name="spark" size={32} />
              <p>Ask anything about the codebase.</p>
              <div className="codechat-starters">
                {STARTERS.map(s => (
                  <button
                    key={s}
                    className="codechat-starter-chip"
                    onClick={() => { setInput(s); setTimeout(() => textareaRef.current?.focus(), 0) }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`codechat-bubble codechat-bubble--${m.role}`}>
              <div className="codechat-bubble-header">
                <span className="codechat-role">{m.role === 'user' ? 'You' : 'Grepo AI'}</span>
                {m.role === 'assistant' && (
                  <button
                    className="codechat-copy-btn"
                    onClick={() => copyMessage(i, m.content)}
                    aria-label="Copy response"
                    title="Copy to clipboard"
                  >
                    {copied === i
                      ? <><Icon name="layers" size={12} /> Copied!</>
                      : <><Icon name="layers" size={12} /> Copy</>
                    }
                  </button>
                )}
              </div>
              {m.role === 'user'
                ? <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{m.content}</p>
                : <div className="md-body">{renderMarkdown(m.content)}</div>
              }
            </div>
          ))}

          {loading && (
            <div className="codechat-bubble codechat-bubble--assistant">
              <div className="codechat-bubble-header">
                <span className="codechat-role">Grepo AI</span>
              </div>
              <span className="codechat-typing">Thinking…</span>
            </div>
          )}

          {error && <p className="codechat-error" role="alert">{error}</p>}
          <div ref={bottomRef} />
        </div>

        {/* ── Composer ── */}
        <div className="codechat-composer">
          <textarea
            ref={textareaRef}
            className="codechat-textarea"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about the code… (Enter to send, Shift+Enter for newline)"
            rows={2}
            disabled={loading}
            aria-label="Chat input"
          />
          {loading
            ? <button className="btn" onClick={cancel}>Stop</button>
            : <button className="btn primary" onClick={submit} disabled={!input.trim()}>
                <Icon name="spark" size={15} /> Ask
              </button>
          }
        </div>

      </div>
    </div>
  )
}
