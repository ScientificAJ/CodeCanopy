# Dependency explorer

Open **Dependencies** after importing a repository. Choose Files or Functions,
select a focus, and follow the **Used by → selected item → Depends on** diagram.
The list provides line-specific import/call evidence and definition links through
the shared source browser. Search filters connected items. Potential impact walks
incoming connections transitively; a cycle notice identifies a path back to the
selection. Both views support keyboard navigation and narrow screens.

## Resolution and evidence

`GET /api/v1/projects/{project_id}/snapshots/{snapshot_id}/dependencies` requires
the existing workspace session and checks project membership and snapshot expiry.
It returns `DependencyResult` with file/function nodes, directed import/call edges,
unresolved references, and coverage. Every edge has a canonical file ID and an
inclusive source range; reading that evidence also validates the snapshot's source
hash. IDs and results are deterministic for the same snapshot. The containment map
and its offline export remain structural views.

Binding metadata is extracted during import by the existing resource-limited
syntax worker. Repository code is never imported or executed. This feature uses
no AI provider, credentials, network module resolution, or package installation.

Supported static resolution:

- Python repository-root and package-relative imports, aliases, explicit function
  imports, and module-qualified calls to unambiguous module-level definitions.
- JavaScript/TypeScript/TSX relative ES imports, named aliases, direct named/default
  function exports, namespace imports, extension and directory-index resolution.
  A `.js` specifier can resolve a unique `.ts`/`.tsx` file if no `.js` file exists.
- Same-file calls, cross-file calls, recursion, and cycles. File view projects call
  endpoints to their owning files alongside import connections.

Calls are potential static relationships, not proof of execution or breakage.
Unsupported or ambiguous calls remain unresolved: dynamic dispatch, object methods,
closures, decorated Python targets, shadowed/reassigned bindings, CommonJS,
re-exports, custom Python source roots, tsconfig aliases, package exports and
external packages. Conditional/local Python imports are not resolved. JavaScript
shadow detection is deliberately conservative across the file, so it may omit
valid calls if another scope uses the same name. Repeated calls between the same
endpoints on the same line share one evidence edge. Other parsed languages still
show their function inventory but do not claim resolved dependencies.

Old snapshots remain readable. They have no new binding metadata; re-import to
analyze dependencies. The UI distinguishes unavailable coverage from an analyzed
file with no resolved connections. Excluded files and binaries do not become
source nodes, and no source is sent to an external service.

## Bounds and validation

The existing parser enforces a 1 MiB input cap, CPU/memory budgets and a subprocess
timeout. The response caps nodes at 5,000, edges at 15,000, and displayed unresolved
references at 3,000, marking truncation explicitly. Total unresolved counts remain
available. Impact traversal visits at most 1,000 items and reports a partial result
when needed. The diagram shows six immediate neighbors per side; the connection
list is paged in groups of 50. Unresolved details show the first 100 references for
the selection. Evidence previews reuse the bounded source API.

- `backend/tests/test_dependencies.py`: real ZIP imports, Python and JS/TS binding
  resolution, ambiguous names, shadowing, minified same-line functions, cycles,
  source evidence, old snapshots, session isolation, expiry, and response limits.
- `frontend/src/features/dependencies/DependencyExplorer.test.tsx`: file projection,
  transitive impact and cycles, traversal bounds, filtering, source navigation,
  empty coverage and request failures.
- `frontend/e2e/workspace.spec.ts`: real backend/browser integration, file/function
  selection, import/call evidence, impact filtering, mobile width and existing
  repository workflows.

AI summaries are a separate feature and are unchanged by this implementation.
