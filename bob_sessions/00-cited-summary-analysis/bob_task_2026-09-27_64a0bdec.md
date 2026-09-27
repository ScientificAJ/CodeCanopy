# # Analyze the file backend/app/services/view_service.py in this repository.

Read the file first. Do not summarize from its filename.

Write a summary where EVERY sentence is a separate claim, and every claim
carries a citation in this exact format: [path:line_start-line_end]

After each claim, state its basis:
- observed = the cited lines literally contain this
- inferred = reasonable reading, not directly proven by the lines
- unknown = you could not cite a line proving it

If you cannot cite a line for a claim, mark it unknown and move on. Do not
guess, do not pad, do not describe what a file of this type usually does.

Example of the required shape:

"This module resolves the active snapshot's entity graph before compiling
the Archify spec [backend/app/services/view_service.py:42-58]. observed"

"The renderer applies a two-render capacity limit to bound memory
[backend/app/services/view_service.py:112-119]. observed"

"The cache key includes wrapper version so stale renders are invalidated
across deploys. inferred"

"Handles retry logic for failed GitHub fetches. unknown"

Format: markdown. No preamble. No closing summary. Do not modify any code.

End with a limitations line listing what you could not determine from this
file alone.

---

**Status:** active  **Date:** 2026-09-26

---

### 👤 User

Analyze the file backend/app/services/view_service.py in this repository.

Read the file first. Do not summarize from its filename.

Write a summary where EVERY sentence is a separate claim, and every claim
carries a citation in this exact format: [path:line_start-line_end]

After each claim, state its basis:
- observed = the cited lines literally contain this
- inferred = reasonable reading, not directly proven by the lines
- unknown = you could not cite a line proving it

If you cannot cite a line for a claim, mark it unknown and move on. Do not
guess, do not pad, do not describe what a file of this type usually does.

Example of the required shape:

"This module resolves the active snapshot's entity graph before compiling
the Archify spec [backend/app/services/view_service.py:42-58]. observed"

"The renderer applies a two-render capacity limit to bound memory
[backend/app/services/view_service.py:112-119]. observed"

"The cache key includes wrapper version so stale renders are invalidated
across deploys. inferred"

"Handles retry logic for failed GitHub fetches. unknown"

Format: markdown. No preamble. No closing summary. Do not modify any code.

End with a limitations line listing what you could not determine from this
file alone.

---

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — backend/app/services/view_service.py

### 🤖 Assistant

---

"The module's docstring declares it is a 'Pinned Archify adapter' that 'fails closed on validation' and 'never serves a stale render'" [`backend/app/services/view_service.py:1`](backend/app/services/view_service.py:1). **observed**

"The Archify renderer is pinned to a specific commit, `9e35d2b0b39b155553ba9fcfe0b4f2a5198dd993`" [`backend/app/services/view_service.py:20`](backend/app/services/view_service.py:20). **observed**

"Concurrent renders are bounded by a `threading.BoundedSemaphore` with a capacity of two" [`backend/app/services/view_service.py:21`](backend/app/services/view_service.py:21). **observed**

"`get_preferences` reads `view.json` from the snapshot directory and validates it as a `ViewPreferences` model; if the file does not exist it returns a default `ViewPreferences()` instance" [`backend/app/services/view_service.py:24-26`](backend/app/services/view_service.py:24-26). **observed**

"`save_preferences` validates that group IDs within the submitted preferences are unique, raising a `WorkspaceError` with HTTP 422 if they are not" [`backend/app/services/view_service.py:33-34`](backend/app/services/view_service.py:33-34). **observed**

"`save_preferences` validates that group members are unique and are all entity IDs that exist in the given snapshot" [`backend/app/services/view_service.py:35-37`](backend/app/services/view_service.py:35-37). **observed**

"`save_preferences` validates that every label references either an entity or a group ID belonging to the snapshot, and that each label value is non-empty and at most 60 characters" [`backend/app/services/view_service.py:38-39`](backend/app/services/view_service.py:38-39). **observed**

"`save_preferences` validates that the `focus` field refers to either a known file-system path or a group ID, raising a 422 otherwise" [`backend/app/services/view_service.py:40-42`](backend/app/services/view_service.py:40-42). **observed**

"Validated preferences are persisted by writing a JSON dump to `<v1_root>/<snapshot_id>/view.json`" [`backend/app/services/view_service.py:43`](backend/app/services/view_service.py:43). **observed**

"The `projection` function calls `build_structural_graph` with a hard `max_entities=4` limit" [`backend/app/services/view_service.py:50`](backend/app/services/view_service.py:50). **observed**

"When the focus is a virtual group, `projection` synthesises a root `GraphEntity` of kind `VIRTUAL_GROUP` instead of using the graph's first entity" [`backend/app/services/view_service.py:51-52`](backend/app/services/view_service.py:51-52). **observed**

