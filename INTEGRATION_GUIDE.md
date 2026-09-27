# Connecting a feature to CodeCanopy

This slice implements structural browsing and shared UI. Add feature behavior
through the public surfaces below; do not create another inventory, identity,
source fetcher or selected-file context. The starter backend feature contracts
under `backend/app/features` are preserved.

## Actual mount points

| Slot ID | Mounted by | Payload / backend endpoint |
| --- | --- | --- |
| `summaries.context-panel` | `frontend/src/pages/workspace/WorkspaceLayout.tsx` | `SummaryPayload`; `GET …/{snapshot}/summaries` |
| `dependencies.workspace` | `…/DependenciesPage.tsx` | `DependencyResult`; connected `GET …/{snapshot}/dependencies` |
| `map.overlay` | `…/MapPage.tsx` when registered | `DependencyOverlay`; same graph/evidence contract; inspector region below the structural map |
| `reuse.findings` | `…/OpportunitiesPage.tsx`, route `/opportunities/reuse` | `ReusableFunctionResult`; `GET …/{snapshot}/findings/reuse` |
| `duplicates.compare` | `…/OpportunitiesPage.tsx`, route `/opportunities/duplicates` | `DuplicateDetectionResult`; `GET …/{snapshot}/findings/duplicates` |
| `unused.review` | `…/OpportunitiesPage.tsx`, route `/opportunities/unused` | `UnusedDetectionResult`; `GET …/{snapshot}/findings/unused` |
| `ask.workspace` | `…/AskPage.tsx` | PRD `Answer`; `POST …/{snapshot}/answers` |
| `proposals.detail` | `…/ProposalsPage.tsx` | PRD `ChangePack`; `GET …/{snapshot}/proposals` |
| `docs.generated` | `frontend/src/App.tsx`, route `/docs` | `GeneratedDocument`; teammate adds an authorized document endpoint |

All mounts use `components/slots/SlotMount.tsx`. Unregistered or explicitly
unavailable features render `Unavailable`; they do not fetch anything. The
unimplemented v1 slots return 501 with `IntegrationSlotResponse` and
`NOT_CONNECTED`. Dependencies, reuse, duplicate and potentially-unused findings are connected and
return snapshot-scoped analysis results. Do not return 200 with dummy findings
or an empty successful analysis.

## Public exports and state

- `contexts/WorkspaceContext.tsx`: `WorkspaceProvider`, `useWorkspace`,
  `WorkspaceContextValue`, `SelectedEntity`, `ViewState`, `selectionFor`.
  It owns the current project, snapshot, files/entities, capabilities, run,
  selection, structural graph and preferences. Snapshot changes abort old
  reads and clear obsolete state.
- `contexts/SlotRegistry.ts`: `registerSlot`, `SlotProps<T>`, `SlotContext`,
  `SlotRegistration`, `RequestState<T>`, `FeatureAvailability`. Registration
  returns teardown; consumers update through `useSyncExternalStore`.
- `contexts/FeatureContracts.ts`: `registerFeature`, `FeaturePayloads`,
  `SummaryPayload`, `DependencyOverlay`, `FindingPage`, `GeneratedDocument`.
  Duplicate and unused slots use the canonical `DuplicateDetectionResult` and
  `UnusedDetectionResult` types from `types/v1`. Use this typed registration for
  a component/adapter pair. Availability
  (`connected`, `not-connected`, `unavailable`) is separate from request status
  (`idle`, `loading`, `ready`, `error`). A ready empty result is possible only
  after a connected adapter actually returns it.
- Every `SlotProps` receives projectId, snapshotId, snapshot, selectedEntity
  (including lineRange), files, entities, graph, capabilities, viewState,
  selectEntity, openSource and navigate. `openSource(fileId, {start,end})`
  checks membership and range order before navigating; the source API remains
  the authority for bounds, ownership, content hash and expiry.
- `services/v1/api.ts`: `request<T>`, `snapshotPath`, `ApiError`, all import/run,
  inventory, source, graph, findings, view and render methods. Requests use credentials
  and support cancellation. Keep all feature HTTP calls here or in a cohesive
  adapter importing `request`; never embed provider secrets in React.

## Structural view navigation and preferences

Map routes persist `focus`, `page`, `node` and optional evidence `start`/`end`
query parameters. Navigation state retains a per-history-entry camera key;
snapshot-scoped session storage holds the last route and bounded camera history.
Use `openSource` for evidence navigation so canonical file IDs and line ranges
remain synchronized with the source panel. Import now lands on a factual
`/overview`; `/map` remains the interactive Archify view.

The additive v1.1 preference fields are `density` (`auto`, `comfortable`,
`expanded`) and group `color` (`lime`, `blue`, `violet`, `amber`). Older persisted
preferences default to automatic density and lime groups. The map request
accepts `page_size` of 3 or 8 (default 8), in addition to focus/cursor. The UI
chooses 3 for an automatic canvas narrower than 640 CSS pixels, otherwise 8.
Group members are validated against the complete immutable inventory.

## Registering your implementation

1. Add your module beneath `frontend/src/features/<feature>/`.
2. Define its component against `SlotProps<FeaturePayloads['your.slot']>`.
   Handle each request state explicitly. Render repository text as text; if a
   document needs Markdown, use a sanitizer before enabling raw HTML.
3. Register once in a module entry file with `registerFeature`. Its `load`
   accepts shared `SlotContext` and `AbortSignal` and returns the matching
   payload. Validate snapshot/evidence membership before returning data.
4. Import that entry in `frontend/src/features/index.ts`. This is the only
   shared bootstrap edit. No edits to MapPage, StructureMap, WorkspaceLayout
   or SourceViewer are necessary.
