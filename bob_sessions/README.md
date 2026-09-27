# GREPO — BOB session evidence

Task folders follow the numbered, descriptive layout established by JAE: a
`session-summary.md` alongside the available transcript and screenshots.
Folder numbers are index positions; the original task IDs are preserved.

Panel screenshots follow the naming convention in the hackathon guide —
`team_taskNN_description_summary.png` — so a reviewer can identify a task
without opening it. The task transcripts keep their original exported
filenames.

| Folder | Contributor | Task / evidence |
| --- | --- | --- |
| [00-cited-summary-analysis](00-cited-summary-analysis/session-summary.md) | JaePyJs | Cited-summary prompt validation |
| [01-summaries-engine](01-summaries-engine/session-summary.md) | JaePyJs | Citation-verified summaries engine |
| [02-dependencies](02-dependencies/session-summary.md) | JaePyJs | Dependency analysis |
| [03-impact-fix](03-impact-fix/session-summary.md) | JaePyJs | Change-impact correction |
| [04-target-guard](04-target-guard/session-summary.md) | JaePyJs | Dependency target guard |
| [05-ask-slot](05-ask-slot/session-summary.md) | JaePyJs | Ask slot wiring and greeting |
| [06-arjun-repository-setup](06-arjun-repository-setup/session-summary.md) | Arjun / ScientificAJ | Repository clone and remote setup |
| [06-ask-render-fix](06-ask-render-fix/session-summary.md) | JaePyJs | Ask response rendering fix (markdown truncation) |
| [07-arjun-structure-workspace](07-arjun-structure-workspace/session-summary.md) | Arjun / ScientificAJ | Initial structure/UI implementation and supporting verification artifacts |
| [08-sajidHameed-chatbot-work](08-sajidHameed-chatbot-work/supporting-evidance/bob-task-2fc52ee1607d5411ee797478405e17df-2026-09-27.md) | SajidHameed | Repository Q&A PRD explanation (transcript only, no session summary supplied) |

## Bobcoin usage

Bobcoin figures are read from each task's own summary panel, not estimated.

| Task ID | Work | Bobcoins |
| --- | --- | --- |
| `681a0938…`, `64a0bdec…`, `8fd491fa…` | Cited-summary analysis and summaries engine | 17.95 |
| `c33b7b17fa8c9ac17554dea8c34de28e` | Dependency graph and change impact | 8.10 |
| `43a21cfe5525f4493c6c6e6bf29c5605` | Change-impact correction for folder and root subjects | 2.02 |
| `40a1564f2628dad5e9d0e678e46663c8` | Dependency target-existence guard | 1.51 |
| `a81ad5b9d10223df4ea559efdeadb608` | Ask response rendering fix | 5.50 |
| `84f1cdb8943d28e56aa8050a22464bb0` | Ask slot greeting and frontend wiring | 4.80 |
| | **Total** | **39.88** |

Context usage across those panels ranged from 13% to 41% of the 270k budget,
so the work was scoped to fit rather than run to the limit. The four
dependency and rendering tasks together cost 17.13 Bobcoins and each one
answered a specific defect found by testing, not a speculative feature.

Panels are archived as screenshots in each task folder and remain the source
of record for these figures.

Arjun's files were originally committed in
[`2046087`](https://github.com/ScientificAJ/CodeCanopy/commit/2046087fe335674d2e216db1663ab9a581d9cd50).
The reorganization preserves every original screenshot, recovered message,
transcript, fixture, and browser artifact without changing its contents.
Historical references to Grepo or CodeCanopy remain as captured; the current
displayed product name is **GREPO**, and the repository is
[`ScientificAJ/CodeCanopy`](https://github.com/ScientificAJ/CodeCanopy).

The new summaries describe the existing evidence; they are not additional BOB
session exports. Arjun's task folders also contain `bob_task_2026-09-26_*.md`
conversations reconstructed from the archived messages, checked against the
local BOB database, and formatted like Jae's Markdown exports. The original
JSON records and full text transcripts retain system context and tool outputs.
Browser screenshots and test receipts are supporting product
verification, separate from BOB task/usage screenshots. New E2E runs write to
`local-verification/` so they do not overwrite the archived evidence.