"Children are sorted by folders-first order (when that preference is active), then case-folded label, then ID" [`backend/app/services/view_service.py:57`](backend/app/services/view_service.py:57). **observed**

"The projection is paginated: a cursor into the child list is accepted, and exactly three children are returned per page" [`backend/app/services/view_service.py:58-60`](backend/app/services/view_service.py:58-60). **observed**

"A cursor value that exceeds the total number of children raises a `WorkspaceError` with code `INVALID_CURSOR` and HTTP 422" [`backend/app/services/view_service.py:58-59`](backend/app/services/view_service.py:58-59). **observed**

"Relations in the projected graph use `RelationKind.GROUPS` for virtual-group roots and `RelationKind.CONTAINS` for directory roots" [`backend/app/services/view_service.py:62-64`](backend/app/services/view_service.py:62-64). **observed**

"`projection` applies per-entity label overrides from `preferences.labels` and records the original label and a `view_only_label` flag in the entity's metadata" [`backend/app/services/view_service.py:71-75`](backend/app/services/view_service.py:71-75). **observed**

"`compile_spec` truncates any node label longer than 24 characters to 21 characters followed by an ellipsis" [`backend/app/services/view_service.py:91`](backend/app/services/view_service.py:91). **observed**

"`compile_spec` places a single child node at x=200 and multiple children at evenly-spaced x-positions depending on whether there are two children (360-unit spacing) or more (180-unit spacing)" [`backend/app/services/view_service.py:89`](backend/app/services/view_service.py:89). **observed**

"Edge IDs in the compiled spec are the first 32 hex characters of a SHA-256 hash of the original relation ID, prefixed with `r_`" [`backend/app/services/view_service.py:96`](backend/app/services/view_service.py:96). **observed**

"A `labelDy` offset of 45 is added to a connection when the target node's x-position is 200, described in the docstring as a diagnosed repair from the pinned showcase validator to prevent label overlap" [`backend/app/services/view_service.py:97-98, 84-85`](backend/app/services/view_service.py:84-98). **observed**

"The compiled spec always sets `diagram_type` to `'architecture'`, `quality_profile` to `'showcase'`, `animation` to `'none'`, and hides the legend" [`backend/app/services/view_service.py:100-102`](backend/app/services/view_service.py:100-102). **observed**

"The `_json_safe` helper HTML-escapes `<`, `>`, and `&` after JSON serialisation to prevent injection in HTML contexts" [`backend/app/services/view_service.py:106`](backend/app/services/view_service.py:106). **observed**

"The cache key is a SHA-256 hash that incorporates a literal wrapper version string `'codecanopy-wrapper-1.1.4'`, the spec bytes, the manifest JSON, the bridge script, and the license notice" [`backend/app/services/view_service.py:119`](backend/app/services/view_service.py:119). **observed**

"The cache key includes the wrapper version, so a change to the wrapper version string will invalidate all previously cached renders" [`backend/app/services/view_service.py:119`](backend/app/services/view_service.py:119). **inferred**

"If a cached render directory already contains `result.json`, `render_view` returns it immediately without invoking the renderer" [`backend/app/services/view_service.py:122-123`](backend/app/services/view_service.py:122-123). **observed**

"If the semaphore cannot be acquired (i.e., two renders are already in progress), a `WorkspaceError` with code `RENDER_BUSY` and HTTP 429 is raised immediately without blocking" [`backend/app/services/view_service.py:124-125`](backend/app/services/view_service.py:124-125). **observed**

"The renderer is invoked as a subprocess running `vendor/archify/bin/archify.mjs` via Node, using a configurable path from the `CODECANOPY_NODE` environment variable (defaulting to `node`)" [`backend/app/services/view_service.py:134-136`](backend/app/services/view_service.py:134-136). **observed**

"The subprocess is given a 40-second timeout; an `OSError` or `TimeoutExpired` raises a 503 `RENDER_UNAVAILABLE` error" [`backend/app/services/view_service.py:136-138`](backend/app/services/view_service.py:136-138). **observed**

"A non-zero return code from the subprocess or a missing output file raises a 422 `RENDER_VALIDATION_FAILED` error, implementing the 'fail closed' guarantee stated in the module docstring" [`backend/app/services/view_service.py:139-140`](backend/app/services/view_service.py:139-140). **observed**

"Path fields (`input`, `output`) and `path` keys inside `specification` and `artifact` sub-dicts are stripped from the delivery receipt before it is returned, preventing server-path disclosure" [`backend/app/services/view_service.py:149-152`](backend/app/services/view_service.py:149-152). **observed**

