# GREPO, IBM Bob Usage Statement

**IBM Bob supported repository foundations, analysis, chat, template auditing and targeted fixes.**

The evidence is organized in [`bob_sessions/`](../bob_sessions/README.md), preserving the original task IDs where available, transcripts, screenshots and contributor attribution. Folder numbers and screenshot labels organize the archive; they do not establish a task count.

## Contributors and concrete work

- **Arjun / ScientificAJ:** repository setup and the initial shared structure/UI slice, including the import, tree, source and map workflow. His [session record](../bob_sessions/07-arjun-structure-workspace/session-summary.md) separates the recorded frontend checks and budget/backend-tooling limits from subsequent completion and verification.
- **Jae / JaePyJs:** cited-summary probes and engine, dependency analysis, change-impact and target-verification corrections, and Ask wiring/greeting/rendering fixes. The original briefs, task IDs and panels remain in the [indexed folders](../bob_sessions/README.md).
- **Sajid / SajidHameed:** repository Q&A planning followed by chat implementation and fixes. The [transcript](../bob_sessions/08-sajidHameed-chatbot-work/supporting-evidance/bob-task-2fc52ee1607d5411ee797478405e17df-2026-09-27.md) contains code changes beyond its initial PRD explanation; the [usage capture](../bob_sessions/08-sajidHameed-chatbot-work/supporting-evidance/summary_of_chatbot_and_project.png) is also preserved.
- **Hero:** audit of template edge cases and redundant logic, then reusable-function discovery across the analyzer, API and frontend layers. The [new evidence and reflection](../bob_sessions/09-hero-template-audit-reusable-functions/session-summary.md) record shared-map/request-wrapper cleanup, source-range handling, Python AST call-site extraction, initial regex-based JS/TS and Java analysis, and source-linked reuse UI work. Hero describes using Bob's plan for repository-wide analysis and separating implementation, syntax review and tests into focused roles. The captures include both completed reports and mixed coordination-tool outcomes, so they do not establish an uninterrupted successful parallel run.

## How Bob helped improve correctness

The [dependency target-guard task](../bob_sessions/04-target-guard/session-summary.md) closed a concrete trust gap: an edge could carry a valid source citation while naming a target file that did not exist. Bob added target-existence/null-target guards and focused tests. That task's panel records **1.51 Bobcoins**.

Bob also challenged incorrect initial diagnoses. For [change impact](../bob_sessions/03-impact-fix/session-summary.md), the repository-root/no-selection case needed correction while the folder case already worked. For [Ask rendering](../bob_sessions/06-ask-render-fix/session-summary.md), the suspected streaming issue was actually markdown cut by a short preview. These records show why reviewing the implementation path mattered more than accepting the first description of a bug.

Hero's screenshots add another example of this review discipline: the checklist acknowledges that some model fixes had already been made externally, while the remaining work addressed shared helpers and feature integration. The reports list historical template checks of **41/41 backend and 7/7 frontend tests**, and later **11/11 frontend tests** for the reuse work. These are captured summary claims, not a new combined test total or proof that the current application is identical to that historical state.

## Usage figures and evidence boundaries

The earlier **39.88-Bobcoin figure belongs to a historical report about Jae's archived subset**, not the whole team. Its grouped subtotal is not reconciled by the individual screenshots; the [session index](../bob_sessions/README.md#bobcoin-usage) lists the identifiable panel values and the duplicate capture. It must not be represented as a verified team total or evidence that all work fit one 40-coin allowance.

Hero's new capture shows **19.96 Bobcoins and 158.5k / 270.0k context (59%)**, but no original task ID or date. It is preserved as displayed and is not added to other contributors' figures.

The new screenshots show Python AST traversal, but the JS/TS and Java implementations in that report are explicitly regex-based. Current Tree-sitter adapters and subsequent reuse corrections are later implementation evidence, not proof that the captured work implemented full AST analysis for every language. Requested subagent roles, a failed todo update and an unknown `/agent` command are retained alongside the later completion reports.

Bob did not produce every part of the final application. Subsequent integration, broader QA, additional feature work, deployment and demo production also used Codex and manual review. Groq supplies the application's hosted inference; IBM Bob was used as a development collaborator. The [scope](SCOPE.md) and [verification record](VERIFICATION.md) preserve the distinction between recorded Bob work and later product checks.
