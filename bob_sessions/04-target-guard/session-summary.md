# Task 04: Dependency Edge Target Guard - Session Summary

**Date:** 2026-09-27
**Task ID:** `40a1564f2628dad5e9d0e678e46663c8`

## What this task fixed

The dependency edge verifier had five guards. All five validated the
citation - the source side of an edge. None validated the target.

Attack: an edge whose evidence is entirely legitimate (real file, real line,
correct content hash, and that line genuinely is an import statement) but whose
target file id names a file that does not exist in the snapshot. Before this
task the verifier returned `verified` and the edge was drawn.

## What was added

Guard 0, inserted before the five existing citation guards. For every edge it
rejects when the target file id is null, and rejects when
`get_file_record` raises for the target id. The reason names the target path
and file id.

No existing guard was modified. No new imports were required.

## Null target path

The edge model permits a null target file id for external or unresolved
targets. That path was previously invisible to all five citation guards and
passed them silently. Guard 0 catches it. This widened the original defect
beyond what the brief described.

## Result

```
128 passed  (122 + 6 new)

A  honest graph                     verified
B  cited line is not an import      unverified
C  citation past end of file        unverified
D  citation valid, target fictional unverified   <- fixed by this task
E  file id from another snapshot    unverified
F  null target (external)           unverified   <- added by this task
```

Full graph on an honest snapshot: 2 verified, 0 unverified.

## Source endpoint

Guard 1 already validates the evidence file id, which is the source endpoint.
No source-side gap exists. The guard was not duplicated.
