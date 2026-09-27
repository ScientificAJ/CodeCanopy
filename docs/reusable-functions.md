# Cross-file reuse candidates

The Reusable code page lists possible cross-file calls from the same cached syntax
used for duplicate and unused-function analysis. Python uses the Python AST;
JavaScript/TypeScript, Java and the other configured languages use Tree-sitter.
The JS/Java legacy adapters also use Tree-sitter rather than regular expressions.
No imported code is executed and no model provider is required for reuse analysis.

## Contract and integration

`GET /api/v1/projects/{project}/snapshots/{snapshot}/findings/reuse?min_callers=1`
returns `ReusableFunctionResult`. The original `/reusable-functions` path remains
an alias. Both routes use the existing workspace ownership and snapshot expiry checks.
`min_callers` accepts 1–50 distinct caller files. The frontend registers a typed
`reuse.findings` adapter alongside the existing duplicate, unused and Ask features.

Each result includes `groups`, `total_reusable`, `analyzed_files`,
`ambiguous_names`, and `limitations`. Each group contains the definition's canonical
file ID and full line range, caller file paths, and precise call-site evidence
(file ID, path, start/end line). Clicking either definition or caller opens the
shared source viewer. Paging and line jumps release the original selected range.

## Interpretation and coverage

A name with exactly one definition in a language can be a candidate when another
parsed file calls that name. Multiple definitions of the same name are omitted,
including repeated method names; no definition is silently overwritten. Calls in
another language and same-file calls do not count. Comments, strings and function
declarations are not calls. Results are deterministically ordered by distinct
caller count, definition path, line and name.

These are review candidates, not resolved dependencies or proof of safe reuse.
Imports, aliases, object types, reflection and dynamic dispatch are not resolved.
Embedded language bodies and unsupported/excluded/failed files can be incomplete.
The panel displays coverage and these limitations even for empty results.
Snapshots created before call-site extraction require re-import; their missing
call evidence is explicitly reported. Missing or corrupt analysis data produces
an error instead of an empty successful result.

## Verification

Backend tests import real Python, JavaScript, TypeScript and Java projects and
exercise same-name ambiguity, cross-language separation, non-call text, caller
thresholds, legacy snapshots, source evidence, session isolation, wrong project,
expiry, and coexistence with duplicate/unused findings. Frontend tests cover
canonical definition/caller navigation and source paging after a selected range.
The browser workflow exercises reuse findings, JavaScript caller evidence, Python
source navigation, existing findings, Ask registration, workspace layout and export.