5. Implement your backend feature in its own package, replace its v1 501 route,
   and use `snapshot_access` from `backend/app/api/v1/snapshots.py`. Source reads
   go through `snapshot_service.read_source_lines`; never search legacy project
   folders or open arbitrary caller-supplied paths.

Registration shape, as used by the dependency feature:

```tsx
import { registerFeature } from '../../contexts/FeatureContracts'
import { request, snapshotPath } from '../../services/v1/api'
import type { DependencyResult } from './types'
import { DependencyExplorer } from './DependencyExplorer'

registerFeature('dependencies.workspace', {
  Component: DependencyExplorer,
  load: (context, signal) => request<DependencyResult>(
    snapshotPath(context.projectId, context.snapshotId) + '/dependencies',
    { signal },
  ),
})
```

The dependency workspace uses `DependencyResult` with function nodes; see
[dependency analysis](docs/dependency-analysis.md). A future `map.overlay` adapter
must project its data into the separate `DependencyOverlay` contract. It receives
canonical visible graph IDs and full inventory context. Semantic relations are
not merged into the structural diagram automatically: the adapter is the
explicit boundary for a future validated projection, not an authorization to
invent them. `StructureMap` accepts only `MapArtifact` returned by the checked
compiler, and the bridge accepts only that artifact's declared entities.

## Contracts and evidence

`contracts/prd.schema.json` preserves the supplied design contract unchanged.
Evidence, SourceRange, Finding, Answer and ChangePack TypeScript definitions are
generated in `types/v1/prd.generated.ts`. The minimal structural 1.1 extension
and regeneration steps are described in `contracts/README.md`.

Use a source file's canonical ID, snapshot ID, original path, inclusive range
and full content SHA-256 for evidence. The inventory's `content_hash` maps to
the PRD Evidence field `content_sha256`. Entity display overrides do not change
these facts. `syntax_extraction=true` means syntax was extracted for a supported
language; it is not proof of resolved calls, safe reuse or unreachability.
Function findings currently parse Python, JavaScript, TypeScript/TSX, Go, Rust,
Java, Kotlin, C/C++, C#, Ruby, PHP, Bash and SQL. Other languages remain
browsable but are excluded from findings.

## Archify boundary

`backend/app/services/view_service.py` compiles observed containment or explicit
virtual-group membership into a maximum of four nodes. It runs the exact
pinned `vendor/archify/bin/archify.mjs deliver … --quality showcase --json`
with a timeout and two-render capacity limit. A failed check returns an error;
it never returns a previous view as a fresh successful result. Caches are
keyed by spec, snapshot/view manifest, wrapper version and bridge bytes.

`backend/app/rendering/bridge.js` uses the audited `data-node-id` seam and
actual `Archify.focus.set/clear` and `Archify.view.zoomIn/zoomOut/reset` APIs.
The iframe has `sandbox="allow-scripts"` and no same-origin privilege. Parent
messages require the actual frame window, a nonce, version, snapshot, view and
canonical allowlisted entity. Opaque origins require postMessage target `*`;
the source/nonce checks are therefore mandatory. Imported text never becomes
script. JSON is escaped before embedding; the HTML CSP blocks network access.

Upstream HTML remains byte-identical to the pinned renderer output. CodeCanopy
adds a separately hashed wrapper, bridge, provenance manifest, CSP and embedded
viewport styling; `upstream_sha256` and `html_sha256` are separate. Upstream
`deliver`, automated `visual-check`, and image review are separate verification
claims. Do not edit vendor source to repair a CodeCanopy compiler issue.

## Optional semantic scoring

Duplicate detection always runs from cached Python AST structure. To enable
semantic comparison, configure the backend process with:

| Environment variable | Purpose | Default |
| --- | --- | --- |
| `CODECANOPY_LLM_API_KEY` | Backend-only bearer credential; without it semantic scoring is disabled | unset |
| `CODECANOPY_LLM_BASE_URL` | OpenAI-compatible API base URL | `https://api.openai.com/v1` |
| `CODECANOPY_LLM_MODEL` | Provider model identifier | `gpt-4o-mini` |

The backend sends only the top eight structurally shortlisted pairs, with at
most 80 source lines and 4,000 characters per function. It does not send the
repository, and no provider setting or credential is sent to the frontend.
Semantic-provider failures leave structural findings available and are
reported as a limitation.

## Tests before connecting

- `backend/tests/test_v1_workspace.py`: source identity, policy, import/export,
  grouping isolation, expiry and unsafe archives.
- `backend/tests/test_v1_boundaries.py`: live PRD schema validation, pinned
  GitHub adapter/redirect checks, cancellation, retention, no stale output and
  every supported diagram chapter size.
- `frontend/src/contexts/SlotRegistry.test.tsx`: isolated component plus adapter
  mounted on the real SlotMount with source navigation; unavailable adapter
  stays idle. This example is test-only.
- `frontend/src/services/exportService.test.ts`: export integrity and forged
  bridge message rejection.
- `frontend/src/components/tree/RepositoryTree.test.tsx`: keyboard expansion,
  deep selection and canonical search navigation.
- `frontend/e2e/workspace.spec.ts`: real ZIP endpoints, map/tree/source behavior,
  persisted groups/labels, all deferred routes, five desktop sizes, mobile
  source access, and an interactive export with networking disabled.

Reuse findings use cached AST call sites, canonical file IDs and source ranges. Matches are same-language name candidates; ambiguous definitions are omitted. See docs/reusable-functions.md for coverage and compatibility details.