"A strict Content Security Policy is injected into the rendered HTML: `default-src 'none'` with only `unsafe-inline` scripts and styles, `data:`/`blob:` images, `data:` fonts, and no network connectivity" [`backend/app/services/view_service.py:153`](backend/app/services/view_service.py:153). **observed**

"An embed-detection script is injected that sets `data-embed='true'` on `<html>` when the page is loaded inside an iframe" [`backend/app/services/view_service.py:154`](backend/app/services/view_service.py:154). **observed**

"The Archify license text is embedded as an HTML comment in `<head>` of every rendered page" [`backend/app/services/view_service.py:154`](backend/app/services/view_service.py:154). **observed**

"A `codecanopy-manifest` JSON script block containing the full manifest (including snapshot, graph, renderer ID mapping, preferences, and a list of deferred capabilities) is injected before `</body>`" [`backend/app/services/view_service.py:117-118, 155`](backend/app/services/view_service.py:117-155). **observed**

"The deferred capabilities list explicitly names: AI summaries, dependencies and impact, reuse, duplicates, unused code, Ask CodeCanopy, proposals and generated documents" [`backend/app/services/view_service.py:118`](backend/app/services/view_service.py:118). **observed**

"Per-snapshot render cache is capped at seven directories; under a `_cache_lock`, older directories (by mtime) beyond the seven most recent are deleted with `shutil.rmtree`" [`backend/app/services/view_service.py:163-165`](backend/app/services/view_service.py:163-165). **observed**

"The temporary directory is only renamed to the final cache path if the cache slot does not already exist, guarding against a race where two requests produce the same view simultaneously" [`backend/app/services/view_service.py:166-167`](backend/app/services/view_service.py:166-167). **observed**

"The `finally` block always releases the semaphore and removes the temporary directory if it still exists, preventing both semaphore leaks and temp-dir accumulation" [`backend/app/services/view_service.py:169-172`](backend/app/services/view_service.py:169-172). **observed**

"The `_cache_lock` is a module-level `threading.Lock`, meaning cache eviction is serialised across all threads in the same process" [`backend/app/services/view_service.py:175`](backend/app/services/view_service.py:175). **observed**

---

**Limitations:** This file alone does not reveal: the full schema of `ViewPreferences`, `MapRequest`, `GraphEntity`, `GraphRelation`, or their field defaults; the behaviour of `build_structural_graph`, `inventory_entities`, `_v1_root`, `_read_json`, `_write_json`, or `get_snapshot`; the content or API contract of `backend/app/rendering/bridge.js`; how `entity_id` computes its hash; whether the cache-eviction limit of seven is configurable; or how `render_view` callers handle the returned dict.

### 🤖 Assistant

Previous conversation summary:

## Goal
The user wanted a rigorous, cited analysis of a single source file — not a general summary, but a structured claim-by-claim breakdown with line citations and explicit epistemological labels (observed / inferred / unknown).

## Instructions
- Read the file first; do not summarize from its filename.
- Every sentence is a separate claim with a citation in the format `[path:line_start-line_end]`.
- After each claim, state its basis

---

**Status:** active  **Date:** 2026-09-27

---

### 👤 User

# Analyze the file backend/app/services/view_service.py in this repository.

Read the file first. Do not summarize from its filename.

Write a summary where EVERY sentence is a separate claim, and every claim
carries a citation in this exact format: [path:line_start-line_end]

After each claim, state its basis:
- observed = the cited lines literally contain this
- inferred = reasonable reading, not directly proven by the lines
- unknown = you could not cite a line proving it

If you cannot cite a line for a claim, mark it unknown and move on. Do not
guess, do not pad, do not describe what a file of this type usually does.

Example of the required shape:

"This module resolves the active snapshot's entity graph before compiling
the Archify spec [backend/app/services/view_service.py:42-58]. observed"

"The renderer applies a two-render capacity limit to bound memory
[backend/app/services/view_service.py:112-119]. observed"

"The cache key includes wrapper version so stale renders are invalidated
across deploys. inferred"

"Handles retry logic for failed GitHub fetches. unknown"

Format: markdown. No preamble. No closing summary. Do not modify any code.

End with a limitations line listing what you could not determine from this
file alone.

---

**Status:** active  **Date:** 2026-09-26

---

### 👤 User

Analyze the file backend/app/services/view_service.py in this repository.

Read the file first. Do not summarize from its filename.

Write a summary where EVERY sentence is a separate claim, and every claim
carries a citation in this exact format: [path:line_start-line_end]

After each claim, state its basis:
- observed = the cited lines literally contain this
- inferred = reasonable reading, not directly proven by the lines
- unknown = you could not cite a line proving it

If you cannot cite a line for a claim, mark it unknown and move on. Do not
guess, do not pad, do not describe what a file of this type usually does.

Example of the required shape:

