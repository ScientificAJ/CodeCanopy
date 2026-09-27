# CodeCanopy visualization/shared-UI scope

Recovered from IBM Bob's implementation session
`f1bb6425233af7a645a4edf70662f791` and its preceding clone session. Bob stopped
at its budget limit after initial frontend build/tests; its GitHub import,
source storage, renderer and extension mounts still needed implementation.
Original session data and the supplied reference package remain local and
ignored. The subsequent user instruction renamed the product and GitHub
repository to CodeCanopy.

| Area | Decision |
| --- | --- |
| Preserve | Existing FastAPI health/projects endpoints, archive extraction limits, PythonAnalyzer, feature contracts, React/TypeScript/Vite stack, repository history |
| Implement | ZIP and public GitHub import, immutable snapshots, source/hash access, complete tree/search, bounded Archify maps, synchronized selection, grouping/labels/order/theme, portable HTML export |
| Necessary shared foundation | Local workspace sessions, bounded jobs and cancellation, per-file capability/diagnostic reporting, expiry/deletion, shared typed state/API/registration, keyboard and responsive shell |
| Deferred | AI summaries, dependency/call discovery and impact computation, reuse/duplicates/unused engines, Ask/retrieval, proposals and generated documents |

Ordinary implementation decisions: single API process; filesystem persistence;
24-hour source lifetime; 1.1 extensions to the supplied design contracts;
adaptive chapters of three or eight siblings for readable embedded labels; every full
inventory path remains reachable through tree paging/search. Folder membership
and user-group membership are the only produced relations. The renderer's
`external` primitive is a neutral drawing shape, not a claim that a file is an
external service; the visible subtitle names its actual repository kind.

Current limits: no private GitHub authentication, no semantic analysis beyond
the preserved Python syntax extractor, no team accounts, no distributed worker
queue, no source contents in HTML exports. Browser workspaces made under the
old product name are not migrated. No paid inference, deployment, permission
changes, source rewrites or imported-code execution are part of this task.

## Shared UI completion (2026-09-27)

The import page exposes ZIP upload, optional GitHub revisions, recent imports,
and retention/exclusion disclosures. A factual overview links documentation,
manifests, folders and dependency analysis. Map history preserves focus, page,
selected source evidence and camera; groups support names, colors and individual
member edits. The source snapshot is unchanged by all view preferences.

The deferred row above records the original foundation scope. Subsequent team
work connected dependency/call analysis, reuse, duplicate and potentially-unused
findings, and repository questions. This completion does not add AI file/folder
summaries, proposals or generated documents. See the current integration guide
and verification record for connected features and their limits.
