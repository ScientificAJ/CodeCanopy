# Task 00: Cited Summary Analysis (Prompt Validation) - Session Summary

**Date:** 2026-09-27
**Task IDs:** `681a09383d153d2a380e0156ed80dcf2`, `64a0bdece15e57f088fcf570b292481e`
**Workspace:** CodeCanopy (`ScientificAJ/CodeCanopy`)
**Status:** Complete
**Purpose:** Validate that line-cited, basis-labelled summaries are achievable
before spending budget on the implementation engine.

## Objective

Establish whether a model can produce a summary of a real source file in which
every claim carries a verifiable line-number citation and an explicit
epistemic basis. This session was a design probe, not a feature build.

The output shape was fixed in advance by a prompt that specified:

- one claim per sentence
- a citation in the form `[path:line_start-line_end]`
- a basis of `observed`, `inferred` or `unknown` on every claim
- an explicit instruction not to guess, pad, or describe what a file of that
  type usually does
- a worked example showing what an `unknown` claim looks like
- a closing limitations line

## Files Analysed

`backend/app/services/view_service.py` was analysed across two runs, the second
after the file grew from 175 to 177 lines following a teammate merge. The
second run re-read the file and re-derived every citation at the new offsets.

## Result

The first run produced 39 claims. The second produced 44 at the corrected line
numbers. In both runs:

- **Every `observed` claim was independently checked against the file and
  found to be exactly correct**, including non-obvious details such as the
  `labelDy` offset applying to the *target* node rather than the parent, the
  cache-key construction on a single line, and the ordering of ID collection
  before validation.
- **The model applied `inferred` sparingly and correctly** — to claims that
  were genuinely reasoning steps rather than literal readings, such as the
  consequence of changing the wrapper version string.
- **The limitations line was substantive**, naming the types, helpers and
  module contracts that could not be determined from that file alone.

## Why This Session Was Worth Running

It validated three things before any implementation budget was spent:

1. The citation format is stable enough to parse into the `Evidence` contract.
2. `basis` labelling is meaningful rather than decorative — the model does not
   mark everything `observed`.
3. The final shipped engine does not need a model at all. Because the
   deterministic engine in task 01 produces citations from AST facts, this
   probe's role became a *comparison point*: it shows what a verified
   post-hoc claim stream looks like, against an engine where verification is
   structural.

## Observed Limitation of the Generated Format

Claims may cite **disjoint ranges** in a single citation, for example
`file.py:83-84,97-98` where the first range is a docstring and the second is
code elsewhere in the function. The `Evidence` contract defines `range` as a
single `{line_start, line_end}` pair, so such a claim must be split into two
evidence entries, and a verifier that checks only the first range would
half-prove the claim while still reporting success.

The deterministic engine in task 01 does not have this failure mode, because
AST-derived ranges are contiguous by construction. It is recorded here because
it is the exact weakness that generated summaries would carry into the product
if the deterministic approach were ever replaced by a model-only one.

## Files

- `bob_task_2026-09-27_681a0938.md` — first run, 175-line file, 39 claims
- `bob_task_2026-09-27_64a0bdec.md` — second run, 177-line file, 44 claims