"This module resolves the active snapshot's entity graph before compiling
the Archify spec [backend/app/services/view_service.py:42-58]. observed"

"The renderer applies a two-render capacity limit to bound memory
[backend/app/services/view_service.py:112-119]. observed"

"The cache key includes wrapper version so stale renders are invalidated
across deploys. inferred"

"Handles retry logic for failed GitHub fetches. unknown"

Format: markdown. No preamble. No closing summary. Do not modify any code.

End with a limitations line listing what you could not determine from this
file alone.

---

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — backend/app/services/view_service.py

### 🤖 Assistant

---

"The module's docstring declares it is a 'Pinned Archify adapter' that 'fails closed on validation' and 'never serves a stale render'" [`backend/app/services/view_service.py:1`](backend/app/services/view_service.py:1). **observed**

"The Archify renderer is pinned to a specific commit, `9e35d2b0b39b155553ba9fcfe0b4f2a5198dd993`" [`backend/app/services/view_service.py:20`](backend/app/services/view_service.py:20). **observed**

"Concurrent renders are bounded by a `threading.BoundedSemaphore` with a capacity of two" [`backend/app/services/view_service.py:21`](backend/app/services/view_service.py:21). **observed**

"`get_preferences` reads `view.json` from the snapshot directory and validates it as a `ViewPreferences` model; if the file does not exist it returns a default `ViewPreferences()` instance" [`backend/app/services/view_service.py:24-26`](backend/app/services/view_service.py:24-26). **observed**

"`save_preferences` validates that group IDs within the submitted preferences are unique, raising a `WorkspaceError` with HTTP 422 if they are not" [`backend/app/services/view_service.py:33-34`](backend/app/services/view_service.py:33-34). **observed**

"`save_preferences` validates that group members are unique and are all entity IDs that exist in the given snapshot" [`backend/app/services/view_service.py:35-37`](backend/app/services/view_service.py:35-37). **observed**

"`save_preferences` validates that every label references either an entity or a group ID belonging to the snapshot, and that each label value is non-empty and at most 60 characters" [`backend/app/services/view_service.py:38-39`](backend/app/services/view_service.py:38-39). **observed**

"`save_preferences` validates that the `focus` field refers to either a known file-system path or a group ID, raising a 422 otherwise" [`backend/app/services/view_service.py:40-42`](backend/app/services/view_service.py:40-42). **observed**

"Validated preferences are persisted by writing a JSON dump to `<v1_root>/<snapshot_id>/view.json`" [`backend/app/services/view_service.py:43`](backend/app/services/view_service.py:43). **observed**

"The `projection` function calls `build_structural_graph` with a hard `max_entities=4` limit" [`backend/app/services/view_service.py:50`](backend/app/services/view_service.py:50). **observed**

"When the focus is a virtual group, `projection` synthesises a root `GraphEntity` of kind `VIRTUAL_GROUP` instead of using the graph's first entity" [`backend/app/services/view_service.py:51-52`](backend/app/services/view_service.py:51-52). **observed**

"Children are sorted by folders-first order (when that preference is active), then case-folded label, then ID" [`backend/app/services/view_service.py:57`](backend/app/services/view_service.py:57). **observed**

"The projection is paginated: a cursor into the child list is accepted, and exactly three children are returned per page" [`backend/app/services/view_service.py:58-60`](backend/app/services/view_service.py:58-60). **observed**

"A cursor value that exceeds the total number of children raises a `WorkspaceError` with code `INVALID_CURSOR` and HTTP 422" [`backend/app/services/view_service.py:58-59`](backend/app/services/view_service.py:58-59). **observed**

"Relations in the projected graph use `RelationKind.GROUPS` for virtual-group roots and `RelationKind.CONTAINS` for directory roots" [`backend/app/services/view_service.py:62-64`](backend/app/services/view_service.py:62-64). **observed**

"`projection` applies per-entity label overrides from `preferences.labels` and records the original label and a `view_only_label` flag in the entity's metadata" [`backend/app/services/view_service.py:71-75`](backend/app/services/view_service.py:71-75). **observed**

"`compile_spec` truncates any node label longer than 24 characters to 21 characters followed by an ellipsis" [`backend/app/services/view_service.py:91`](backend/app/services/view_service.py:91). **observed**

"`compile_spec` places a single child node at x=200 and multiple children at evenly-spaced x-positions depending on whether there are two children (360-unit spacing) or more (180-unit spacing)" [`backend/app/services/view_service.py:89`](backend/app/services/view_service.py:89). **observed**

"Edge IDs in the compiled spec are the first 32 hex characters of a SHA-256 hash of the original relation ID, prefixed with `r_`" [`backend/app/services/view_service.py:96`](backend/app/services/view_service.py:96). **observed**

