# GREPO — BOB session evidence

Task folders follow the numbered, descriptive layout established by JAE: a
`session-summary.md` alongside the available transcript and screenshots.
Folder numbers are index positions; the original task IDs and screenshot
filenames are preserved.

| Folder | Contributor | Task / evidence |
| --- | --- | --- |
| [00-cited-summary-analysis](00-cited-summary-analysis/session-summary.md) | JaePyJs | Cited-summary prompt validation |
| [01-summaries-engine](01-summaries-engine/session-summary.md) | JaePyJs | Citation-verified summaries engine |
| [02-dependencies](02-dependencies/session-summary.md) | JaePyJs | Dependency analysis |
| [03-impact-fix](03-impact-fix/session-summary.md) | JaePyJs | Change-impact correction |
| [04-target-guard](04-target-guard/session-summary.md) | JaePyJs | Dependency target guard |
| [05-ask-slot](05-ask-slot/session-summary.md) | JaePyJs | Ask slot wiring and greeting |
| [06-arjun-repository-setup](06-arjun-repository-setup/session-summary.md) | Arjun / ScientificAJ | Repository clone and remote setup |
| [07-arjun-structure-workspace](07-arjun-structure-workspace/session-summary.md) | Arjun / ScientificAJ | Initial structure/UI implementation and supporting verification artifacts |

Arjun's files were originally committed in
[`2046087`](https://github.com/ScientificAJ/CodeCanopy/commit/2046087fe335674d2e216db1663ab9a581d9cd50).
The reorganization preserves every original screenshot, recovered message,
transcript, fixture, and browser artifact without changing its contents.
Historical references to Grepo or CodeCanopy remain as captured; the current
displayed product name is **GREPO**, and the repository is
[`ScientificAJ/CodeCanopy`](https://github.com/ScientificAJ/CodeCanopy).

The new summaries describe the existing evidence; they are not additional BOB
session exports. Browser screenshots and test receipts are supporting product
verification, separate from BOB task/usage screenshots. New E2E runs write to
`local-verification/` so they do not overwrite the archived evidence.
