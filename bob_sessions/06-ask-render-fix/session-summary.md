# Task 06: Ask Response Rendering Fix - Session Summary

**Date:** 2026-09-27
**Task ID:** `a81ad5b9d10223df4ea559efdeadb608`
**Bobcoins spent:** 5.50
**Context used:** 79.6k / 270.0k (29%)
**Todos:** 9

## What was reported broken

A real answer rendered in the chat panel showed its opening label three
times, followed by a markdown table that stopped partway through. Content was
correct; only the rendering was wrong.

## The actual cause

The brief assumed a streaming bug: chunk concatenation duplicating labels and
closing blocks mid-stream. That was wrong.

There is no streaming. The chat state hook has no chunk or delta handling; the
response arrives as one string. The renderer emits each label exactly once.

The real cause was the 300-character preview in the last-answer panel. It
sliced the response at a hard character boundary, cutting a markdown table in
half. The tokenizer received a pipe-delimited header row with no separator
following it, which per the markdown spec is not a table, so it fell through to
plain text and printed the pipe characters literally. The repeated label was
the plain-text fallback re-printing the opening lines, not a duplicated render.

## What changed

**Preview slicing** - the last-answer preview now truncates at the last
newline before the character limit, so the renderer never receives a line cut
in half.

**Partial table** - a pipe-delimited line at end of input, or one followed by a
blank line where the separator has not arrived yet, is emitted as a table token
with empty rows rather than falling through to raw text.

**Unclosed fence** - the index advance after a closing fence is now bounded, so
a fence left open at end of input still emits its token.

**Inline guards** - minimum-length checks stop single characters such as `*`,
`**` and a backtick from being read as formatting markers.

## Result

```
frontend  33 passed  (29 + 4 new)
backend   134 passed
type check clean
```

The new test feeds a deliberately chunked response containing a three-row
table split across three chunks and a fenced code block split across two. It
asserts the label appears once, all three rows render, the code block
completes, and no raw HTML is injected.

## Security check

The renderer uses JSX only. React escapes text content. Verified by search for
`dangerouslySetInnerHTML`, `innerHTML`, `document.write` and similar across the
ask feature: no matches.

## Note on the brief

The brief's hypothesis was wrong and the agent said so rather than building a
streaming fix for a non-existent streaming path. It verified the renderer's
control flow first, reported that the label renders exactly once, and fixed the
real cause instead. Correcting a wrong premise is worth more than complying
with it.
