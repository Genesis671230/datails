"""Jurisdiction wording overlays (05 §1.5).

Jurisdiction affects report WORDING, mostly small deltas (EU→UK ≈ two
sentences on the front page). Model: base template + variant overlays, not
separate templates. Applied at draft time as extra prompt instructions.
"""

JURISDICTIONS = ("EU", "UK", "US", "AT", "DE", "CH", "AE")

_OVERLAYS = {
    "EU": "Frame regulatory references within MiCA, the Travel Rule, DAC8, and CARF.",
    "UK": "Frame regulatory references for the UK regime (FCA registration, POCA).",
    "US": "Frame regulatory references for the US regime (OFAC exposure, subpoena route).",
    "AT": "Frame for Austrian procedure; reference the parallel official police filing.",
    "DE": "Frame for German procedure (Onlinewache filing reference, Akteneinsicht).",
    "CH": "Frame for Swiss procedure (MROS reporting where applicable).",
    "AE": "Frame for UAE procedure (goAML reporting where applicable).",
}


def jurisdiction_overlay(jurisdiction: str | None) -> str | None:
    if jurisdiction is None:
        return None
    overlay = _OVERLAYS.get(jurisdiction)
    if overlay is None:
        raise ValueError(
            f"unknown jurisdiction {jurisdiction!r}; known: {sorted(_OVERLAYS)}"
        )
    return overlay
