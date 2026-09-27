# CodeCanopy

**See the structure. Find your path through the code.**

CodeCanopy imports a public GitHub repository or ZIP into a read-only snapshot,
then connects a searchable file tree, an interactive structure map, and bounded
source previews. Organize your view with labels and virtual groups, and export
that view as an interactive, offline HTML file.

The workspace includes a [dependency explorer](docs/dependency-analysis.md) for
Python and JavaScript/TypeScript file imports and function calls, with source
links, cycle detection, and potential change impact. Dependency analysis runs
locally without model credentials. Reuse, duplicate/unused findings and Ask have
separate connected modules; AI summaries, proposals and generated documents remain
extension slots.

## Run locally

Requirements: Linux/macOS, Python 3.11+ and Node.js 22+ with npm. Tested with
Python 3.14 and Node 24. The bounded Python parser uses POSIX resource limits;
on Windows use WSL for this slice. The legacy API remains available separately.

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open **http://127.0.0.1:5173**. Use the same hostname for frontend and backend
(`localhost` also works). The frontend defaults to port 8000 on its own host;
`VITE_API_BASE_URL` can override it. API documentation is at
http://127.0.0.1:8000/docs. These are the two existing development services;
there are no additional feature servers.

The API needs Node on PATH to run the vendored renderer. Set `CODECANOPY_NODE`
to an absolute Node executable if necessary. No installation inside
`vendor/archify` is needed.

## Explore a repository

1. Enter an HTTPS public GitHub URL, optionally with a branch/tag/commit, or
   upload a ZIP. GitHub refs resolve to a full immutable commit before download.
2. Wait for the import run. It can be cancelled; warnings produce a partial
   result with per-file diagnostics, not fabricated success.
3. Start on the factual overview, then open the architecture map or suggested
   README/manifests. Search the tree (Ctrl/Cmd+K), expand folders, and select a file. Double-click
   a folder or use its map-list arrow to drill down. Map selection and source
   inspection share canonical snapshot-scoped IDs.
4. Use Customize view to change labels, order, theme and map density. Create
   virtual groups from the complete inventory, rename/recolor them, and add or
   remove individual members. These preferences never modify source bytes.
5. Export HTML for the current map chapter. The export contains the graph,
   provenance and view preferences, plus Archify's offline interactions. Source
   contents are **not included**. It is a structural view, not an AI report or
   dependency analysis.

Automatic map density shows up to eight children on a wide canvas and three
on a narrow canvas; Customize view also offers explicit density choices.
Sibling paging, folder drilldown, the searchable full tree and the accessible
map list reach the remaining inventory. Browser Back restores focus, page,
selection, source evidence lines and camera; returning via Architecture resumes
the last view in this browser session. Recent imports are available on the
import page, alongside the storage policy and optional GitHub revision selector. No invented architectural
roles or semantic edges are added.

## Storage and bounds

- ZIP: 50 MiB upload, 25 MiB per file, 250 MiB extracted, 10,000 entries.
  Traversal, unsafe Windows names, symlinks, special files and unsupported
  compression are rejected. Generated/dependency directories are skipped.
- GitHub: unauthenticated public HTTPS only. Requests and redirects are checked
  against `github.com`, `api.github.com`, and `codeload.github.com` **before**
  following them. Metadata and archive downloads are bounded. No git hooks or
  repository installation scripts run.
- New workspace data: `CODECANOPY_SNAPSHOTS_DIR`, default
  `<system-temp>/codecanopy/snapshots`. The HttpOnly SameSite=Strict browser
  cookie scopes v1 access. This is a local, single-process workspace model,
  not a multi-user production identity service. Clearing the cookie loses
  access to that workspace.
- Source access expires after 24 hours. Cleanup runs every minute while the API
  is running and at startup; source/render bytes are removed then. Brief
  metadata tombstones and terminal runs are removed after two days. Use
  Snapshot storage → Delete imported repository for immediate deletion.
- Known secret filenames and private-key material are excluded. This is **not
  complete secret detection**; inspect archives before importing sensitive data.
