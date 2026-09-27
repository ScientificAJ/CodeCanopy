# Task 05: Ask Slot Wiring and Empty-Success Fix - Session Summary

**Date:** 2026-09-27
**Task IDs:** `cb9773082cfc2ac838d5dc42ce0517be` (wiring), `84f1cdb8943d28e56aa8050a22464bb0` (greeting)

## Background

The conversational backend was already complete. `POST /chat` was implemented,
read `GROQ_API_KEY` from the server environment, and returned real answers.
Two things prevented it from reaching the UI.

## Task 05a: wiring

**1. The slot route was a stub.** The GET endpoint returned HTTP 501 with a
static not-connected placeholder. Replaced with a real handler.

**2. The frontend registered through the legacy call.** The ask feature used the
bare slot-registry call with a component only, while every working feature uses
the feature-contracts call that takes a component plus a loader. Because the
loader never ran, the panel never received data. Migrated to the same call the
other features use.

Result: 126 passing. GET /ask returns 200. No key reaches the frontend bundle.

## Task 05b: the empty-success fix

The wired endpoint returned HTTP 200 with an empty answer string and a
connectivity hint. A 200 with nothing in it reads as broken, and it
contradicts the project's own principle that a slot unable to answer must say
why. It had already cost debugging time because a reviewer could not
distinguish "feature broken" from "backend down".

Replaced with real greeting copy describing what the feature does, and a
context hint embedding the resolved snapshot id. Rendered in the panel through
a narrowed runtime read, shown only when there is no prior conversation.

Result: 128 passing. Response is 297 characters with a real snapshot id.

## Audit for the same pattern elsewhere

The two live slots delegate to `build_summary` and `build_dependencies`, which
either return a fully populated payload or raise. The proposals slot returns
an explicit HTTP 501, which is an honest failure status. No other slot can
return 200 with an empty body.

## Known tech debt

The feature contract declares `ask.workspace` as `Answer`, carrying
`schema_version`, `claims`, and `evidence`. The endpoint returns
`{answer, context_hint}`. The frontend narrows the type at runtime rather than
claiming the wrong shape. This is documented in the source and is not a runtime
defect, but it is unresolved. Changing the contract would require editing a
shared file, so it was left alone deliberately.
