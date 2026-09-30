"""Deterministic confidence policy: evidence quality, graded by the readings a conclusion depends on.

A reading's grade comes from its status in the interpretation registry (Phase 2 SWITCHES and the
audit's AUDIT_SWITCHES), never from how well it fits the billing:

* TEXT_RESOLVED            -> HIGH   (the contract settles it; the alternative is kept for sensitivity only)
* EVIDENCE_NOT_PROVIDED    -> MEDIUM
* UNRESOLVED               -> MEDIUM, or LOW for the readings where the text gives near-equal support
                                      to both sides (LEAST_CERTAIN)

A dependency is recorded only when flipping the reading actually changes the finding or total,
which the dependency analysis measures by re-running the audit.
"""

from contractor_audit.domains.civil_works.audit.options import AUDIT_SWITCHES_BY_FIELD
from contractor_audit.domains.civil_works.interpretation import SWITCHES_BY_FIELD, SwitchStatus
from contractor_audit.shared.findings import ConfidenceBand

# 32 'following' vs P19 'within two days of'; 31A 'on or after' vs A3 recital 'after'.
LEAST_CERTAIN = frozenset({"exclusion_window", "retro_adjustment_trigger"})


def switch_info(field: str):
    return SWITCHES_BY_FIELD.get(field) or AUDIT_SWITCHES_BY_FIELD[field]


def grade(field: str) -> ConfidenceBand:
    status = switch_info(field).status
    if status is SwitchStatus.TEXT_RESOLVED:
        return ConfidenceBand.HIGH
    if status is SwitchStatus.UNRESOLVED and field in LEAST_CERTAIN:
        return ConfidenceBand.LOW
    return ConfidenceBand.MEDIUM
