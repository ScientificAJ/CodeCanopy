# Submission checklist

Everything in this file is a claim the submission makes about itself. Each one
is either verified here, or owned by a named person. Nothing is left as an
assumption.

## Verified, reproduce it yourself

| Item | Where to check | Expected |
| --- | --- | --- |
| Bob session evidence | `bob_sessions/` | 10 numbered folders, index links all resolve |
| Bobcoin total | `bob_sessions/README.md` | 39.88 of 40, every figure from a panel |
| Backend suite | `cd backend && .venv/bin/python -m pytest -q` | 142 passed |
| Frontend suite | `cd frontend && npx vitest run` | 38 passed, 10 files |
| Type check | `cd frontend && npx tsc -b` | exit 0, no output |
| Verifier attacks | `cd backend && .venv/bin/python scripts/demo_verifier.py` | 1 honest graph verified, 4 forgeries unverified |
| Import cost | `cd backend && .venv/bin/python scripts/stress_test.py <repo>` | times scale roughly with file count |
| Keyless operation | unset `GROQ_API_KEY`, start the API | summaries, dependencies, proposals all 200; only Ask returns `AI_NOT_CONFIGURED` |

## Written and in the repository

- [x] **Problem and Solution statement**, `docs/submission-problem-solution.md`, 484 words
- [x] **IBM Bob Usage statement**, `docs/submission-bob-usage.md`, 489 words
- [x] **README**, leads with the verifier, shows the attack table, real captures, honest infrastructure section
- [x] **Bob IDE proof**, `docs/images/bob-ide-workspace.png`, referenced from the README
- [x] **Folder structure**, verified tree, all 52 paths checked against disk
- [x] **Cover image**, use `frontend/public/codecanopy-logo.png`; the submission form wants a single image, and the logo is the one asset built for that

## What the guide requires, confirmed

The only hard deliverable in the hackathon guide is the `bob_sessions` folder
with the task session consumption summary screenshots. The guide also states
that a solution must "showcase IBM Bob IDE as a core component" to be eligible
for judging. Both are covered.

The guide does not mention a demo video. If the submission form asks for one,
that is a lablab requirement rather than a guide requirement.

## Not in this repository

- [ ] **Demo video**, AJ. Not a guide requirement; a submission-form requirement.
- [ ] **`06-arjun-repository-setup` panel screenshot**, Arjun. The guide says each
      participant must upload their own task panels. The folder currently has
      transcripts but no panel image.
- [ ] **`08-sajidHameed-chatbot-work` panel screenshot**, Sajid. Same requirement;
      that folder has a transcript and no panel image.

## Known limits, stated rather than hidden

- Import cost: 133 files in 11.8s, 832 in 97s, 726 in 125s. Repositories in the
  thousands of files exceed a live demo's time budget. The archive caps are
  10,000 entries, 25 MiB per file, 250 MiB extracted.
- No Dockerfile, CI workflow or cloud config is checked in. The README explains
  why: snapshots expire in 24 hours, parsing runs under POSIX resource limits so
  exactly one API worker is correct, and workspace identity is a browser cookie.
- Optional AI: only the Ask module calls a hosted model. Every other feature
  runs with no credentials at all.
- `duplicate_detection` and `relationships` have backend packages but no
  dedicated panel; their findings are served through the findings route.

## Before the deadline

1. Confirm both statement files are pasted into the submission form. They exist
   in the repository but the form is separate.
2. Confirm every team member's Bob panels are present, including the two above.
3. Re-run the verification table at the top on the final commit.
4. If the form requires a live app URL, that does not exist yet. The service
   runs on loopback. See the deployment section of the README.