"A `labelDy` offset of 45 is added to a connection when the target node's x-position is 200, described in the docstring as a diagnosed repair from the pinned showcase validator to prevent label overlap" [`backend/app/services/view_service.py:97-98, 84-85`](backend/app/services/view_service.py:84-98). **observed**

"The compiled spec always sets `diagram_type` to `'architecture'`, `quality_profile` to `'showcase'`, `animation` to `'none'`, and hides the legend" [`backend/app/services/view_service.py:100-102`](backend/app/services/view_service.py:100-102). **observed**

"The `_json_safe` helper HTML-escapes `<`, `>`, and `&` after JSON serialisation to prevent injection in HTML contexts" [`backend/app/services/view_service.py:106`](backend/app/services/view_service.py:106). **observed**

"The cache key is a SHA-256 hash that incorporates a literal wrapper version string `'codecanopy-wrapper-1.1.4'`, the spec bytes, the manifest JSON, the bridge script, and the license notice" [`backend/app/services/view_service.py:119`](backend/app/services/view_service.py:119). **observed**

"The cache key includes the wrapper version, so a change to the wrapper version string will invalidate all previously cached renders" [`backend/app/services/view_service.py:119`](backend/app/services/view_service.py:119). **inferred**

"If a cached render directory already contains `result.json`, `render_view` returns it immediately without invoking the renderer" [`backend/app/services/view_service.py:122-123`](backend/app/services/view_service.py:122-123). **observed**

"If the semaphore cannot be acquired (i.e., two renders are already in progress), a `WorkspaceError` with code `RENDER_BUSY` and HTTP 429 is raised immediately without blocking" [`backend/app/services/view_service.py:124-125`](backend/app/services/view_service.py:124-125). **observed**

"The renderer is invoked as a subprocess running `vendor/archify/bin/archify.mjs` via Node, using a configurable path from the `CODECANOPY_NODE` environment variable (defaulting to `node`)" [`backend/app/services/view_service.py:134-136`](backend/app/services/view_service.py:134-136). **observed**

"The subprocess is given a 40-second timeout; an `OSError` or `TimeoutExpired` raises a 503 `RENDER_UNAVAILABLE` error" [`backend/app/services/view_service.py:136-138`](backend/app/services/view_service.py:136-138). **observed**

"A non-zero return code from the subprocess or a missing output file raises a 422 `RENDER_VALIDATION_FAILED` error, implementing the 'fail closed' guarantee stated in the module docstring" [`backend/app/services/view_service.py:139-140`](backend/app/services/view_service.py:139-140). **observed**

"Path fields (`input`, `output`) and `path` keys inside `specification` and `artifact` sub-dicts are stripped from the delivery receipt before it is returned, preventing server-path disclosure" [`backend/app/services/view_service.py:149-152`](backend/app/services/view_service.py:149-152). **observed**

"A strict Content Security Policy is injected into the rendered HTML: `default-src 'none'` with only `unsafe-inline` scripts and styles, `data:`/`blob:` images, `data:` fonts, and no network connectivity" [`backend/app/services/view_service.py:153`](backend/app/services/view_service.py:153). **observed**

"An embed-detection script is injected that sets `data-embed='true'` on `<html>` when the page is loaded inside an iframe" [`backend/app/services/view_service.py:154`](backend/app/services/view_service.py:154). **observed**

"The Archify license text is embedded as an HTML comment in `<head>` of every rendered page" [`backend/app/services/view_service.py:154`](backend/app/services/view_service.py:154). **observed**

"A `codecanopy-manifest` JSON script block containing the full manifest (including snapshot, graph, renderer ID mapping, preferences, and a list of deferred capabilities) is injected before `</body>`" [`backend/app/services/view_service.py:117-118, 155`](backend/app/services/view_service.py:117-155). **observed**

"The deferred capabilities list explicitly names: AI summaries, dependencies and impact, reuse, duplicates, unused code, Ask CodeCanopy, proposals and generated documents" [`backend/app/services/view_service.py:118`](backend/app/services/view_service.py:118). **observed**

"Per-snapshot render cache is capped at seven directories; under a `_cache_lock`, older directories (by mtime) beyond the seven most recent are deleted with `shutil.rmtree`" [`backend/app/services/view_service.py:163-165`](backend/app/services/view_service.py:163-165). **observed**

"The temporary directory is only renamed to the final cache path if the cache slot does not already exist, guarding against a race where two requests produce the same view simultaneously" [`backend/app/services/view_service.py:166-167`](backend/app/services/view_service.py:166-167). **observed**

"The `finally` block always releases the semaphore and removes the temporary directory if it still exists, preventing both semaphore leaks and temp-dir accumulation" [`backend/app/services/view_service.py:169-172`](backend/app/services/view_service.py:169-172). **observed**

