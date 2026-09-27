/**
 * Minimal markdown renderer for AI chat responses.
 * Handles: headings, bold, inline code, fenced code blocks, lists, tables, horizontal rules.
 * Designed to render partial/streaming content safely — an unclosed block renders what it has.
 * No external dependencies. Never injects raw HTML.
 */
import React from 'react'

interface Token {
  type: 'fence' | 'heading' | 'hr' | 'li' | 'table' | 'blank' | 'text'
  raw: string
  level?: number        // 1–6 as written; rendered level clamped to 1–3
  ordered?: boolean
  lang?: string
  // table-specific
  headers?: string[]
  rows?: string[][]
}

/** Split a pipe-delimited table row into trimmed cells, ignoring leading/trailing pipes. */
function splitRow(line: string): string[] {
  return line.replace(/^\||\|$/g, '').split('|').map(c => c.trim())
}

/** Return true if every cell in the row is a separator like `---`, `:---`, `---:` */
function isSeparatorRow(cells: string[]): boolean {
  return cells.length > 0 && cells.every(c => /^:?-{2,}:?$/.test(c.trim()))
}

/**
 * Tokenise markdown text.  Handles partial/truncated input:
 * - An unclosed fenced code block emits a fence token with all accumulated body lines.
 * - A table header line with no following separator row emits a partial table (no rows).
 * - Mid-table truncation (truncated after the separator) emits whatever rows arrived.
 */
function tokenize(md: string): Token[] {
  const lines = md.split('\n')
  const tokens: Token[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Fenced code block — emit even if the closing ``` never arrives
    if (/^```/.test(line)) {
      const lang = line.slice(3).trim()
      const body: string[] = []
      i++
      while (i < lines.length && !/^```/.test(lines[i])) {
        body.push(lines[i])
        i++
      }
      tokens.push({ type: 'fence', raw: body.join('\n'), lang })
      if (i < lines.length) i++ // skip closing ``` when present
      continue
    }

    // Table: pipe-delimited header line followed by a separator line
    if (/\|/.test(line)) {
      const headerCells = splitRow(line)
      if (headerCells.length > 0) {
        const nextLine = lines[i + 1] ?? ''
        const sepCells = splitRow(nextLine)
        if (isSeparatorRow(sepCells)) {
          // Confirmed full table — collect all following pipe rows
          const rows: string[][] = []
          i += 2 // skip header + separator
          while (i < lines.length && /\|/.test(lines[i])) {
            rows.push(splitRow(lines[i]))
            i++
          }
          tokens.push({ type: 'table', raw: line, headers: headerCells, rows })
          continue
        }
        // Partial table: header line is the last line, or separator is still arriving.
        // Emit a table token with no rows so the header renders as a proper table
        // rather than raw pipe-delimited text.
        if (i + 1 >= lines.length || nextLine.trim() === '') {
          tokens.push({ type: 'table', raw: line, headers: headerCells, rows: [] })
          i++
          continue
        }
      }
    }

    // Heading — support all 6 levels; renderer clamps 4-6 → h3 styling
    const hm = line.match(/^(#{1,6})\s+(.*)$/)
    if (hm) {
      tokens.push({ type: 'heading', raw: hm[2], level: hm[1].length })
      i++
      continue
    }

    // Horizontal rule — must not be a table separator (already handled above)
    if (/^---+$/.test(line.trim())) {
      tokens.push({ type: 'hr', raw: line })
      i++
      continue
    }

    // Ordered list item
    const olm = line.match(/^\d+\.\s+(.*)$/)
    if (olm) {
      tokens.push({ type: 'li', raw: olm[1], ordered: true })
      i++
      continue
    }

    // Unordered list item
    const ulm = line.match(/^[-*]\s+(.*)$/)
    if (ulm) {
      tokens.push({ type: 'li', raw: ulm[1], ordered: false })
      i++
      continue
    }

    // Blank line
    if (line.trim() === '') {
      tokens.push({ type: 'blank', raw: '' })
      i++
      continue
    }

    tokens.push({ type: 'text', raw: line })
    i++
  }
  return tokens
}

/**
 * Apply inline formatting: **bold**, `code`, *italic*.
 * Only matches complete markers — an unclosed marker renders as plain text,
 * so a truncated chunk never produces garbled output.
 */
function inline(text: string): React.ReactNode[] {
  // Only match markers that are both opened and properly closed.
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g)
  return parts.map((part, idx) => {
    if (part.length > 4 && part.startsWith('**') && part.endsWith('**'))
      return <strong key={idx}>{part.slice(2, -2)}</strong>
    if (part.length > 2 && part.startsWith('`') && part.endsWith('`'))
      return <code key={idx} className="md-inline-code">{part.slice(1, -1)}</code>
    if (part.length > 2 && part.startsWith('*') && part.endsWith('*'))
      return <em key={idx}>{part.slice(1, -1)}</em>
    return part
  })
}

export function renderMarkdown(md: string): React.ReactNode {
  const tokens = tokenize(md)
  const nodes: React.ReactNode[] = []
  let i = 0

  while (i < tokens.length) {
    const t = tokens[i]

    if (t.type === 'fence') {
      nodes.push(
        <pre key={i} className="md-fence">
          <code className={t.lang ? `md-lang-${t.lang}` : ''}>{t.raw}</code>
        </pre>
      )
      i++
      continue
    }

    if (t.type === 'table') {
      nodes.push(
        <div key={i} className="md-table-wrap">
          <table className="md-table">
            <thead>
              <tr>{(t.headers ?? []).map((h, hi) => <th key={hi}>{inline(h)}</th>)}</tr>
            </thead>
            <tbody>
              {(t.rows ?? []).map((row, ri) => (
                <tr key={ri}>
                  {row.map((cell, ci) => <td key={ci}>{inline(cell)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      i++
      continue
    }

    if (t.type === 'heading') {
      // clamp h4/h5/h6 down to h3 so we always use a valid HTML tag + style
      const renderLevel = Math.min(t.level ?? 2, 3) as 1 | 2 | 3
      const Tag = `h${renderLevel}` as 'h1' | 'h2' | 'h3'
      nodes.push(<Tag key={i} className={`md-h${renderLevel}`}>{inline(t.raw)}</Tag>)
      i++
      continue
    }

    if (t.type === 'hr') {
      nodes.push(<hr key={i} className="md-hr" />)
      i++
      continue
    }

    if (t.type === 'blank') {
      i++
      continue
    }

    // Collect consecutive list items of same type
    if (t.type === 'li') {
      const ordered = t.ordered
      const items: React.ReactNode[] = []
      while (i < tokens.length && tokens[i].type === 'li' && tokens[i].ordered === ordered) {
        items.push(<li key={i}>{inline(tokens[i].raw)}</li>)
        i++
      }
      const ListTag = ordered ? 'ol' : 'ul'
      nodes.push(<ListTag key={`list-${i}`} className="md-list">{items}</ListTag>)
      continue
    }

    // Plain text paragraph — collect consecutive text lines
    if (t.type === 'text') {
      const lines: string[] = []
      while (i < tokens.length && tokens[i].type === 'text') {
        lines.push(tokens[i].raw)
        i++
      }
      nodes.push(
        <p key={`p-${i}`} className="md-p">
          {lines.flatMap((line, li) => [
            ...inline(line),
            li < lines.length - 1 ? <br key={`br-${li}`} /> : null,
          ])}
        </p>
      )
      continue
    }

    i++
  }

  return <>{nodes}</>
}
