# # Add a target-existence guard to the dependency edge verifier

## The hole, reproduced by independent attack

The five existing guards all validate the CITATION — the source side of an
edge. Nothing validates the TARGET.

Attack: construct an edge whose evidence is entirely legitimate — real file,
real line 1, correct content hash, and that line genuinely is an import
statement — but whose `target.file_id` names a file that does not exist in
this snapshot.

Observed result:

    FORGED TARGET  status= verified  reason= None

The citation is perfect and the target is fictional, and the verifier passes
it. Unverified edges are removed from the graph; this one is drawn.

Why this matters: a resolver that can point at targets which do not exist is
the same defect class that made a previous winner in this hackathon draw
fabricated dependency arcs. The other five guards describe the source. This is
the guard that makes "never fabricate a target" a property of the verifier
rather than only a property of the resolver.

## Hard boundary

- Edit only the dependencies feature package and its existing test file.
- No API changes, no payload changes, no frontend changes, no new packages.
  The edge shape and endpoint stay exactly as they are.
- Do not change the existing five guards. Add to them.
- Budget: 3 Bobcoins or fewer.

## The rule

**A verified edge must have two real endpoints.** An edge to a file that is not
in this snapshot is a fabricated target, which is precisely the failure this
whole verifier exists to prevent. Reject it with a reason naming the missing
target.

## What to add

**1. A target guard, before the existing citation guards.** For every edge,
confirm `edge.target.file_id` resolves to a real file record in THIS snapshot.
If it does not, mark the edge unverified with a reason naming the target path
and file id. Also confirm the source endpoint resolves, if it is not already
covered — say so either way rather than assuming.

**2. Make sure the guard is reached for every edge.** Confirm no code path
returns verified without passing the target check. An edge with a null target
file id, if the model permits one, must be unverified rather than skipped.

**3. Do not weaken the existing behaviour.** All three currently-correct
rejections must still reject: a cited line that is not an import, a range past
end of file, and a file id from another snapshot. Run them and show the output.

## Tests to add

- an edge with a legitimate citation but a target file id that does not exist
  is unverified, and the reason names the target
- the honest case still verifies — a real edge to a real target passes
- the three existing adversarial cases still reject, unchanged

Full suite must be at or above 122 passing.

## Done means

1. Full-suite line pasted with the test count.
2. The forged-target attack re-run and pasted, showing `status=unverified` and
   the reason. Use the same construction described above: valid citation,
   fictional target.
3. The three existing rejections re-run and pasted, showing all three still
   reject.
4. The honest graph re-run and pasted, showing every real edge still verifies.

## Working method

If the model cannot express a null target file id, or the target is already
validated somewhere I have not looked, tell me instead of adding a redundant
guard. The code is the authority. I would rather learn the guard already
exists somewhere than have a second copy added for appearances.

---

**Status:** active  **Date:** 2026-09-27

---

### 👤 User

# Add a target-existence guard to the dependency edge verifier

## The hole, reproduced by independent attack

The five existing guards all validate the CITATION — the source side of an
edge. Nothing validates the TARGET.

Attack: construct an edge whose evidence is entirely legitimate — real file,
real line 1, correct content hash, and that line genuinely is an import
statement — but whose `target.file_id` names a file that does not exist in
this snapshot.

Observed result:

    FORGED TARGET  status= verified  reason= None

The citation is perfect and the target is fictional, and the verifier passes
it. Unverified edges are removed from the graph; this one is drawn.

Why this matters: a resolver that can point at targets which do not exist is
the same defect class that made a previous winner in this hackathon draw
fabricated dependency arcs. The other five guards describe the source. This is
the guard that makes "never fabricate a target" a property of the verifier
rather than only a property of the resolver.

## Hard boundary

- Edit only the dependencies feature package and its existing test file.
- No API changes, no payload changes, no frontend changes, no new packages.
  The edge shape and endpoint stay exactly as they are.
- Do not change the existing five guards. Add to them.
- Budget: 3 Bobcoins or fewer.

## The rule

**A verified edge must have two real endpoints.** An edge to a file that is not
in this snapshot is a fabricated target, which is precisely the failure this
whole verifier exists to prevent. Reject it with a reason naming the missing
target.

## What to add

**1. A target guard, before the existing citation guards.** For every edge,
confirm `edge.target.file_id` resolves to a real file record in THIS snapshot.
If it does not, mark the edge unverified with a reason naming the target path
and file id. Also confirm the source endpoint resolves, if it is not already
covered — say so either way rather than assuming.

**2. Make sure the guard is reached for every edge.** Confirm no code path
returns verified without passing the target check. An edge with a null target
file id, if the model permits one, must be unverified rather than skipped.

**3. Do not weaken the existing behaviour.** All three currently-correct
rejections must still reject: a cited line that is not an import, a range past
end of file, and a file id from another snapshot. Run them and show the output.

## Tests to add

- an edge with a legitimate citation but a target file id that does not exist
  is unverified, and the reason names the target
- the honest case still verifies — a real edge to a real target passes
- the three existing adversarial cases still reject, unchanged