"The `_cache_lock` is a module-level `threading.Lock`, meaning cache eviction is serialised across all threads in the same process" [`backend/app/services/view_service.py:175`](backend/app/services/view_service.py:175). **observed**

---

**Limitations:** This file alone does not reveal: the full schema of `ViewPreferences`, `MapRequest`, `GraphEntity`, `GraphRelation`, or their field defaults; the behaviour of `build_structural_graph`, `inventory_entities`, `_v1_root`, `_read_json`, `_write_json`, or `get_snapshot`; the content or API contract of `backend/app/rendering/bridge.js`; how `entity_id` computes its hash; whether the cache-eviction limit of seven is configurable; or how `render_view` callers handle the returned dict.

### 🤖 Assistant

Previous conversation summary:

## Goal
The user wanted a rigorous, cited analysis of a single source file — not a general summary, but a structured claim-by-claim breakdown with line citations and explicit epistemological labels (observed / inferred / unknown).

## Instructions
- Read the file first; do not summarize from its filename.
- Every sentence is a separate claim with a citation in the format `[path:line_start-line_end]`.
- After each claim, state its basis

---

### 🤖 Assistant

> 🔧 called: use_skill



> 🔧 **use_skill** — cited-summary

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — backend/app/services/view_service.py

### 🤖 Assistant

---

The module's docstring declares it is a "Pinned Archify adapter" that "fails closed on validation" and "never serves a stale render" [`backend/app/services/view_service.py:1`](backend/app/services/view_service.py:1). **observed**

The Archify renderer is pinned to a specific commit hash `9e35d2b0b39b155553ba9fcfe0b4f2a5198dd993`, stored as the module-level constant `ARCHIFY_COMMIT` [`backend/app/services/view_service.py:20`](backend/app/services/view_service.py:20). **observed**

Concurrent renders are bounded by a `threading.BoundedSemaphore` with a capacity of two, stored as the module-level variable `_render_capacity` [`backend/app/services/view_service.py:21`](backend/app/services/view_service.py:21). **observed**

`get_preferences` reads `view.json` from the snapshot directory and validates it as a `ViewPreferences` model; if the file does not exist it returns a default `ViewPreferences()` instance [`backend/app/services/view_service.py:24-26`](backend/app/services/view_service.py:24-26). **observed**

`save_preferences` collects all entity IDs from the snapshot via `inventory_entities` and all group IDs from the submitted preferences before performing any validation [`backend/app/services/view_service.py:30-32`](backend/app/services/view_service.py:30-32). **observed**

`save_preferences` raises a `WorkspaceError` with code `INVALID_VIEW` and HTTP 422 if the list of group IDs contains duplicates [`backend/app/services/view_service.py:33-34`](backend/app/services/view_service.py:33-34). **observed**

`save_preferences` raises a `WorkspaceError` with code `INVALID_VIEW` and HTTP 422 if any group's members are not a subset of the snapshot's entity IDs or if the members list itself contains duplicates [`backend/app/services/view_service.py:35-37`](backend/app/services/view_service.py:35-37). **observed**

`save_preferences` raises a `WorkspaceError` with code `INVALID_VIEW` and HTTP 422 if any label key is not a known entity or group ID, or if any label value is blank or longer than 60 characters [`backend/app/services/view_service.py:38-39`](backend/app/services/view_service.py:38-39). **observed**

`save_preferences` raises a `WorkspaceError` with code `INVALID_VIEW` and HTTP 422 if the `focus` field does not match a known entity path or group ID [`backend/app/services/view_service.py:40-42`](backend/app/services/view_service.py:40-42). **observed**

After all validation passes, `save_preferences` persists the preferences by writing them as JSON to `<v1_root>/<snapshot_id>/view.json` [`backend/app/services/view_service.py:43`](backend/app/services/view_service.py:43). **observed**

`projection` calls `build_structural_graph` with a hard `max_entities=4` limit and passes `focus=None` when the request targets a virtual group [`backend/app/services/view_service.py:50`](backend/app/services/view_service.py:50). **observed**

When the request focus matches a virtual group, `projection` constructs a synthetic root `GraphEntity` of kind `VIRTUAL_GROUP` with a `view_only: True` metadata flag, and its children are the snapshot entities whose IDs are in `group.members` [`backend/app/services/view_service.py:51-53`](backend/app/services/view_service.py:51-53). **observed**

When the focus is not a virtual group, the root is `graph.entities[0]` and children are those entities whose `parent_id` equals the root's ID [`backend/app/services/view_service.py:55-56`](backend/app/services/view_service.py:55-56). **observed**

Children are sorted by a three-key tuple: folders-first (files sort after non-files when `preferences.order == 'folders-first'`), then case-folded label, then entity ID [`backend/app/services/view_service.py:57`](backend/app/services/view_service.py:57). **observed**

