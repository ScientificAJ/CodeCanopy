# Reusable Function Highlighting

Surfaces functions that are **defined in one file and called from at least one other file**, so developers can immediately see which utilities are shared across the codebase.

Supported languages: **Python**, **JavaScript / TypeScript**, **Java**.

---

## What Was Changed

### Backend

| File | Change |
|---|---|
| `backend/app/analyzers/python_analyzer.py` | Walks `ast.Call` nodes; populates `call_sites` on every parsed `File` |
| `backend/app/analyzers/js_analyzer.py` | New regex-based analyzer for `.js .jsx .ts .tsx .mjs .cjs` |
| `backend/app/analyzers/java_analyzer.py` | New regex-based analyzer for `.java` |
| `backend/app/core/analyzers.py` | Registers `JSAnalyzer` and `JavaAnalyzer` alongside `PythonAnalyzer` |
| `backend/app/features/reusable_functions/__init__.py` | Implements `ConcreteReusableFunctionService` — builds a definition index and a caller index from stored syntax data, then emits a `ReusableGroup` for every function called across file boundaries |
| `backend/app/api/v1/snapshots.py` | Adds `GET /api/v1/projects/{projectId}/snapshots/{snapshotId}/reusable-functions` |

### Frontend

| File | Change |
|---|---|
| `frontend/src/types/codebase.ts` | Adds `ReusableGroup` and `ReusableFunctionResult` interfaces |
| `frontend/src/services/v1/api.ts` | Adds `getReusableFunctions(projectId, snapshotId, minCallers?, signal?)` |
| `frontend/src/features/reusable_functions/useReusableFunctions.ts` | Data-fetch hook with abort-on-unmount |
| `frontend/src/features/reusable_functions/ReusableFunctionPanel.tsx` | Slot component — loading / error / empty states, grouped list with clickable source-jump buttons |
| `frontend/src/features/reusable_functions/register.ts` | Registers the panel into the `reuse.findings` slot |
| `frontend/src/features/index.ts` | Imports the registration module so the feature loads with the app |

### Code health fixes (same sprint)

- `CallSite` model forward-reference resolved in `codebase.py`
- Duplicate language-extension map removed from `project_storage.py` (now delegates to `inventory_service.LANGUAGES`)
- `SlotStatus` and `CapabilityLevel` changed from plain `str` subclasses to proper `str` enums; `FileCapability.level` default fixed to `.value`
- `SLOT_UNUSED.integration_path` corrected from `duplicate_detection` to `unused_code`
- `OverviewPage.tsx` deleted — `/overview` route now points directly to `MapPage`
- Legacy `services/api.ts` migrated to reuse the `ApiError` class from `v1/api.ts`
- `WorkspaceLayout` project-list effect dependency changed from `[projectId]` to `[]`
- `SourceViewer` `lineEnd` guard removed — always forwarded to the API
- `IntegrationPlaceholder` component wired into `SlotMount`; previously unused

---

## How to Test

### 1. Run the automated test suites

```bash
# Backend — 54 tests
cd backend
.venv/bin/python -m pytest --tb=short -q

# Frontend — 11 tests (5 test files)
cd ../frontend
npm test
```

Expected output:
```
# backend
54 passed, 1 warning

# frontend
Test Files  5 passed (5)
Tests      11 passed (11)
```

### 2. Start the dev servers

```bash
# Terminal 1 — API
cd backend
.venv/bin/uvicorn app.main:app --reload

# Terminal 2 — UI
cd frontend
npm run dev
```

### 3. Import a repository

1. Open `http://localhost:5173`
2. Import a public GitHub URL or upload a ZIP that contains Python, JS/TS, or Java files
3. Wait for the import to complete — you are redirected to the workspace

### 4. Open the Reuse panel

1. In the left nav, click **Reuse**
2. The panel fetches `GET .../reusable-functions?min_callers=1` and renders results
3. Each row shows the function name, the file it is defined in (click → jumps to that line in the source viewer), and the files that call it (click → jumps to that file)

### 5. Call the API directly

```bash
# Replace PROJECT_ID and SNAPSHOT_ID with values from the URL after import
curl -b codecanopy_workspace=<your-cookie> \
  "http://localhost:8000/api/v1/projects/{PROJECT_ID}/snapshots/{SNAPSHOT_ID}/reusable-functions?min_callers=1"
```

**Response shape:**
```json
{
  "snapshot_id": "...",
  "total_reusable": 3,
  "groups": [
    {
      "function_name": "parse_config",
      "defined_in": "src/utils/config.py",
      "defined_line_start": 12,
      "defined_line_end": 24,
      "called_from": ["src/server.py", "src/worker.py"]
    }
  ]
}
```

Use `?min_callers=2` to surface only functions used in two or more distinct files.

### 6. What to look for in the UI

- **Loading state** — "Scanning for reusable functions…" while the request is in flight
- **Empty state** — "No reusable functions detected across multiple files." for repos where nothing is shared
- **Results** — each group shows `functionName` in `<code>`, a button labelled `path/to/file.py:lineNumber` that jumps to the definition, and a list of caller files below it
- **Source navigation** — clicking any file button selects it in the source viewer on the right panel and scrolls to the correct line

---

## Known Limitations

- **Python** uses a full AST so extraction is precise. **JS/TS** and **Java** use regex and will miss dynamic calls (`getattr`, template-literal calls, reflection).
- Functions with common names (`init`, `main`, `render`) will appear as reusable if they exist in multiple call sites — use `min_callers=2` or higher to reduce noise.
- Only files processed during the import are covered. Binary, excluded, and files over 1 MiB are not parsed.
