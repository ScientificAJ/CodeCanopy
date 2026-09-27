# GREPO, Problem and Solution Statement

**The problem: repository analysis tools make claims you cannot check.**

Asking an AI tool to summarise a repository produces confident, plausible prose.
Whether a function "validates the payload" or a module "handles retries" is not
something a reader can confirm in one click, and when it is wrong there is no
signal at all. A developer who cannot trust a summary does not act on it; they
open the file. The tool saves no time at the exact moment it is supposed to
save the most.

The failure is worst on dependencies. A resolver that cannot prove an import
target exists will invent one to make a graph look connected, or it will quietly
drop every edge it could not prove and present an empty graph as complete. The
previous edition's second-place project shipped a resolver that could fabricate
targets, and every map in its judged build drew zero dependency arcs. A
dependency view that looked finished and contained nothing.

**The solution: verify every claim before it is shown, and prove the verifier.**

GREPO imports a public GitHub repository or a ZIP into an immutable, read-only
snapshot, then computes every claim from an AST walk rather than from a model.
Each claim cites the exact source range it came from. Before any of it reaches
the interface, a verifier independently re-reads that range through the
snapshot service, which re-checks the content hash, enforces bounds, and
confirms the cited line supports the claim. Claims that fail are removed rather
than shown faintly.

The same rule governs the dependency graph. An import that does not resolve
stays unresolved and is listed with its reason, a bare package specifier and a
missing file are different problems and are reported differently. Change impact
with no meaningful answer returns an empty list and says why, instead of a
confident zero. Nothing is invented to make a view look complete.

The verifier is delivered with the attacks that broke it. Six forgeries were
constructed by hand and run against the real verifier: a citation on a real
line that does not import the target, a citation past end of file, a file ID
belonging to another snapshot, a null target, and, found by attacking finished
code rather than by writing tests for it, an edge whose citation was entirely
valid but whose target file did not exist. All six are rejected, each with its
own reason. `backend/scripts/demo_verifier.py` reproduces the table.

The result is a tool whose central promise is falsifiable, and a reader can
test it in under two minutes. On this repository's own source, GREPO reports
832 files and 269 verified dependency edges, and every edge it cannot prove
stays unresolved with the reason attached. On `pallets/click` it reports 191
verified edges while 517 imports stay unresolved and labelled, which is the
honest ratio for a library whose dependencies live outside its own tree.
