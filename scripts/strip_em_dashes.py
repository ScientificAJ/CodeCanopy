"""One-off: replace em dashes with plain punctuation in project prose.

Only files we authored. Bob transcripts and vendored docs are left alone:
they are evidence and third-party source respectively.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

TARGETS = [
    "README.md",
    "docs/submission-bob-usage.md",
    "docs/submission-checklist.md",
    "docs/submission-problem-solution.md",
    "docs/VERIFICATION.md",
]

# Explicit rewrites where a comma alone reads wrong.
EXACT = {
    "README.md": [
        ("| **Architecture map** \u2014 observed", "| **Architecture map**, observed"),
        ("| **Verified dependencies** \u2014 88", "| **Verified dependencies**, 88"),
        ("exist \u2014 the check described below", "exist: the check described below"),
        ("10s \u2014 259 edges", "10s, 259 edges"),
        ("1.7s \u2014 88 edges", "1.7s, 88 edges"),
        ("twice \u2014 by two people, for two different designs \u2014 without",
         "twice, by two people, for two different designs, without"),
        ("reason \u2014 an external package", "reason: an external package"),
        ("**Run one API worker** \u2014 a second", "**Run one API worker**, because a second"),
        ("is real work \u2014 sticky sessions, shared\nsnapshot storage, a job queue \u2014 and none of it is pretending to be done.",
         "is real work: sticky sessions, shared\nsnapshot storage, a job queue. None of it is pretending to be done."),
    ],
}

total = 0
for rel in TARGETS:
    p = ROOT / rel
    text = p.read_text(encoding="utf-8")
    before = text.count("\u2014")
    if before == 0:
        print(f"{rel}: already clean")
        continue
    for a, b in EXACT.get(rel, []):
        if a not in text:
            print(f"  WARN pattern absent in {rel}: {a[:55]}")
        text = text.replace(a, b)
    # Anything still left: a bare spaced dash. Drop it to a comma.
    if "\u2014" in text:
        text = re.sub(r" ?\u2014 ?", ", ", text)
        text = re.sub(r",\s*,", ",", text)
    p.write_text(text, encoding="utf-8")
    left = text.count("\u2014")
    total += before
    print(f"{rel}: {before} -> {left}")
    if left:
        sys.exit(f"FAILED: em dashes remain in {rel}")

print(f"\ntotal removed: {total}")