A cursor value strictly greater than the total number of children raises a `WorkspaceError` with code `INVALID_CURSOR` and HTTP 422 [`backend/app/services/view_service.py:58-59`](backend/app/services/view_service.py:58-59). **observed**

Exactly three children are returned per page, sliced as `children[cursor : cursor + 3]` [`backend/app/services/view_service.py:60`](backend/app/services/view_service.py:60). **observed**

`graph.next_cursor` is set to `cursor + 3` if more children remain, otherwise to `None`, providing a simple forward-pagination token [`backend/app/services/view_service.py:68`](backend/app/services/view_service.py:68). **observed**

`graph.coverage.truncated` is set to `True` whenever the visible slice is smaller than the full children list [`backend/app/services/view_service.py:70`](backend/app/services/view_service.py:70). **observed**

For entities whose IDs appear in `preferences.labels`, `projection` stores the original label under `entity.metadata['original_label']`, sets `entity.metadata['view_only_label'] = True`, and replaces `entity.label` with the override value [`backend/app/services/view_service.py:71-75`](backend/app/services/view_service.py:71-75). **observed**

`compile_spec` places the root node at x=200 regardless of child count, and places a single child also at x=200; when there are two children they are spaced 360 units apart starting from x=20, and with more children the spacing reduces to 180 units [`backend/app/services/view_service.py:89`](backend/app/services/view_service.py:89). **observed**

Node labels longer than 24 characters are truncated to 21 characters and suffixed with an ellipsis character [`backend/app/services/view_service.py:91`](backend/app/services/view_service.py:91). **observed**

The `sublabel` for a `VIRTUAL_GROUP` entity is the literal string `'View-only group'`; for all other entities it is the capitalised value of `entity.kind.value` [`backend/app/services/view_service.py:92`](backend/app/services/view_service.py:92). **observed**

Edge IDs in the compiled spec are the prefix `r_` followed by the first 32 hex characters of a SHA-256 hash of the original relation ID [`backend/app/services/view_service.py:96`](backend/app/services/view_service.py:96). **observed**

Edge labels are `'member'` for `RelationKind.GROUPS` relations and `'contains'` for all others [`backend/app/services/view_service.py:96`](backend/app/services/view_service.py:96). **observed**

A `labelDy` offset of 45 is added to a connection when its target node's x-position equals 200; the function's docstring describes this as a "diagnosed repair from the pinned showcase validator" to prevent label overlap [`backend/app/services/view_service.py:83-84,97-98`](backend/app/services/view_service.py:83-98). **observed**

The compiled spec always sets `diagram_type` to `'architecture'`, `quality_profile` to `'showcase'`, `animation` to `'none'`, and hides the legend with `{'mode': 'hidden'}` [`backend/app/services/view_service.py:100-102`](backend/app/services/view_service.py:100-102). **observed**

`_json_safe` serialises a value to compact JSON with `sort_keys=True` and then HTML-escapes `<`, `>`, and `&` as their Unicode escape sequences to prevent injection in HTML contexts [`backend/app/services/view_service.py:105-106`](backend/app/services/view_service.py:105-106). **observed**

The cache key is the SHA-256 hex digest of the concatenation of the literal bytes `b'codecanopy-wrapper-1.1.4'`, the spec bytes, the JSON-safe manifest, the bridge script, and the license notice [`backend/app/services/view_service.py:119`](backend/app/services/view_service.py:119). **observed**

Because the cache key incorporates the literal wrapper version string, changing that string in the source will invalidate all previously cached renders even if the spec and manifest are identical [`backend/app/services/view_service.py:119`](backend/app/services/view_service.py:119). **inferred**

If the cache directory already contains `result.json`, `render_view` returns the cached result immediately without invoking the renderer subprocess [`backend/app/services/view_service.py:122-123`](backend/app/services/view_service.py:122-123). **observed**

If the semaphore cannot be acquired (i.e., two renders are already in progress), a `WorkspaceError` with code `RENDER_BUSY` and HTTP 429 is raised immediately without blocking [`backend/app/services/view_service.py:124-125`](backend/app/services/view_service.py:124-125). **observed**

The renderer is invoked as a subprocess running `vendor/archify/bin/archify.mjs` via a Node binary whose path is read from the `CODECANOPY_NODE` environment variable, defaulting to `node` [`backend/app/services/view_service.py:134-136`](backend/app/services/view_service.py:134-136). **observed**

The subprocess is given a 40-second timeout; if `OSError` or `subprocess.TimeoutExpired` is raised the function raises a `WorkspaceError` with code `RENDER_UNAVAILABLE` and HTTP 503 [`backend/app/services/view_service.py:136-138`](backend/app/services/view_service.py:136-138). **observed**

