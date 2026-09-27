# Task 01: Deterministic Citation-Verified Summaries Engine - Session Summary

**Date:** 2026-09-27
**Task ID:** `8fd491fa551dbb392741b2f9461f964b`
**Workspace:** CodeCanopy (`ScientificAJ/CodeCanopy`)
**Status:** Complete and independently verified
**Bobcoin cost:** 7.83 of a 10-coin session budget
**Context used:** 103.1k / 270.0k (38%)

## Objective

Implement the `summaries.context-panel` integration slot so that every claim in
every file and folder summary carries a line-number citation, and so that a
verifier independently re-reads each cited line to confirm the claim is
supported before it is presented as fact.

The differentiating constraint: summaries are computed from AST facts already
produced at import time, so citations are true by construction. The verifier
then proves it independently. No model inference is required for the feature to
return a correct result.

## Architecture Decision

Deterministic-first was chosen over a model-generated summary. The reasons,
in order of weight:

1. **Truthfulness is structural, not promised.** A summary built from
   `syntax.json` and the file inventory cites lines that were read to produce
   the claim. A generated summary cites lines chosen after the fact.
2. **No hard dependency on a provider key.** The feature returns a complete,
   correct payload when no AI key is configured. Proven by test
   `test_summary_payload_is_valid_with_no_ai_key`.
3. **The contract already anticipated it.** `Evidence.basis` is defined as
   `observed | resolved | inferred`. Every claim this engine emits is
   `observed`, because each is read directly from the cited lines.
4. **Cost.** No inference means no per-summarisation token spend during a demo.

An `enrich()` seam was built in (`async def enrich(claims) -> str | None`,
returning `None` by default) so AI prose can be added later without touching
the engine. The constraint written into the brief was that enrichment may only
*add* prose and may never alter a citation, line number, or basis value.

## Files Created

1. **backend/app/features/summaries/service.py** (283 lines)
   - `SourceRange`, `EvidenceItem`, `SummaryPayload` Pydantic models
   - `_extract_docstring_lines` — docstring detection with real line ranges
   - `_summarise_file` — docstring, imports, functions, classes, call edges, LOC
   - `_summarise_folder` — child count, total lines, language histogram, union
     of top-level symbols
   - `enrich()` — no-op seam, returns `None`
   - `build_summary()` — dispatches file vs folder vs repository root

2. **backend/app/features/summaries/verifier.py**
   - `VerificationResult` / `VerificationReport`
   - `verify_evidence()` — four independent guards per evidence item:
     a. the `file_id` resolves **in this snapshot** (rejects cross-snapshot IDs)
     b. `line_start >= 1` and `line_end >= line_start`
     c. the range is within the file's real line count
     d. the content hash returned by `read_source_lines` equals the evidence
        `content_sha256`

3. **backend/tests/test_summaries_service.py** (9 tests)
4. **backend/tests/test_summaries_verifier.py** (7 tests)
5. **frontend/src/features/summaries/SummaryPanel.tsx**
   - Basis badge per claim (`observed` / `resolved` / `inferred`)
   - Clickable citation button calling `openSource(fileId, {start, end})`
   - Explicit handling of all four request states: idle, loading, ready, error
   - `limitations` rendered in a disclosure so unverified claims stay visible
6. **frontend/src/features/summaries/register.ts**
   - `registerFeature('summaries.context-panel', ...)` with the load adapter
   - Sends `?path=` from `selectedEntity.path` so the panel follows selection

## Files Modified

1. **backend/app/api/v1/slots.py** — replaced `get_summaries_slot`, previously
   HTTP 501 `NOT_CONNECTED`, with a live `async` handler returning
   `SummaryPayload` at HTTP 200. Added an optional `path` query parameter.
   No other slot route was touched.
2. **frontend/src/features/index.ts** — added exactly one import line:
   `import './summaries/register'`. This is the only permitted shared-file
   edit and no other shared shell file was modified.
