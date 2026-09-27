# Hosted GREPO

The hosted application serves the React/Vite frontend and FastAPI API from one origin. Anonymous browser workspaces are isolated by an HttpOnly session cookie. Private Vercel Blob storage persists imported snapshots across function instances; local temporary files are a cache, not the source of truth.

## Configuration

Create a Vercel project from the repository root and connect a **private** Blob store to Production and Preview. Configure these server environment variables:

- `BLOB_READ_WRITE_TOKEN`: supplied by the connected private store.
- `CODECANOPY_STORAGE=vercel_blob`: requires durable storage on hosted instances.
- `GROQ_API_KEY`: sensitive Production secret for optional AI features. Never prefix it with `VITE_`.
- `CRON_SECRET`: independent random sensitive secret for the authenticated cleanup endpoint.

Set the public build setting `VITE_HOSTED=true`. The build uses same-origin API requests, packages a Linux Node executable for the pinned Archify renderer, and includes its license. Python 3.12 runs the API. No imported source is executed.

Deploy from the repository root with the Vercel CLI. The production build must pass before promotion. Credentials and local environment files are excluded from both Git and deployment uploads.

## Retention and limits

Snapshot access expires after 24 hours. The weekly authenticated cleanup removes expired source bundles and view data; metadata tombstones remain briefly so expired links return an honest expiry response. Deleting an import revokes the workspace project pointer before removing its durable source.

The hosted upload path sends ZIP archives directly from the browser to private Blob storage using a short-lived, workspace-scoped upload token. Its archive allowance is **1 GiB (1,024 MiB)**. The long-lived storage token stays on the server. The importer reads bounded ZIP byte ranges rather than copying a whole large archive onto the function's limited scratch disk.

Archive upload size and analysis size are separate budgets. After dependency/build folders are excluded, the existing processing limits remain 250 MiB of extracted files, 50,000 accepted files, 200,000 archive entries, and 25 MiB per file. Syntax extraction is bounded to 1 MiB per source file; larger readable files remain browsable. Hosted imports must finish within the function duration budget. GitHub archive downloads retain their separate 250 MiB limit. The local CLI/server remains useful for workloads beyond hosted limits.

## Verification before sharing

Verify a GitHub import, a ZIP import through private storage, source reading, repository map rendering, deterministic findings, an AI answer with citations, proposal/document drafts, and deletion. Repeat snapshot access from a fresh process/instance to confirm durability. Verify unauthenticated API access cannot read another browser workspace. The deployment URL must be accessible without Vercel login before it is used in a submission.

## Hosted latency

Hosted workspace startup uses one authorized bootstrap response instead of six
independent ownership reads. Responses above 4 MiB explicitly fall back to the
existing resources; inventory and analysis coverage are not shortened. Optional
run diagnostics do not block opening the workspace. Feature loaders on the hosted
frontend repeat only when their actual request inputs change.

The hosted backend reuses storage and AI HTTP connections; mutable ownership
records still come from the origin on every request, so deletion remains effective
across warm instances. Recent project records are fetched with bounded concurrency.
A first standalone greeting can answer without source retrieval or an AI call;
repository questions, follow-ups, proposals and documentation retain the same
model and evidence budgets.

Production `Server-Timing` headers report application processing time, plus chat
retrieval and provider time when applicable. They contain durations, not source,
prompts or credentials. Compare these with total browser time to distinguish
provider work from transfer or platform startup delays. First requests and provider
response times can vary; a warm benchmark is not a cold-start guarantee.
