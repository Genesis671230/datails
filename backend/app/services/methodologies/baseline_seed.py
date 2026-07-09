"""Baseline investigation methodology seed (05_DOMAIN_MODEL.md §2).

Derived from AQ Forensics practice — the pilot must feel like "it already
knows how I work," not an empty engine. Step content is used VERBATIM from
the domain model; do not "improve" it from general knowledge (master prompt,
Domain fidelity).

Seeded for every new tenant at workspace bootstrap.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Methodology, MethodologyStep

BASELINE_METHODOLOGY_NAME = "Baseline crypto investigation methodology (AQ practice)"
BASELINE_SPECIALTY = "criminal_investigation"

# Maps 1:1 onto methodology_steps (05 §2). Albert's compression of the same
# pipeline: "input/aggregation, analysis/making it readable,
# report/communication" [02-16].
BASELINE_STEPS: tuple[dict, ...] = (
    {
        "step_order": 1,
        "step_name": "Victim intake (five W's)",
        "description": (
            "Who lost what/how much to whom/which wallet; reconstruct on-ramp; "
            "identify fiat→crypto mixing point"
        ),
        "tool_preference": "intake form / conversation",
        "output_type": "structured intake record",
        "requires_human_approval": False,
    },
    {
        "step_order": 2,
        "step_name": "Evidence collection",
        "description": (
            "Transaction-history export from on-ramp exchange; screenshots; communications"
        ),
        "tool_preference": "file upload",
        "output_type": "evidence_items",
        "requires_human_approval": False,
    },
    {
        "step_order": 3,
        "step_name": "Parallel police filing",
        "description": (
            "Guide victim to official filing (Onlinewache model); record file reference"
        ),
        "tool_preference": None,
        "output_type": "police_file_reference",
        "requires_human_approval": False,
    },
    {
        "step_order": 4,
        "step_name": "Preliminary wallet check",
        "description": "Validate addresses; quick lookup on submitted wallets",
        "tool_preference": "connector",
        "output_type": "preliminary trace summary",
        "requires_human_approval": False,
    },
    {
        "step_order": 5,
        "step_name": "On-chain tracing",
        "description": (
            "Investigator-led exploration: labels, change outputs, hot-wallet "
            "boundaries, chain hops"
        ),
        "tool_preference": "Crystal connector",
        "output_type": "findings",
        "requires_human_approval": True,  # findings approval
    },
    {
        "step_order": 6,
        "step_name": "Freeze / blocklist communication",
        "description": "Per-platform letters with hashes to CEX/DeFi",
        "tool_preference": "report generator",
        "output_type": "freeze_blocklist_request",
        "requires_human_approval": True,
    },
    {
        "step_order": 7,
        "step_name": "Regulatory reporting",
        "description": "SAR/STR draft to FIU; jurisdiction wording",
        "tool_preference": "report generator",
        "output_type": "sar_draft",
        "requires_human_approval": True,
    },
    {
        "step_order": 8,
        "step_name": "Court-ready report",
        "description": "Source-hyperlinked, jurisdiction-specific final report",
        "tool_preference": "report generator",
        "output_type": "police_intake / case_dossier",
        "requires_human_approval": True,
    },
)

# Initial jurisdiction vocabulary (05 §1.5).
BASELINE_JURISDICTIONS = ["EU", "UK", "US", "AT", "DE", "CH", "AE"]


async def seed_baseline_methodology(
    session: AsyncSession, tenant_id: UUID, workspace_id: UUID
) -> Methodology:
    """Create the baseline methodology plus its eight steps for a new tenant.

    Flushes but does not commit — the caller owns the transaction (bootstrap
    creates tenant, workspace, and seed atomically).
    """
    methodology = Methodology(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        name=BASELINE_METHODOLOGY_NAME,
        specialty=BASELINE_SPECIALTY,
        jurisdictions_json={"jurisdictions": BASELINE_JURISDICTIONS},
    )
    session.add(methodology)
    await session.flush()

    for step in BASELINE_STEPS:
        session.add(MethodologyStep(methodology_id=methodology.id, **step))
    await session.flush()
    return methodology