3. **backend/tests/test_v1_workspace.py** line 62 — a pre-existing assertion
   expected the placeholder status `501`; the endpoint is now live, so the
   assertion was updated to `200`. Flagged in the Bob session report.

## One Contract Correction Made Mid-Session

The first draft of the backend model flattened the citation range to
`line_start` / `line_end` top-level fields. On re-reading
`contracts/prd.schema.json`, the `Evidence` definition requires `range` as a
**nested** `SourceRange` object. The model, the verifier and both test files
were corrected to the nested shape, and the frontend already expected
`ev.range.line_start`. Caught before the frontend was written.

The `Evidence.id` pattern is `^[A-Za-z0-9_-]+$`; `uuid4().hex` yields
`[a-f0-9]{32}`, which satisfies it.

## Verification Results

All results below were reproduced independently after the Bob session ended.

**Test suite:** 98 passed, 0 failed.

**Verifier output on a real file** (`app/features/summaries/service.py`,
283 lines, summarised against itself):

```
Verified: 10   Unverified: 0
```

Every evidence item — module docstring (lines 1-7), each of the seven
functions with its real definition range, and the two output models — was
marked `verified`.

**Adversarial verification.** Four forged payloads were constructed by hand and
submitted to the verifier. All four were rejected with a reason:

| Forged claim | Verifier response |
| --- | --- |
| `line_end = 9999` on a 283-line file | `line_end 9999 exceeds file length 283` |
| `content_sha256` set to all zeroes | `Content hash mismatch: expected 0000...` |
| `line_start = 0` | `Invalid range: line_start=0, line_end=3` |
| `file_id` taken from a different snapshot | `file_id ... not found in snapshot ...` |

This is the evidence that the verifier is load-bearing rather than decorative.
It was not asked to confirm anything; it was asked to catch these.

**Live API exercise.** A synthetic ZIP was imported through the real
`POST /api/v1/imports/zip` route and every summarising path was called:

| Request | Status | Result |
| --- | --- | --- |
| `?path=pkg/core.py` | 200 | 8 lines, docstring at 1-1, 3 evidence entries |
| `?path=pkg` | 200 | folder: 2 files, 6 total lines |
| no `path` | 200 | repository root: 3 files, 7 total lines |
| `?path=nope.py` | 404 | not fabricated into an empty success |

## What the Summary Text Looks Like

```
service.py is a python file with 283 lines.
Module docstring found at lines 1-7 [9a9761892a2f451f8cbc94dc3e65b668].
Function `_make_evidence` defined at lines 57-68 [0448ab8b...]. Calls: EvidenceItem, SourceRange, uuid4.
Function `_extract_docstring_lines` defined at lines 71-102 [ff9dade1...]. Calls: endswith, enumerate, len, splitlines, startswith, strip.
```

Each line ends with the evidence ID it cites. The panel resolves that ID to a
clickable `path:line` button, and any claim the verifier could not confirm is
surfaced in the `limitations` disclosure instead of being presented as fact.

## Known Limitation, Stated Honestly

There is no AI enrichment in this session. `enrich()` returns `None` by
design. The feature is fully functional without it, and the seam exists for a
follow-up session, but the shipped behaviour is purely deterministic. This is
a deliberate trade documented above, not an oversight.

`read_source_lines` verifies the content hash on every read, so the verifier is
checking a second independent read of the same immutable snapshot rather than
trusting the first.

## Files Not Touched

No shared shell component was modified: `WorkspaceLayout.tsx`, `MapPage.tsx`,
`StructureMap.tsx`, `SourceViewer.tsx`, `WorkspaceContext.tsx`,
`SlotRegistry.ts` and `FeatureContracts.ts` are all unchanged. The slot was
already mounted and the contracts already defined, so no mount work was
necessary.

## Reproducing This Result

```bash
cd backend
python3 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest -q
```

Expected: `98 passed`.

To reproduce the adversarial verification, construct an `EvidenceItem` whose
`range.line_end` exceeds the file length and confirm the report returns
`status='unverified'` with a reason string.
