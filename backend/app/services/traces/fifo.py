"""FIFO attribution engine — deterministic, engine-side arithmetic (05 §8).

Attribution is NOT model work: the engine selects the next candidate hop
from connector transfer data under first-in-first-out ordering; the
investigator confirms or rejects every hop (human-led tracing, spec
guardrail). Alternative methods (LIFO, pro-rata) are configuration, not
rebuild — this module is the only place selection order lives.

Confidence is a deterministic pilot heuristic, surfaced per hop:
- one candidate outgoing transfer → 0.95 (temporal FIFO order, no ambiguity)
- multiple candidates → 0.75 (FIFO picks the earliest, ambiguity flagged)
Documented here so the reader knows it is a heuristic, not vendor data.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.integrations.generic_api.base import NormalizedTransfer

CONFIDENCE_SINGLE_CANDIDATE = Decimal("0.95")
CONFIDENCE_AMBIGUOUS = Decimal("0.75")


@dataclass(frozen=True)
class HopCandidate:
    tx_hash: str
    to_address: str
    asset: str
    amount: Decimal
    confidence: Decimal
    timestamp: str | None


def select_next_hop(
    transfers: list[NormalizedTransfer],
    *,
    tracked_amount: Decimal,
    excluded_tx_hashes: frozenset[str],
) -> HopCandidate | None:
    """Pick the next hop out of the current wallet under FIFO.

    Candidates are outgoing transfers not already used or rejected, ordered
    by timestamp (earliest first — first in, first out). Returns None when
    the wallet has no remaining outgoing candidates.
    """
    candidates = sorted(
        (
            transfer
            for transfer in transfers
            if transfer.direction == "out" and transfer.tx_hash not in excluded_tx_hashes
        ),
        key=lambda transfer: (transfer.timestamp or "", transfer.tx_hash),
    )
    if not candidates:
        return None

    chosen = candidates[0]
    confidence = (
        CONFIDENCE_SINGLE_CANDIDATE if len(candidates) == 1 else CONFIDENCE_AMBIGUOUS
    )
    return HopCandidate(
        tx_hash=chosen.tx_hash,
        to_address=chosen.counterparty_address,
        asset=chosen.asset,
        amount=min(tracked_amount, Decimal(chosen.amount)),
        confidence=confidence,
        timestamp=chosen.timestamp,
    )
