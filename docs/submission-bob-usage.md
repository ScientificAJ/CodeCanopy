# GREPO — IBM Bob Usage Statement

**Ten Bob sessions, 39.88 of 40 Bobcoins, and three agents that corrected the
briefs they were given.**

All work was done in the Bob IDE against the `CodeCanopy` workspace. The
per-task transcripts and the task session consumption summary panels for every
task are in [`bob_sessions/`](../bob_sessions/), one numbered folder each, with
the task ID, Bobcoin cost and context usage recorded in its `session-summary.md`.

| Task ID | Work | Bobcoins |
| --- | --- | --- |
| `681a0938`, `64a0bdec`, `8fd491fa` | Cited-summary prompt validation, then the summaries engine | 17.95 |
| `c33b7b17` | Dependency graph, unresolved-reference handling, change impact | 8.10 |
| `43a21cfe` | Change-impact correction for folder and repository-root subjects | 2.02 |
| `40a1564f` | Dependency target-existence guard | 1.51 |
| `a81ad5b9` | Ask response rendering fix | 5.50 |
| `84f1cdb8` | Ask slot greeting and frontend wiring | 4.80 |
| | **Total** | **39.88** |

**How the sessions were run.** Each brief was scoped to a defect found by
testing rather than to a feature idea, and each carried an explicit budget with
an instruction to report the actual panel cost rather than an estimate. Context
usage ranged from 13% to 41% of the 270k budget, so the briefs fit rather than
ran to the ceiling. The smallest session, the target guard, cost 1.51 Bobcoins
and added two guards plus tests.

**Three times, Bob reported that the brief was wrong.** Each is recorded in
its session summary, and each is the more useful outcome:

- The impact brief asserted the bug lived in root and folder subjects. Bob
  verified the folder case was also wrong rather than making the root case look
  fixed, on the grounds that both problems should be visible in the output.
- The rendering brief assumed a streaming bug. There is no streaming. Bob traced
  the renderer's control flow, reported that the label renders exactly once, and
  fixed the real cause — a preview that sliced a markdown table in half.
- The Ask wiring brief asked for a budget confirmation Bob could not see. Bob
  said so instead of inventing a figure.

**The most consequential session was the cheapest.** The first dependency
implementation validated the citation on every edge but never checked that the
target file existed, so a fabricated target with a perfect citation passed. That
gap was found by attacking the finished code, not by writing a test for it, and
closed in a 1.51-Bobcoin session. A second attack found the same class of hole
on a null target endpoint.

**What Bob did not do.** Bob did not fabricate costs, did not claim a fix for a
bug that did not exist, and did not weaken a test to make a suite pass. Where a
brief's premise was wrong it said so in the summary, which is why those three
sessions are the ones worth reading.
