"""Directional drilling services contract DDS-2025-118 (invoices MDS-xxxxx).

Layers, in dependency order (enforced by tests/drilling/test_layout.py):

    ingestion  raw files -> typed rows and parsed Daily Drilling Reports, verbatim   (shared only)
    contract   reviewed contract extraction -> typed terms, readings, pricing         (shared only)
    audit      joins what was billed and recorded with what the contract allows       (+ ingestion, contract)
    reporting  artifacts and draft outputs                                            (+ audit, ingestion, contract)

`sources.py` names the raw files; `pipeline.py` is the only module that wires the layers together.
"""

from contractor_audit.domains.drilling.pipeline import DOMAIN

__all__ = ["DOMAIN"]
