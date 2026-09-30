"""Typed access to the reviewed contract extraction (artifacts/civil_works/contract_extraction.json).

The audit never reads the scanned PDF. This module loads the reviewed transcription,
validates its shape and provenance, and exposes the terms as typed values. It states
what the contract says; how those terms combine into a price is decided elsewhere.
"""

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

CONTRACT_PAGE_COUNT = 43
REVIEW_STATUSES = {"VERIFIED", "AMBIGUOUS", "UNREADABLE", "NOT_PROVIDED_IN_DATA"}
PROVENANCE_KEYS = ("source_page", "source_section", "source_text", "review_status", "review_passes")
# Sections whose values drive pricing: each must have been read twice (contract_verification.md).
HIGH_IMPACT_SECTIONS = ("schedule_1", "schedule_2", "schedule_2a", "schedule_2b", "schedule_3",
                        "schedule_4", "schedule_5", "schedule_of_variations", "instruments", "agreement")
EXTRACTION_FILENAME = "contract_extraction.json"


class ContractExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class Provenance:
    page: int
    section: str
    text: str
    status: str
    passes: int


@dataclass(frozen=True)
class BoqItem:
    code: str
    series: str
    description: str
    unit: str
    estimated_quantity: Decimal
    base_rate: Decimal
    provenance: Provenance


@dataclass(frozen=True)
class Band:
    """One printed band row, kept as printed: either `from`..`to`, or `above`."""
    printed: str
    start: int | None
    end: int | None
    above: int | None
    percent_of_rate: Decimal


@dataclass(frozen=True)
class DailyLimit:
    code: str
    limit: Decimal
    unit: str


@dataclass(frozen=True)
class Exclusion:
    excluded_item: str
    excluded_by: str
    period_days: int


@dataclass(frozen=True)
class RecordRequirement:
    code: str
    record_name: str
    reference_series: str


@dataclass(frozen=True)
class RateSubstitution:
    instrument_id: str
    code: str
    unit: str
    rate_previously_payable: Decimal
    rate_payable: Decimal
    effective: date


@dataclass(frozen=True)
class MonthlyRate:
    instrument_id: str
    code: str
    month: str          # "YYYY-MM"
    rate_payable: Decimal


@dataclass(frozen=True)
class Discount:
    instrument_id: str
    percent: Decimal
    effective: date
    codes: tuple[str, ...]


@dataclass(frozen=True)
class Instrument:
    id: str
    name: str
    reference: str
    issued: date
    effective: date
    retroactive: bool
    new_completion_date: date | None
    rate_substitutions: tuple[RateSubstitution, ...]
    monthly_rates: tuple[MonthlyRate, ...]
    discount: Discount | None
    page: int


@dataclass(frozen=True)
class ContractYear:
    year: int
    start: date
    end: date


@dataclass(frozen=True)
class Ambiguity:
    id: str
    topic: str
    readings: tuple[str, ...]
    impact: str
    status: str
    pages: tuple[int, ...]


@dataclass(frozen=True)
class ContractTerms:
    contract_ref: str
    currency: str
    commencement_date: date
    original_completion_date: date
    retention_percent: Decimal
    rest_days: tuple[str, ...]
    boq: dict[str, BoqItem]
    zone_factor_series: frozenset[str]
    zone_factors: dict[str, Decimal]
    work_areas: tuple[str, ...]
    ground_factor_items: frozenset[str]
    ground_factors: dict[str, Decimal]
    night_uplift_percent: dict[str, Decimal]
    rest_day_uplift_percent: dict[str, Decimal]
    bands: dict[str, tuple[Band, ...]]
    daily_limits: dict[str, DailyLimit]
    exclusions: tuple[Exclusion, ...]
    surveyed_items: frozenset[str]
    survey_tolerance_percent: Decimal
    required_records: dict[str, RecordRequirement]
    week_minimum_days: int
    indexed_items: frozenset[str]
    index_base: Decimal
    site_materials_index: dict[str, Decimal]
    usd_items: dict[str, Decimal]
    fx_halalas_per_usd: dict[str, Decimal]
    instruments: tuple[Instrument, ...]
    contract_years: tuple[ContractYear, ...]
    ambiguities: tuple[Ambiguity, ...]
    source_sha256: str

    @property
    def completion_date(self) -> date:
        """Date for Completion as extended by every instrument."""
        extended = [i.new_completion_date for i in self.instruments if i.new_completion_date]
        return max(extended, default=self.original_completion_date)


# --------------------------------------------------------------------------- validation