- Valid UTF-8 text of any language is browsable; Python also honors encoding
  declarations. Binary/unsupported encodings have metadata only. Python syntax
  extraction reuses the existing analyzer, isolated to 1 MiB input, 384 MiB
  address space, 2 CPU seconds and a 4-second wall timeout per file. It never
  executes repository code. Other languages are honestly marked text-only.
- Source previews verify the full content hash and return at most 2,000 lines
  and 256 KiB. UI pages use 200 lines. Two imports run concurrently with four
  admitted jobs; processing has a three-minute deadline. Run status is durable;
  interrupted runs report failure after a server restart. Run **one** API worker.
- HTML runs in an opaque sandboxed iframe. A checked source-window, nonce,
  snapshot, view and entity bridge synchronizes selection. Export CSP prohibits
  network connections. No provider keys belong in browser code.

The legacy `/api/projects` API keeps its original storage, contracts and Python
analysis behavior (`CODECANOPY_PROJECTS_DIR`, default system-temp/codecanopy/projects).
Its original routes are not the session-scoped v1 service; keep this development
server on loopback. The v1 UI does not load old legacy uploads or old-name local
workspace sessions automatically.

## APIs and teammate integration

All new behavior is under `/api/v1`:

| Route | Purpose |
| --- | --- |
| `POST /session` | Establish the browser workspace cookie |
| `POST /imports/zip`, `/imports/github` | Return HTTP 202 with a durable run ID |
| `GET /runs/{id}`, `POST /runs/{id}/cancel` | Status, diagnostics and cancellation |
| `GET /projects`, `GET/DELETE /projects/{id}` | Workspace-owned imports |
| `GET /projects/{p}/snapshots` | Available snapshots |
| `GET …/snapshots/{s}` | Immutable revision and expiry |
| `GET …/{s}/files`, `/entities`, `/capabilities` | Inventory and honest coverage |
| `GET …/{s}/source/{file_id}` | Validated bounded line ranges |
| `GET …/{s}/dependencies` | Static file/function connections, evidence and coverage |
| `GET …/{s}/graph` | Bounded observed containment graph |
| `GET/PATCH …/{s}/view` | View-only preferences |
| `POST …/{s}/map` | Validated Archify HTML, graph, hashes and receipt |

Deferred backend endpoints return HTTP **501**, with a machine-readable
`NOT_CONNECTED` response. The UI's unregistered slots make no feature requests.
See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md),
[contract notes](contracts/README.md), [scope](docs/SCOPE.md), and the
[verification record](docs/VERIFICATION.md).

Future work should stay in independent feature packages, reuse these IDs and
source access, and keep provider calls server-side. Preserve the starter's
`backend/app/features` contracts. The registry accepts a component and optional
abortable adapter; its test-only example is not shipped as a feature.

## Verify

```bash
cd backend
.venv/bin/python -m pytest -q
cd ../frontend
npm run contracts
npm run lint
npm run build
npm test
```

For browser checks (the test runner starts both local servers when needed):

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

The browser test uses an explicitly synthetic ZIP, exercises real endpoints,
and checks selection, source pagination, organization, deferred pages, responsive
access and offline export. Screenshots and receipts stay in ignored
`bob_sessions/browser-evidence`. The container test configuration uses
`--no-sandbox`; normal desktop Chromium can use its own sandbox.

## Archify and licenses

Structure maps use the **complete, unmodified** `archify/` package from
[tt-a1i/archify](https://github.com/tt-a1i/archify/tree/9e35d2b0b39b155553ba9fcfe0b4f2a5198dd993/archify),
pinned to `9e35d2b0b39b155553ba9fcfe0b4f2a5198dd993`.
`vendor/archify.lock.json` records every file hash. CodeCanopy's compiler and
bridge are separate. No fallback diagram renderer is used. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Archify is MIT licensed, copyright tt-a1i and Cocoon AI; its license and bundled
font notices are retained. A license for the project's original application
code has not yet been selected. The supplied gecko image master is preserved
byte-for-byte; CSS viewports show the gecko beside the CodeCanopy wordmark.
