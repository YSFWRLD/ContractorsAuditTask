"""Deterministic quantity extraction from site-record descriptions.

Each rule is an anchored regular expression for one phrasing observed in the records
(record_inventory.md lists them). A description that no rule matches exactly is returned
as unresolved: nothing is guessed. `indicated_items` records which Schedule 1 items the
phrase describes in the site's own words; it is a reading of the phrase, not a match to a line.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from contractor_audit.domains.civil_works.records import SiteRecord

_N = r"(?P<qty>\d+(?:\.\d+)?)"


@dataclass(frozen=True)
class QuantityRule:
    rule_id: str
    record_type: str
    pattern: re.Pattern
    unit: str                              # Schedule 1 unit the quantity is expressed in
    indicated_items: tuple[str, ...]
    note: str = ""


def _rule(rule_id, record_type, regex, unit, items, note=""):
    return QuantityRule(rule_id, record_type, re.compile(rf"^{regex}$"), unit, tuple(items), note)


RULES: tuple[QuantityRule, ...] = (
    _rule("CT.subbase_square_metres", "CT", rf"{_N} square metres of sub-base in and compacted", "m2", ["D.41.010"]),
    _rule("CT.laid_rolled_type1", "CT", rf"laid and rolled {_N} m2 of Type 1", "m2", ["D.41.010"], "Type 1 is the Series D sub-base material"),
    _rule("CT.capping_layer", "CT", rf"capping layer, {_N} m2 placed and compacted", "m2", ["D.41.040"]),
    _rule("CT.whacked_imported_stone", "CT", rf"placed and whacked {_N} m3 of imported stone", "m3", ["A.14.010"]),
    _rule("CT.brought_in_fill", "CT", rf"brought in {_N} cube of fill, compacted in layers", "m3", ["A.14.010"], "'cube' = cubic metres"),
    _rule("CV.surveyed_run", "CV", rf"surveyed {_N} m of the finished run with the camera", "lm", ["C.35.010"]),
    _rule("DW.pumps_kept_going", "DW", rf"pumps kept going {_N} week this period", "week", ["A.16.010"]),
    _rule("DW.wellpoints_running", "DW", rf"wellpoints running, {_N} week on the dewatering", "week", ["A.16.010"]),
    _rule("DX.trench_dig_depth", "DX", rf"trench dig {_N} cube, (?P<depth>\d+(?:\.\d+)?) m deep section", "m3", [],
          "depth stated; item follows P13 depth bands (see depth_item)"),
    _rule("DX.over_four_metres", "DX", rf"trench over four metres, {_N} m3 dug", "m3", ["A.12.040"]),
    _rule("DX.between_two_and_four", "DX", rf"deep trench {_N} m3, between two and four metres", "m3", ["A.12.030"]),
    _rule("JS.chainage_band", "JS", rf"set out and agreed {_N} chainage band with the Engineer", "no.", ["E.52.010"]),
    _rule("JS.fixers_placed_bar", "JS", rf"steel fixers placed {_N} t of high yield bar", "tonne", ["B.23.010"]),
    _rule("JS.mesh_with_laps", "JS", rf"laid {_N} m2 of A393 mesh with laps", "m2", ["B.23.020"]),
    _rule("JS.fixed_bar", "JS", rf"fixed {_N} tonne of bar, cut and bent to schedule", "tonne", ["B.23.010"]),
    _rule("MO.no_work_weather", "MO", rf"no work possible, weather, {_N} hours standing", "hour", ["E.51.010"], "hours attended (Clause 6A)"),
    _rule("MO.rained_off", "MO", rf"rained off -- crew and plant stood for {_N} hours", "hour", ["E.51.010"], "hours attended (Clause 6A)"),
    _rule("PR.foundation_pour_cube", "PR", rf"foundation pour {_N} cube, C32/40 off the truck", "m3", ["B.21.020"]),
    _rule("PR.wall_pour", "PR", rf"wall pour {_N} m3, 32/40 mix", "m3", ["B.21.040"]),
    _rule("PR.poured_foundations", "PR", rf"poured {_N} m3 into the foundations, 32/40 mix", "m3", ["B.21.020"]),
    _rule("PR.slab_pour", "PR", rf"slab pour {_N} m3, 32/40", "m3", ["B.21.030"]),
    _rule("PR.poured_slab_cube", "PR", rf"poured the slab, {_N} cube of C32/40", "m3", ["B.21.030"]),
    _rule("PS.machine_stood_idle", "PS", rf"tracked machine stood idle {_N} hours waiting on access", "hour", ["E.51.030"], "hours attended (Clause 6A)"),
    _rule("PS.excavator_held_up", "PS", rf"excavator and driver held up {_N} hours", "hour", ["E.51.030"], "hours attended (Clause 6A)"),
    _rule("PT.large_chamber_1800", "PT", rf"built {_N} large chamber, 1800 dia precast", "no.", ["C.32.030"]),
    _rule("PT.ductile_main_400", "PT", rf"laid {_N} m of 400 ductile main", "lm", ["C.31.020"]),
)


@dataclass(frozen=True)
class RecordQuantity:
    record_id: str
    source_file: str
    record_type: str
    raw_text: str
    quantity: Decimal | None       # None when unresolved
    unit: str | None
    rule_id: str | None
    indicated_items: tuple[str, ...]
    details: dict
    resolved: bool
    reason: str = ""


def depth_item(depth: Decimal) -> str | None:
    """P13 p.13: trench depth decides A.12.020 (<= 2 m), A.12.030 (2-4 m) or A.12.040 (> 4 m).

    A depth of exactly 2 m or 4 m sits on a printed boundary ('not exceeding 2 m', '2 m to 4 m',
    'exceeding 4 m'); 2 m is read as 'not exceeding 2 m' and 4 m as '2 m to 4 m'.
    """
    if depth <= 2:
        return "A.12.020"
    if depth <= 4:
        return "A.12.030"
    return "A.12.040"


def extract_quantity(record: SiteRecord) -> RecordQuantity:
    rid = record.ticket or record.source_file
    matches = [(r, r.pattern.match(record.description)) for r in RULES if r.record_type == record.record_type]
    matches = [(r, m) for r, m in matches if m]
    if len(matches) != 1:
        reason = "no rule matches the description" if not matches else f"ambiguous: {len(matches)} rules match"
        return RecordQuantity(rid, record.source_file, record.record_type or "?", record.description, None, None, None, (), {}, False, reason)
    rule, m = matches[0]
    details = {}
    items = rule.indicated_items
    if "depth" in m.groupdict():
        depth = Decimal(m["depth"])
        details["depth_m"] = str(depth)
        items = (depth_item(depth),)
    if record.record_type == "DW":
        details["days_on"] = len(record.days_on)
    return RecordQuantity(rid, record.source_file, record.record_type, record.description, Decimal(m["qty"]), rule.unit,
                          rule.rule_id, items, details, True)


def extract_all(records) -> list[RecordQuantity]:
    return [extract_quantity(r) for r in records]