def iter_provenance(node: Any, path: str = "$") -> Iterator[tuple[str, dict]]:
    """Every object in the extraction that carries (or partly carries) provenance, with its JSON path.

    A node counts as soon as it has any provenance key, so a value that lost its page is still checked.
    Ambiguity entries cite `source_pages` and are validated separately.
    """
    if isinstance(node, dict):
        if any(key in node for key in PROVENANCE_KEYS if key != "review_status"):
            yield path, node
        for key, value in node.items():
            yield from iter_provenance(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from iter_provenance(value, f"{path}[{i}]")


def validate_extraction(raw: dict) -> list[str]:
    """Structural and provenance problems in a raw extraction; empty when valid."""
    problems: list[str] = []
    for key in ("schema_version", "contract_ref", "source_document", "agreement", "schedule_1", "schedule_2",
                "schedule_2a", "schedule_2b", "schedule_3", "schedule_4", "schedule_5", "instruments",
                "schedule_of_variations", "ambiguities", "clauses"):
        if key not in raw:
            problems.append(f"missing top-level key {key!r}")
    if problems:
        return problems

    for path, node in iter_provenance(raw):
        for key in PROVENANCE_KEYS:
            if key not in node:
                problems.append(f"{path}: missing {key}")
        page = node.get("source_page")
        if not isinstance(page, int) or not 1 <= page <= CONTRACT_PAGE_COUNT:
            problems.append(f"{path}: source_page {page!r} outside 1..{CONTRACT_PAGE_COUNT}")
        if node.get("review_status") not in REVIEW_STATUSES:
            problems.append(f"{path}: review_status {node.get('review_status')!r}")
        if not str(node.get("source_text", "")).strip():
            problems.append(f"{path}: empty source_text")
        if node.get("review_passes") not in (1, 2):
            problems.append(f"{path}: review_passes {node.get('review_passes')!r}")
        top = path.split(".")[1].split("[")[0] if "." in path else ""
        if top in HIGH_IMPACT_SECTIONS and node.get("review_status") == "VERIFIED" and node.get("review_passes") != 2:
            problems.append(f"{path}: high-impact value marked VERIFIED after a single pass")

    codes = [item.get("code") for item in raw["schedule_1"].get("items", [])]
    if len(codes) != len(set(codes)):
        problems.append("schedule_1: duplicate item codes")
    known = set(codes)

    def check_codes(where: str, refs) -> None:
        for code in refs:
            if code not in known:
                problems.append(f"{where}: item {code!r} is not in Schedule 1")

    s4 = raw["schedule_4"]
    check_codes("schedule_2a", (i["code"] for i in raw["schedule_2a"]["items"]))
    check_codes("schedule_2b", (i["code"] for i in raw["schedule_2b"]["items"]))
    check_codes("schedule_3", raw["schedule_3"]["applies_to_items"])
    for part in ("night_uplift", "rest_day_uplift", "banded_quantities", "daily_limits", "surveyed_items"):
        check_codes(f"schedule_4.{part}", (i["code"] for i in s4[part]["items"]))
    check_codes("schedule_5", (i["code"] for i in raw["schedule_5"]["items"]))
    for inst in raw["instruments"]:
        check_codes(f"instrument {inst['id']}", (r["code"] for r in inst.get("rate_substitutions", {}).get("rows", [])))
        check_codes(f"instrument {inst['id']}", (i["code"] for i in inst.get("discount", {}).get("items", [])))
        if "monthly_rates" in inst:
            check_codes(f"instrument {inst['id']}", [inst["monthly_rates"]["code"]])
    for amb in raw["ambiguities"]:
        if amb.get("review_status") not in REVIEW_STATUSES - {"VERIFIED"}:
            problems.append(f"ambiguity {amb.get('id')}: status {amb.get('review_status')!r}")
        if not amb.get("readings"):
            problems.append(f"ambiguity {amb.get('id')}: no readings recorded")
    return problems


# --------------------------------------------------------------------------- loading

def _prov(node: dict) -> Provenance:
    return Provenance(node["source_page"], node["source_section"], node["source_text"],
                      node["review_status"], node["review_passes"])


def _d(text: str) -> Decimal:
    return Decimal(text)


def _date(text: str) -> date:
    return date.fromisoformat(text)


def _int_or_none(text: str | None) -> int | None:
    return None if text is None else int(text)


def _instrument(node: dict) -> Instrument:
    iid = node["id"]
    subs = tuple(RateSubstitution(iid, r["code"], r["unit"], _d(r["rate_previously_payable"]), _d(r["rate_payable"]),
                                  _date(r["effective"]))
                 for r in node.get("rate_substitutions", {}).get("rows", []))
    monthly = ()
    if "monthly_rates" in node:
        m = node["monthly_rates"]
        monthly = tuple(MonthlyRate(iid, m["code"], r["month"], _d(r["rate_payable"])) for r in m["rates"])
    discount = None
    if "discount" in node:
        d = node["discount"]
        discount = Discount(iid, _d(d["percent"]), _date(d["effective"]), tuple(i["code"] for i in d["items"]))
    extension = node.get("completion_extension")
    return Instrument(
        id=iid, name=node["name"], reference=node["reference"], issued=_date(node["issued"]),
        effective=_date(node["effective"]), retroactive=bool(node["retroactive"]),
        new_completion_date=_date(extension["new_completion_date"]) if extension else None,
        rate_substitutions=subs, monthly_rates=monthly, discount=discount, page=node["source_page"],
    )


def terms_from_raw(raw: dict) -> ContractTerms:
    problems = validate_extraction(raw)
    if problems:
        raise ContractExtractionError("invalid contract extraction:\n  " + "\n  ".join(problems[:20]))
    ag = raw["agreement"]
    s4 = raw["schedule_4"]
    return ContractTerms(
        contract_ref=ag["contract_ref"]["value"],
        currency=ag["currency"]["value"],
        commencement_date=_date(ag["commencement_date"]["value"]),
        original_completion_date=_date(ag["completion_date_original"]["value"]),
        retention_percent=_d(ag["retention_percent"]["value"]),
        rest_days=tuple(ag["rest_days"]["value"]),
        boq={i["code"]: BoqItem(i["code"], i["series"], i["description"], i["unit"], _d(i["estimated_quantity"]),
                                _d(i["base_rate"]), _prov(i)) for i in raw["schedule_1"]["items"]},
        zone_factor_series=frozenset(raw["schedule_2"]["applies_to_series"]),
        zone_factors={z["zone"]: _d(z["factor"]) for z in raw["schedule_2"]["zones"]},
        work_areas=tuple(w["work_area"] for w in raw["schedule_2"]["work_areas"]),
        ground_factor_items=frozenset(raw["schedule_3"]["applies_to_items"]),
        ground_factors={g["ground_class"]: _d(g["factor"]) for g in raw["schedule_3"]["classes"]},
        night_uplift_percent={i["code"]: _d(i["uplift_percent"]) for i in s4["night_uplift"]["items"]},
        rest_day_uplift_percent={i["code"]: _d(i["uplift_percent"]) for i in s4["rest_day_uplift"]["items"]},
        bands={i["code"]: tuple(Band(b["printed"], _int_or_none(b["from"]), _int_or_none(b["to"]),
                                     _int_or_none(b["above"]), _d(b["percent_of_rate"])) for b in i["bands"])
               for i in s4["banded_quantities"]["items"]},
        daily_limits={i["code"]: DailyLimit(i["code"], _d(i["limit"]), i["unit"]) for i in s4["daily_limits"]["items"]},
        exclusions=tuple(Exclusion(i["excluded_item"], i["excluded_by"], int(i["period_days"]))
                         for i in s4["mutually_exclusive"]["items"]),
        surveyed_items=frozenset(i["code"] for i in s4["surveyed_items"]["items"]),
        survey_tolerance_percent=_d(s4["surveyed_items"]["tolerance"]["tolerance_percent"]),
        required_records={i["code"]: RecordRequirement(i["code"], i["record_required"], i["reference_series"])
                          for i in raw["schedule_5"]["items"]},
        week_minimum_days=int(raw["schedule_5"]["week_rule"]["minimum_days_worked"]),
        indexed_items=frozenset(i["code"] for i in raw["schedule_2a"]["items"]),
        index_base=_d(raw["schedule_2a"]["base_index"]),
        site_materials_index={m["month"]: _d(m["index"]) for m in raw["schedule_2a"]["monthly_index"]},
        usd_items={i["code"]: _d(i["usd_rate"]) for i in raw["schedule_2b"]["items"]},
        fx_halalas_per_usd={m["month"]: _d(m["halalas_per_usd"]) for m in raw["schedule_2b"]["monthly_fx"]},
        instruments=tuple(sorted((_instrument(i) for i in raw["instruments"]), key=lambda i: i.issued)),
        contract_years=tuple(ContractYear(y["year"], _date(y["start"]), _date(y["end"]))
                             for y in raw["contract_years"]["derived_years"]),
        ambiguities=tuple(Ambiguity(a["id"], a["topic"], tuple(a["readings"]), a["impact"], a["review_status"],
                                    tuple(a["source_pages"])) for a in raw["ambiguities"]),
        source_sha256=raw["source_document"]["sha256"],
    )


def load_raw_extraction(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_contract(path: Path) -> ContractTerms:
    return terms_from_raw(load_raw_extraction(path))
