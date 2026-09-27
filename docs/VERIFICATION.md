# Verification record

## 2026-09-27, shared UI completion

Implemented real ZIP upload, optional GitHub revision input, recent imports,
retention/exclusion disclosures, a factual overview, adaptive map density,
editable group names/colors/members, and map navigation/camera restoration.
Existing source evidence ranges remain intact across navigation.

| Check | Result |
| --- | --- |
| Full backend suite | 98 passed; existing Starlette/httpx deprecation warning |
| Final workspace/render boundary rerun | 33 passed after the final camera bridge fix |
| Frontend unit tests | 20 passed |
| Production build and shared contracts | Passed |
| ESLint | No errors; one pre-existing unused-disable warning in Ask/ChatModal.tsx |
| Full browser suite with live GitHub | 4 passed; public ScientificAJ/CodeCanopy import resolved an immutable revision |
| Final synthetic browser rerun | 3 passed after camera/source-history changes and mobile assertions |
| Archify deterministic rendering | 9/9 showcase, zero errors/warnings for every supported 0–8 child layout |
| Expanded HTML automated visual check | Passed for upstream delivery and actual downloaded CodeCanopy export |

The browser tests now upload ZIPs through the visible UI. They cover GitHub
ref submission/default omission, failure recovery, actual cancellation-button
requests, invalid ZIP selection, recent imports, separate overview, folder/page
Back navigation, edge-pan and zoom restoration, density changes, persisted group
rename/color/member removal, source evidence navigation, findings/dependencies,
keyboard/mobile source access and offline export. The explicit-ref/error/cancel
cases use deterministic API fixtures; the public GitHub import uses the live
service. Automatic density switches to three children at 390×844 with no
horizontal page overflow; desktop supports eight children plus the focus node.

Perceptual review inspected desktop import, overview, expanded map and blue
edited group, plus 390×844 import/map layouts. The exact final expanded export
was inspected in light theme at 1440×900 and dark theme at 2048×1320: cards,
connectors, title, provenance and navigation controls remain separated and
readable. Automated checks cover containment at 1440×900, 1600×1000, 1920×1080
and 2048×1320, with both endpoint themes captured. The diagnosed initial expanded
layout overflow was corrected by compacting authored vertical spacing, without
changing the vendor, hiding overflow or shrinking typography.

Final expanded-export receipt (original output path recorded at the time):

```text
diagram_type: architecture
output: bob_sessions/browser-evidence/expanded-export.html
specification_sha256: 53f6a13ab4e0ef797d214e63a7a348738e1c40c64ed8798562d28cd69abc4172
artifact_sha256: e763070df0dcc1edae9128adb0f96bf8a1a462b9212c351705903a48e1678d6d
upstream_artifact_sha256: 2ed980203902dbc603d21f4db7c9311ddd4a3f2a18c44cb76227c7154417aef5
validation: 9/9 showcase, 0 errors, 0 warnings
browser_evidence: passed
visual_review: passed
correction_rounds: 1
```

These are local implementation/browser checks, not a hosted deployment claim.
The original foundation evidence below remains a historical record.

## 2026-09-26, foundation

Recorded 2026-09-26. Scope: the structure workspace and shared integration
surfaces described in [SCOPE.md](SCOPE.md).

| Check | Result |
| --- | --- |
| Backend `pytest -q` | 41 passed; one upstream Starlette/httpx deprecation warning |
| Frontend `npm run lint` | Passed |
| Frontend `npm run build` | Passed |
| Frontend `npm test` | 7 passed |
| Playwright E2E (`CODECANOPY_LIVE_GITHUB=1 npm run test:e2e`) | 2 passed (live public GitHub import and synthetic ZIP workspace) |
| Targeted Playwright workspace/export rerun (`npx playwright test e2e/workspace.spec.ts`) | 1 passed after the final wrapper repair; includes visible provenance and explicit dark-theme query checks with empty local storage |
| Live public GitHub import | Passed against ScientificAJ/CodeCanopy, resolved to public `main` commit `e7081fbfe02cfedc7a3e13e38f453a53d94aead0` |
| Pinned Archify package | 219 files match the downloaded pinned archive; hashes in `vendor/archify.lock.json` |
| Archify deterministic delivery | 9/9 showcase checks, zero errors and warnings for each supported chapter size |
| Upstream HTML automated browser check | Passed after compacting authored vertical spacing |
| CodeCanopy wrapped HTML automated browser check | Passed for the root view and downloaded grouped export; four desktop containment measurements and light/dark endpoint captures for each |

The ZIP browser test exercises actual import endpoints, map/tree selection,
bounded source paging and line jumps, inert unknown-language text, persisted
labels/groups, unconnected feature routes without feature requests, mobile
source access, keyboard navigation and offline HTML interaction. The offline
export test checks visible provenance in the header, explicit `?theme=dark`
behavior with an empty saved-theme value, and no HTTP requests or application
page errors. The combined live GitHub/ZIP run completed before the final
renderer-wrapper-only change; the ZIP workspace/export test was rerun after it.

E2E screenshots cover 1672×941, 1440×900, 1920×1080, 1600×1000 and 2048×1320,
plus mobile 390×844. Archify visual-check measured light-theme containment at
1440×900, 1600×1000, 1920×1080 and 2048×1320, and captured both light and dark
themes at 1440×900 and 2048×1320 for each final artifact. Every measurement had
no page overflow or viewer-stage/dock collision, stable viewer chrome, and a
minimum projected node label size of 9 px.

The checked root HTML binds SHA-256
`eaa5b329573bbbd292dafea8484304971c23b8ea87273851ba2a7615fac8c085` (806,669
bytes); its upstream delivered HTML binds SHA-256
`720b568fe0eab15d175f4d3f79d37ed25865cfbb4a5aa4628ed45f5c3989188b` (797,472
bytes). The downloaded grouped export binds SHA-256
`61c08e82bbd517abb770ded967d4dc08fce16bb098f28568a44e253841ed8540` (802,149
bytes). Automated browser checks passed for both. Perceptual review passed on
the exact root and grouped artifacts in both themes at 1440×900 and 2048×1320;
the provenance remains readable under the title without covering controls or
the map. The initial body-level disclosure caused Archify's viewer-chrome
measurement to keep changing; placing it in the existing header fixed the
loop. Explicit valid `?theme=light|dark` values now take precedence over the
saved view theme, with an E2E assertion for the empty-storage dark case.

Archived evidence receipts and screenshots are tracked under
[`bob_sessions/07-arjun-structure-workspace/supporting-evidence/browser-evidence`](../bob_sessions/07-arjun-structure-workspace/supporting-evidence/browser-evidence).
The archived browser receipts are
`upstream-root.visual-check.json`, `codecanopy-root.visual-check.json`, and
`structural-export.visual-check.json`; the root delivery receipt and exact
source files are `delivery.json`, `upstream-root.html`, `codecanopy-root.html`,
`view.architecture.json`, and `root-render-result.json`.

The foundation commit did not include raw conversation logs, imported repositories
or the bulk design archive. Recovered BOB session records were added separately
in commit `2046087` and are now linked from the [session index](../bob_sessions/README.md).

To repeat the optional live network check:

```bash
cd frontend
CODECANOPY_LIVE_GITHUB=1 npm run test:e2e
```

The ordinary browser command skips that external-network test and runs the
synthetic ZIP workflow. Both commands start the development servers when needed.