A non-zero return code or a missing output file raises a `WorkspaceError` with code `RENDER_VALIDATION_FAILED` and HTTP 422, implementing the "fail closed" guarantee stated in the module docstring [`backend/app/services/view_service.py:139-140`](backend/app/services/view_service.py:139-140). **observed**

The manifest injected into the rendered page embeds SHA-256 hashes of both the original Archify output and the input spec, copied from the renderer's `validation` sub-object [`backend/app/services/view_service.py:144-149`](backend/app/services/view_service.py:144-149). **observed**

`input`, `output`, and any `path` key inside the `specification` or `artifact` sub-dicts are stripped from the delivery receipt before it is returned, preventing exposure of temporary server paths [`backend/app/services/view_service.py:150-154`](backend/app/services/view_service.py:150-154). **observed**

A strict Content Security Policy is injected into `<head>`: `default-src 'none'` with only `unsafe-inline` scripts and styles, `data:` and `blob:` images, `data:` fonts, and no network connectivity (`connect-src 'none'`) [`backend/app/services/view_service.py:155-156`](backend/app/services/view_service.py:155-156). **observed**

An inline script is injected into `<head>` that sets `data-embed="true"` on `<html>` when the page is loaded inside an iframe [`backend/app/services/view_service.py:156`](backend/app/services/view_service.py:156). **observed**

The Archify license text is embedded as an HTML comment immediately after `<head>`, before the CSP meta tag [`backend/app/services/view_service.py:156`](backend/app/services/view_service.py:156). **observed**

A `<script id="codecanopy-manifest" type="application/json">` block containing the full manifest and a `<script>` block containing the bridge script content are injected just before `</body>` [`backend/app/services/view_service.py:157`](backend/app/services/view_service.py:157). **observed**

CSS injected before `</body>` hides `.codecanopy-provenance` elements and makes the SVG diagram fill the viewport height when the page is embedded via iframe [`backend/app/services/view_service.py:158`](backend/app/services/view_service.py:158). **observed**

The CSS also applies `animation:none` and `transition:none` globally when `prefers-reduced-motion: reduce` is active [`backend/app/services/view_service.py:158`](backend/app/services/view_service.py:158). **observed**

The manifest's `deferred_capabilities` list explicitly names: `'AI summaries'`, `'dependencies and impact'`, `'reuse'`, `'duplicates'`, `'unused code'`, `'Ask CodeCanopy'`, and `'proposals and generated documents'` [`backend/app/services/view_service.py:118`](backend/app/services/view_service.py:118). **observed**

The returned result dict includes `html_sha256`, the SHA-256 hex digest of the final assembled HTML string [`backend/app/services/view_service.py:161`](backend/app/services/view_service.py:161). **observed**

An intermediate `codecanopy.html` file is written to the temporary directory, but the result dict delivered to callers contains only the in-memory HTML string, not a file path [`backend/app/services/view_service.py:163`](backend/app/services/view_service.py:163). **observed**

Per-snapshot render cache is capped at seven directories; under `_cache_lock`, directories beyond the seven most recent (sorted by mtime) are deleted with `shutil.rmtree` [`backend/app/services/view_service.py:164-167`](backend/app/services/view_service.py:164-167). **observed**

Directories whose names start with `'.'` are excluded from the eviction candidate list, preventing active temporary directories from being counted against the quota [`backend/app/services/view_service.py:166`](backend/app/services/view_service.py:166). **observed**

The temporary directory is renamed to the final cache path only if the cache slot does not already exist, guarding against a race where two concurrent requests produce the same view simultaneously [`backend/app/services/view_service.py:168-169`](backend/app/services/view_service.py:168-169). **observed**

The `finally` block always releases the semaphore and removes the temporary directory if it still exists, preventing both semaphore leaks and orphaned temp directories [`backend/app/services/view_service.py:171-174`](backend/app/services/view_service.py:171-174). **observed**

`_cache_lock` is a module-level `threading.Lock` defined after `render_view`, meaning cache eviction is serialised across all threads in the same process [`backend/app/services/view_service.py:177`](backend/app/services/view_service.py:177). **observed**

---

**Limitations:** This file alone does not reveal: the schema or field defaults of `ViewPreferences`, `MapRequest`, `GraphEntity`, `GraphRelation`, `EntityKind`, or `RelationKind`; the implementations of `build_structural_graph`, `inventory_entities`, `entity_id`, `_v1_root`, `_read_json`, `_write_json`, or `get_snapshot`; the content or API contract of `backend/app/rendering/bridge.js`; the Archify CLI's `deliver` command output format (beyond that its stdout is JSON and includes a `validation` key); whether the seven-directory cache cap is configurable at runtime; how `render_view` callers consume the returned dict; and whether `codecanopy.html` written to the temp directory is ever read before eviction.