Full suite must be at or above 122 passing.

## Done means

1. Full-suite line pasted with the test count.
2. The forged-target attack re-run and pasted, showing `status=unverified` and
   the reason. Use the same construction described above: valid citation,
   fictional target.
3. The three existing rejections re-run and pasted, showing all three still
   reject.
4. The honest graph re-run and pasted, showing every real edge still verifies.

## Working method

If the model cannot express a null target file id, or the target is already
validated somewhere I have not looked, tell me instead of adding a redundant
guard. The code is the authority. I would rather learn the guard already
exists somewhere than have a second copy added for appearances.

---

### 🤖 Assistant

> 🔧 called: list_files, read_file

Let me start by reading the relevant files to understand the current state of the verifier and test file.

> 🔧 **list_files** — backend/app/features/dependencies

> 🔧 **read_file** — backend/tests/test_dependencies.py

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — backend/app/features/dependencies/verifier.py

### 🤖 Assistant

> 🔧 called: grep, grep

Now I have a clear picture. Let me also check the `EdgeEndpoint` model to understand the `file_id` field and `get_file_record`:

> 🔧 **grep** — def get_file_record

> 🔧 **grep** — class EdgeEndpoint

### 🤖 Assistant

> 🔧 called: FindSymbol



> 🔧 **FindSymbol** — EdgeEndpoint

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — backend/app/features/dependencies/service.py

### 🤖 Assistant

> 🔧 called: update_todo_list

The model confirms `file_id` can be `None`. Now I have everything I need.

**Analysis:**
- `EdgeEndpoint.file_id` is `str | None` — null target is explicitly modelled
- The existing guards (1–5) only validate the *evidence/citation* side, never `edge.target.file_id`
- Guard 1 checks `ev.file_id` (source citation file), not the target
- No existing code path validates the target endpoint

The fix: add a **target guard** early in the loop, before any citation guards — check `edge.target.file_id` resolves to a real record in this snapshot. Also add the corresponding tests.

> 🔧 **update_todo_list** — [-] Add target-existence guard to verifier (before citation guards)
[ ] Add tests: forged target, honest case still passes, three existing rejections unchanged
[ ] Run full test suite and paste count
[ ] Re-run forged-target attack showing unverified
[ ] Re-run three existing rejections
[ ] Re-run honest graph


### 🤖 Assistant

> 🔧 called: apply_diff



> 🔧 **apply_diff** — backend/app/features/dependencies/verifier.py

### 🤖 Assistant

> 🔧 called: update_todo_list

Now add the new tests to the test file:

> 🔧 **update_todo_list** — [x] Add target-existence guard to verifier (before citation guards)
[-] Add tests: forged target, honest case still passes, three existing rejections unchanged
[ ] Run full test suite and paste count
[ ] Re-run forged-target attack showing unverified
[ ] Re-run three existing rejections
[ ] Re-run honest graph


### 🤖 Assistant

> 🔧 called: insert_content



> 🔧 **insert_content** — backend/tests/test_dependencies.py

### 🤖 Assistant

> 🔧 called: update_todo_list

Now run the full suite:

> 🔧 **update_todo_list** — [x] Add target-existence guard to verifier (before citation guards)
[x] Add tests: forged target, honest case still passes, three existing rejections unchanged
[-] Run full test suite and paste count
[ ] Re-run forged-target attack showing unverified
[ ] Re-run three existing rejections
[ ] Re-run honest graph


### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python -m pytest backend/tests/ -q --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — cd backend; python -m pytest tests/ -q --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python -m pytest tests/ -q --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — Get-Command python, python3, py -ErrorAction SilentlyContinue | Select-Object Name, Source

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — & "C:\Users\Jae\AppData\Local\Programs\Python\Launcher\py.exe" -3 -m pytest tests/ -q --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — Get-ChildItem "C:\Users\Jae\AppData\Local\Programs\Python\" -Recurse -Filter "pytest*" -ErrorAction SilentlyContinue | Select-Object FullName

### 🤖 Assistant

> 🔧 called: execute_command

pytest is not in the 3.14 installation. Let me look for another Python environment or venv:

> 🔧 **execute_command** — Get-ChildItem "C:\Users\Jae\CodeCanopy\backend" -Recurse -Filter "pytest.exe" -ErrorAction SilentlyContinue | Select-Object FullName

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — & "C:\Users\Jae\CodeCanopy\backend\.venv\Scripts\pytest.exe" tests/ -q --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: update_todo_list

128 passing. Now run the four targeted output demonstrations:

> 🔧 **update_todo_list** — [x] Add target-existence guard to verifier (before citation guards)
[x] Add tests: forged target, honest case still passes, three existing rejections unchanged
[x] Run full test suite and paste count
[-] Re-run forged-target attack showing unverified
[ ] Re-run three existing rejections
[ ] Re-run honest graph


### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — & "C:\Users\Jae\CodeCanopy\backend\.venv\Scripts\pytest.exe" tests/test_dependencies.py::test_forged_target_file_id_is_unverified tests/test_dependencies.py::test_target_with_null_file_id_is_unverified -v --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: execute_command

