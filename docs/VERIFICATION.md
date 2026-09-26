# Verification record

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

Evidence receipts and screenshots remain ignored under
`bob_sessions/browser-evidence`. The current browser receipts are
`upstream-root.visual-check.json`, `codecanopy-root.visual-check.json`, and
`structural-export.visual-check.json`; the root delivery receipt and exact
source files are `delivery.json`, `upstream-root.html`, `codecanopy-root.html`,
`view.architecture.json`, and `root-render-result.json`.

No raw conversation logs, imported repositories or bulk design archive are
included in the commit.

To repeat the optional live network check:

```bash
cd frontend
CODECANOPY_LIVE_GITHUB=1 npm run test:e2e
```

The ordinary browser command skips that external-network test and runs the
synthetic ZIP workflow. Both commands start the development servers when needed.
