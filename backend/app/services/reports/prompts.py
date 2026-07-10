"""Report-type drafting instructions (05 §1.4, §3 Report Writer rules).

Domain content validated with operators — reality notes preserved verbatim
in intent: exchanges act on law-enforcement requests; a private
investigator's letter is a notification preparing the LE handoff, not an
order (LD-17). SAR/STR drafts mirror the department-head approval reality.
"""

from app.db.models.enums import ReportType

_INSTRUCTIONS: dict[ReportType, str] = {
    ReportType.POLICE_INTAKE: (
        "Structure as an official police intake report: the five W's (who lost "
        "what/how much, to whom, which wallet), the fiat→crypto mixing point, "
        "evidence inventory with source references, and the on-chain summary. "
        "Court-facing register; every claim cites a source reference."
    ),
    ReportType.EXCHANGE_COMPLIANCE_REQUEST: (
        "Structure as a compliance information request to an exchange: case "
        "reference, affected addresses with label provenance, the specific "
        "transaction hashes, and the concrete information requested. Note that "
        "exchanges act on law-enforcement requests — this letter prepares the "
        "LE handoff; word it as a notification, not an order."
    ),
    ReportType.FREEZE_BLOCKLIST_REQUEST: (
        "Structure as a per-platform freeze/blocklist request: platform name, "
        "affected deposit addresses, the exact transaction hashes, amounts and "
        "assets, and the case reference. This is a legal-weight communication "
        "and remains a DRAFT until human approval. Word it as a notification "
        "that prepares the law-enforcement handoff, never as an order."
    ),
    ReportType.INVESTIGATOR_SUMMARY: (
        "Structure as an internal investigator summary: current state, key "
        "findings with confidence, open questions, recommended next steps per "
        "the methodology cues."
    ),
    ReportType.CASE_DOSSIER: (
        "Structure as a structured case dossier: chronology, parties, wallets "
        "with label provenance, evidence inventory, findings, decisions taken. "
        "Every claim cites a source reference."
    ),
    ReportType.SAR_DRAFT: (
        "Structure as a SAR/STR draft for an FIU: reporting entity context, "
        "suspicious activity narrative grounded in cited sources, involved "
        "addresses and transactions. This draft requires department-head "
        "approval inside the customer's institution — mark it clearly as a "
        "draft prepared for that approval."
    ),
}


def drafting_instructions(report_type: ReportType) -> str:
    return _INSTRUCTIONS[report_type]
