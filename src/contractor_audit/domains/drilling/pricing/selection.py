"""The reading chosen for each switch, and where the choice came from.

A selection mixes approved readings (from artifacts/drilling/approved_readings.json), readings the
contract text resolves, and hypothetical readings supplied for sensitivity. Pricing fails before it starts
if any switch it needs has no reading; a result is canonical only if no reading used was hypothetical.
"""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from contractor_audit.domains.drilling.interpretation.switches import Switch

APPROVED_FILENAME = "approved_readings.json"

# Switches pricing reads. Phase-3 switches select which quantities exist; Phase-4 switches change how they are priced;
# calloff_evidence decides where a well class may come from. ds900_threshold_basis is invoice-level (not priced here);
# unranked_precedence is a meta-switch settled through the concrete switches it underlies.
PRICING_SWITCHES = (
    "appendix_g_reading", "appendix_g_duplicates", "dd102_basis", "hc630_basis", "dd121_condition", "dd120_hours",
    "metre_source", "lih_hours", "rig_up_hour", "pd210_class_factor", "standby_section_factor", "rig_services_index",
    "dd120_rate_from_feb_2026", "monthly_rate_basis", "principal_discount_combination", "volume_tier_scope",
    "contract_year_2", "lih_replacement_value", "calloff_evidence",
)


class Source(StrEnum):
    APPROVED = "APPROVED"                  # approved by the user
    CONTRACT_TEXT = "CONTRACT_TEXT"        # resolved by the contract's own words (no approval needed)
    HYPOTHETICAL = "HYPOTHETICAL"          # supplied for sensitivity; never canonical


class MissingSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class Choice:
    switch: str
    value: str
    source: Source


@dataclass(frozen=True)
class Selection:
    choices: dict[str, Choice]

    def value(self, switch: str) -> str:
        if switch not in self.choices:
            raise MissingSelectionError(f"no reading selected for switch {switch!r}")
        return self.choices[switch].value

    @property
    def canonical(self) -> bool:
        return all(c.source is not Source.HYPOTHETICAL for c in self.choices.values())

    def hypothetical(self) -> tuple[str, ...]:
        return tuple(sorted(n for n, c in self.choices.items() if c.source is Source.HYPOTHETICAL))

    def with_choice(self, switch: str, value: str, source: Source = Source.HYPOTHETICAL) -> "Selection":
        return Selection({**self.choices, switch: Choice(switch, value, source)})


def load_approved(path: Path, switches: dict[str, Switch]) -> dict[str, Choice]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for a in raw["approvals"]:
        s = switches[a["switch"]]
        if a["value"] not in s.values or s.reading(a["value"]).ambiguity_reading != a["ambiguity_reading"] or s.ambiguity_id != a["ambiguity"]:
            raise ValueError(f"approval {a} does not match switch {s.name}")
        out[s.name] = Choice(s.name, a["value"], Source.APPROVED)
    return out


def contract_text_choices(switches: dict[str, Switch]) -> dict[str, Choice]:
    """Switches the contract text resolves (no approval needed): fixed at their text reading."""
    return {n: Choice(n, s.default, Source.CONTRACT_TEXT) for n, s in switches.items() if not s.requires_approval and s.default}


def build_selection(switches: dict[str, Switch], approved: dict[str, Choice], hypothetical: dict[str, str] | None = None) -> Selection:
    """Approved and text-resolved readings, plus any hypothetical ones; hypothetical may not override an approval."""
    choices = {**contract_text_choices(switches), **approved}
    for name, value in (hypothetical or {}).items():
        if name in choices and choices[name].source is not Source.HYPOTHETICAL and choices[name].value != value:
            raise ValueError(f"{name} is fixed at {choices[name].value} ({choices[name].source}); a hypothetical reading may not replace it")
        if value not in switches[name].values:
            raise ValueError(f"{value!r} is not a reading of {name}")
        choices.setdefault(name, Choice(name, value, Source.HYPOTHETICAL))
    return Selection(choices)


def require(selection: Selection, switches: dict[str, Switch]) -> None:
    """Fail explicitly if any switch pricing reads has no selected reading."""
    missing = [n for n in PRICING_SWITCHES if n not in selection.choices]
    if missing:
        unresolved = [n for n in missing if switches[n].requires_approval]
        raise MissingSelectionError(f"pricing needs a reading for {missing} (unresolved, awaiting approval: {unresolved})")
    for n, c in selection.choices.items():
        if c.value not in switches[n].values:
            raise MissingSelectionError(f"{c.value!r} is not a reading of {n}")
