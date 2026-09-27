# Task 03: Change Impact Honesty Fix — Session Summary

**Date:** 2026-09-27
**Task ID:** `43a21cfe5525f4493c6c6e6bf29c5605`
**Bobcoins spent:** 2.02
**Context used:** 46.0k / 270.0k (17%)
**Todos:** 4/4

## Why this session exists

Task 02 shipped a working dependency graph but left a defect that made the
change-impact feature look dead on first open. The bug was found by
independent verification after the session closed, not by the task itself.

## The defect

`compute_impact` returned an empty list for every subject except an explicitly
selected file:

```
path=None            impact=0
path='.'             impact=0
path='pkg'           impact=0
path='pkg/utils.py'  impact=2   (the only working case)
```

A user opening the Dependencies slot with nothing selected saw "0 files would be
affected" on a repository with a real dependency chain, and `limitations` was
empty — so the failure was not even disclosed. For a project whose entire
argument is *we do not show you a confident answer we cannot prove*, a silent
empty result was the worst possible output.

## The fix

Three cases are now distinguished in `build_dependencies` before the walk runs:

1. **No subject, or the repository root** — the "affected by" set is undefined.
   Return empty **and** state that impact requires selecting a file or folder.
2. **A subject covering the whole snapshot** — same disclosure. A full-repo
   impact list is meaningless, not maximal.
3. **Otherwise** — walk normally, preserving existing truncation behaviour.

`compute_impact` itself is unchanged and stays directly callable with a file
path.

## Result

```
122 passed  (118 + 4 new, 0 regressions)

path=None            impact=0  lim=[Change impact requires a specific file or folder...]
path='.'             impact=0  lim=[same]
path='pkg'           impact=1  lim=[]
path='pkg/utils.py'  impact=2  lim=[]
```

The first two now disclose why they are empty. The last two are unchanged and
still correct. An empty answer with a stated reason is a valid answer.

## The brief's diagnosis was wrong

The brief asserted the BFS was seeded with every file under `'.'`, excluding
them all. The actual cause: `'.'` produced the prefix `'./'`, which matches no
real path, so the seed set was **empty** and the walk never started. Different
mechanism, identical symptom.

Bob identified this and corrected it during implementation. Two briefs, two
corrections — the model's audit of the spec was load-bearing both times.

## The brief also suspected the folder case was broken. It was not.

`compute_impact` seeds correctly with the folder's own files and excludes them
from results, returning only external importers. This was verified and reported
as already working rather than silently "fixed" — the honest answer to a
suspected second bug, and the reason `path='pkg'` still returns exactly 1.