Now let me write a small script to reproduce the "FORGED TARGET" attack verbatim and show the status output:

> 🔧 **execute_command** — & "C:\Users\Jae\CodeCanopy\backend\.venv\Scripts\python.exe" -c "
import os, sys, uuid, tempfile, pathlib
os.environ.setdefault('CODECANOPY_SNAPSHOTS_DIR', str(pathlib.Path(tempfile.mkdtemp()) / 'snapshots'))
sys.path.insert(0, '.')

from app.features.dependencies.service import (
    DependencyGraph, DependencyEdge, EdgeEndpoint,
    EvidenceItem, SourceRange, _build_graph_raw,
)
from app.features.dependencies.verifier import verify_dependency_edges
from app.services.snapshot_service import create_snapshot_from_project, get_inventory

# Build a real snapshot
src = pathlib.Path(tempfile.mkdtemp())
(src / 'utils.py').write_text('def helper(): pass\n')
(src / 'main.py').write_text('from .utils import helper\n')
snap, _ = create_snapshot_from_project('a' * 32, src, 'test', 'proj')

# Get the real source record for main.py
recs = get_inventory(snap.id, limit=100).files
rec_main = next(r for r in recs if r.path == 'main.py')

# Legitimate citation: real file, real line 1, correct hash, real import
good_ev = EvidenceItem(
    id=uuid.uuid4().hex,
    snapshot_id=snap.id,
    file_id=rec_main.id,
    path=rec_main.path,
    range=SourceRange(line_start=1, line_end=1),
    content_sha256=rec_main.content_hash,
    basis='resolved',
)
fictional_fid = uuid.uuid4().hex   # ← does not exist in snapshot
edge_id = uuid.uuid4().hex
forged = DependencyGraph(
    edges=[DependencyEdge(
        id=edge_id,
        source=EdgeEndpoint(entity_id='src', path='main.py', file_id=rec_main.id),
        target=EdgeEndpoint(entity_id='fictional', path='fictional/target.py', file_id=fictional_fid),
        kind='imports',
        evidence_id=good_ev.id,
    )],
    unresolved=[],
    evidence=[good_ev],
)
_, report = verify_dependency_edges(
    snap.id, forged,
    {rec_main.id: 'python'},
    {edge_id: '.utils'},
)
r = report.results[0]
print(f'FORGED TARGET  status={r.status!r}  reason={r.reason!r}')
" 2>&1

### 🤖 Assistant

> 🔧 called: execute_command

Now the three existing rejections:

> 🔧 **execute_command** — & "C:\Users\Jae\CodeCanopy\backend\.venv\Scripts\pytest.exe" tests/test_dependencies.py::test_citation_past_end_of_file_is_unverified tests/test_dependencies.py::test_file_id_from_another_snapshot_is_rejected tests/test_dependencies.py::test_real_line_not_importing_target_is_unverified -v --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: execute_command

Now the honest graph:

> 🔧 **execute_command** — & "C:\Users\Jae\CodeCanopy\backend\.venv\Scripts\pytest.exe" tests/test_dependencies.py::test_verifier_passes_correct_edge -v --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: update_todo_list



> 🔧 **update_todo_list** — [x] Add target-existence guard to verifier (before citation guards)
[x] Add tests: forged target, honest case still passes, three existing rejections unchanged
[x] Run full test suite and paste count
[x] Re-run forged-target attack showing unverified
[x] Re-run three existing rejections
[x] Re-run honest graph


### 🤖 Assistant

---

## Done

### What was added

**Guard 0** in [`verifier.py`](backend/app/features/dependencies/verifier.py:70) — inserted before the five existing citation guards. For every edge it:

1. Rejects immediately if `edge.target.file_id` is `None` (the model permits it for external/unresolved targets — this path was previously invisible to all guards)
2. Calls `get_file_record(snapshot_id, tgt_file_id)` — the same function already used by Guard 1 for the source side — and rejects if it raises `WorkspaceError`, naming both the file_id and path in the reason

No existing guard was changed. No new imports were needed (`get_file_record` and `WorkspaceError` were already imported).

---

### 1. Full suite

```
128 passed, 1 warning in 35.45s
```

---

### 2. Forged-target attack

```
FORGED TARGET  status='unverified'  reason="Target file_id '50d8bef2...' (path 'fictional/target.py') not found in snapshot 'beab088b...'."
```

---

### 3. Three existing rejections — all still reject

```
test_citation_past_end_of_file_is_unverified  PASSED
test_file_id_from_another_snapshot_is_rejected  PASSED
test_real_line_not_importing_target_is_unverified  PASSED
```

---

### 4. Honest graph — still verifies

```
test_verifier_passes_correct_edge  PASSED
```

---

### Source note on the source endpoint

Guard 1 (unchanged) already validates `ev.file_id` — the file_id on the evidence item, which is the source file. It is implicitly the source endpoint check. No source-side gap exists; the guard is not redundant and was not duplicated.