"""V1 integration-slot response models.

These models define the machine-readable "not connected" responses
returned by all integration slot endpoints.  They allow frontend
components to distinguish:
  - NOT_CONNECTED  : the feature module has not been wired in yet
  - NOT_IMPLEMENTED: the endpoint exists but the feature is deferred
  - UNAVAILABLE    : the service is temporarily down

Frontend code MUST NOT treat these as empty-success responses.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SlotStatus(str):
    NOT_CONNECTED = "NOT_CONNECTED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    UNAVAILABLE = "UNAVAILABLE"


class IntegrationSlotResponse(BaseModel):
    """Returned by any deferred-feature endpoint.

    Clients render an explicit placeholder; they must never treat this
    as a successful analysis result.
    """

    schema_version: Literal["1.0"] = "1.0"
    slot: str          # e.g. "summaries.context-panel"
    status: str        # one of SlotStatus constants
    title: str
    description: str
    integration_path: str | None = None  # import path of the slot module
    docs_url: str | None = None


# ---------------------------------------------------------------------------
# Pre-built slot definitions for each deferred feature
# ---------------------------------------------------------------------------

SLOT_SUMMARIES = IntegrationSlotResponse(
    slot="summaries.context-panel",
    status=SlotStatus.NOT_CONNECTED,
    title="AI File & Folder Summaries",
    description=(
        "Integration slot: put the summaries feature here.  "
        "Not connected yet.  The repository map and source browser work independently."
    ),
    integration_path="app.features.summaries",
)

SLOT_DEPENDENCIES = IntegrationSlotResponse(
    slot="dependencies.workspace",
    status=SlotStatus.NOT_CONNECTED,
    title="Connections & Change Impact",
    description=(
        "Integration slot: put the dependencies feature here.  "
        "Not connected yet.  Structural containment browsing works independently."
    ),
    integration_path="app.features.relationships",
)

SLOT_REUSE = IntegrationSlotResponse(
    slot="reuse.findings",
    status=SlotStatus.NOT_CONNECTED,
    title="Reusable & Shared Functions",
    description=(
        "Integration slot: put the reuse-discovery feature here.  "
        "Not connected yet."
    ),
    integration_path="app.features.reusable_functions",
)

SLOT_DUPLICATES = IntegrationSlotResponse(
    slot="duplicates.compare",
    status=SlotStatus.NOT_CONNECTED,
    title="Duplicate Code Review",
    description=(
        "Integration slot: put the duplicate-detection feature here.  "
        "Not connected yet."
    ),
    integration_path="app.features.duplicate_detection",
)

SLOT_UNUSED = IntegrationSlotResponse(
    slot="unused.review",
    status=SlotStatus.NOT_CONNECTED,
    title="Unused Code Candidates",
    description=(
        "Integration slot: put the unused-code review feature here.  "
        "Not connected yet."
    ),
    integration_path="app.features.duplicate_detection",
)

SLOT_ASK = IntegrationSlotResponse(
    slot="ask.workspace",
    status=SlotStatus.NOT_CONNECTED,
    title="Ask CodeCanopy",
    description=(
        "Integration slot: put the Ask CodeCanopy conversational feature here.  "
        "Not connected yet.  No Watson credentials are required to browse the map."
    ),
    integration_path="app.features.codebase_chat",
)

SLOT_PROPOSALS = IntegrationSlotResponse(
    slot="proposals.detail",
    status=SlotStatus.NOT_CONNECTED,
    title="Proposals & Change Packs",
    description=(
        "Integration slot: put the proposals feature here.  "
        "Not connected yet."
    ),
    integration_path="app.features.onboarding",
)
