# Verification record

Recorded 2026-09-26. Scope: the structure workspace and shared integration
surfaces described in [SCOPE.md](SCOPE.md).

| Check | Result |
| --- | --- |
| Backend `pytest -q` | 41 passed; one upstream Starlette/httpx deprecation warning |
| Frontend `npm run lint` | Passed |
| Frontend `npm run build` | Passed |
| Frontend `npm test` | 7 passed |
| ZIP browser workflow | Passed after the layout repair |
| Live public GitHub browser workflow | Passed against ScientificAJ/CodeCanopy, resolved to `a21b7e35abf8978032a280fdc950764d74781cfc` before this implementation was pushed |
| Pinned Archify package | 219 files match the downloaded pinned archive; hashes in `vendor/archify.lock.json` |
| Archify deterministic delivery | 9/9 showcase checks, zero errors and warnings for each supported chapter size |
| Upstream HTML automated browser check | Passed after compacting authored vertical spacing |
| Wrapped export additional automated browser check | Incomplete: Chrome inspection failed; no final pass claimed |

The ZIP browser test exercises actual import endpoints, map/tree selection,
bounded source paging and line jumps, inert unknown-language text, persisted
labels/groups, unconnected feature routes without feature requests, mobile
source access, keyboard navigation and offline HTML interaction. The offline
export test observed no HTTP requests or application page errors.

Screenshots were collected at 1672×941, 1440×900, 1920×1080, 1600×1000 and
2048×1320, plus mobile 390×844. Image review identified and corrected spacing
for the longer wordmark and excess standalone diagram height. A final
perceptual review of the repaired standalone export was not completed before
the user requested an immediate commit. Automated browser evidence and image
review are separate from deterministic renderer validation.

Local receipts, screenshots and synthetic inputs remain ignored under
`bob_sessions/browser-evidence`. The final upstream browser receipt binds
SHA-256 `c781fc815ea3d17eb22d0472119a5178c10a4fad85442d1eefd508bc725a5e7a`.
No raw conversation logs, imported repositories or bulk design archive are
included in the commit.

To repeat the optional live network check:

```bash
cd frontend
CODECANOPY_LIVE_GITHUB=1 npm run test:e2e
```

The ordinary browser command skips that external-network test and runs the
synthetic ZIP workflow. Both commands start the development servers when needed.
