"""Load and validate the reviewed drilling contract artifacts.

The reviewed files are the source of truth: contract_terms.json (facts, with provenance) and
contract_ambiguities.json (contested readings). Nothing here reads the PDF or any invoice data.
"""

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

from contractor_audit.domains.drilling.contract.models import (
    Ambiguity, AmbiguityStatus, ContractTerms, ContractYear, DailyLimit, DepthBand, Document, FactStatus,
    FieldTermMapping, Instrument, InvoiceDiscount, LostInHoleTerms, MonthlyRates, PrecedenceRule, PriceIndex,
    Provenance, RateBasis, RateDiscount, RateSubstitution, Reading, ServiceDefinition, Standby, StandbyTreatment,
    TermExtension, VolumeTier, day_before,
)

TERMS_FILENAME = "contract_terms.json"
AMBIGUITIES_FILENAME = "contract_ambiguities.json"
TERMS_SCHEMA = ("contractor-audit/drilling-contract-terms", "1.0")
AMBIGUITIES_SCHEMA = ("contractor-audit/drilling-contract-ambiguities", "1.0")
CONTRACT_PAGES = 42
TERMS_KEYS = ("schema", "schema_version", "contract_ref", "status_definitions", "extraction", "source_files", "documents",
              "identity", "contract_years", "precedence", "services", "invoice_discount", "cost_build_up", "depth_bands",
              "volume_tiers", "price_index", "lost_in_hole", "monthly_rates", "instruments", "variations_table",
              "appendix_g", "records", "chargeability", "billing_rules", "definitions", "worked_examples",
              "evidence_not_provided")
UNITS = {"person-day", "day", "run", "hour", "survey", "well", "metre", "point", "trip", "each"}
MONEY_SUFFIXES = ("_cents", "_halalas")


class ContractTermsError(ValueError):
    pass


# --------------------------------------------------------------------------- raw loading
def _reject_float(text: str):
    raise ContractTermsError(f"float literal {text!r} in a reviewed artifact; money is integer minor units, other decimals are strings")


def load_raw(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_float=_reject_float)


def _walk(node: Any, path: str = "$") -> Iterator[tuple[str, str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield path, key, value
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk(value, f"{path}[{i}]")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _date(text: str) -> date:
    return date.fromisoformat(text)


def _dec(text: str) -> Decimal:
    if not isinstance(text, str):
        raise ContractTermsError(f"decimal {text!r} must be a string")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ContractTermsError(f"not a decimal: {text!r}") from exc


def _prov(p: dict) -> Provenance:
    return Provenance(p["source_file"], p.get("page"), p.get("printed_page"), p.get("section", ""), p.get("source_text", ""))


# --------------------------------------------------------------------------- validation
def validate_terms(raw: dict) -> list[str]:
    problems: list[str] = []
    if (raw.get("schema"), raw.get("schema_version")) != TERMS_SCHEMA:
        problems.append(f"schema/version {raw.get('schema')!r}/{raw.get('schema_version')!r}, expected {TERMS_SCHEMA}")
    problems += [f"missing top-level key {k!r}" for k in TERMS_KEYS if k not in raw]
    if problems:
        return problems

    for path, key, value in _walk(raw):
        if key.endswith(MONEY_SUFFIXES) and value is not None and not _is_int(value):
            problems.append(f"{path}.{key}: money must be integer minor units, got {value!r}")
        if key == "provenance":
            for p in value:
                page = p.get("page")
                if not p.get("source_file") or not p.get("source_text"):
                    problems.append(f"{path}: provenance without source_file/source_text")
                if page is not None and not (1 <= page <= CONTRACT_PAGES):
                    problems.append(f"{path}: page {page} outside 1..{CONTRACT_PAGES}")

    pages = sorted(p for d in raw["documents"] for p in range(d["pages"][0], d["pages"][1] + 1))
    if pages != list(range(1, CONTRACT_PAGES + 1)):
        problems.append("documents do not cover pages 1..42 exactly once")

    codes = [s["code"] for s in raw["services"]]
    duplicates = sorted({c for c in codes if codes.count(c) > 1})
    if duplicates:
        problems.append(f"duplicate service codes {duplicates}")
    known = set(codes)
    for s in raw["services"]:
        if s["unit"] not in UNITS:
            problems.append(f"{s['code']}: unknown unit {s['unit']!r}")
        basis, cents = s["rate"]["basis"], s["rate"]["base_rate_cents"]
        if (basis == "SCHEDULE_1") != (cents is not None):
            problems.append(f"{s['code']}: rate basis {basis} inconsistent with base_rate_cents {cents!r}")
        if not s.get("provenance"):
            problems.append(f"{s['code']}: no provenance")

    ids = [i["id"] for i in raw["instruments"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate instrument ids")
    for ins in raw["instruments"]:
        issued, effective = _date(ins["issued"]), _date(ins["effective"])
        if ins["retroactive"] != (effective < issued):
            problems.append(f"{ins['id']}: retroactive flag disagrees with its dates")
        for ch in ins["changes"]:
            for code in ch.get("codes", [ch.get("code")]):
                if code is not None and code not in known:
                    problems.append(f"{ins['id']}: change refers to unknown service {code}")
    table = {(r["instrument"].split()[0][0] + r["instrument"].split()[-1]): (r["issued"], r["effective"]) for r in raw["variations_table"]["rows"]}
    for ins in raw["instruments"]:
        if table.get(ins["id"]) != (ins["issued"], ins["effective"]):
            problems.append(f"{ins['id']}: dates differ from the Schedule of Variations table")

    problems += _check_substitution_chain(raw)
    for row in raw["appendix_g"]["rows"]:
        if row["code"] not in known:
            problems.append(f"Appendix G row {row['row']}: unknown code {row['code']}")
    for code in raw["cost_build_up"]["section_rated_services"] + raw["cost_build_up"]["class_rated_services_as_printed"]:
        if code not in known:
            problems.append(f"factor list names unknown service {code}")
    for group in ("hole_section_factors", "well_class_factors"):
        for value in raw["cost_build_up"][group].values():
            _dec(value)
    for value in list(raw["price_index"]["monthly_index"].values()) + list(raw["lost_in_hole"]["exchange_rates"]["months"].values()):
        _dec(value)
    return problems


def _check_substitution_chain(raw: dict) -> list[str]:
    """Each substitution's 'rate previously chargeable' must equal the rate the earlier statements left in force."""
    base = {s["code"]: s["rate"]["base_rate_cents"] for s in raw["services"]}
    subs = sorted(((ch, ins) for ins in raw["instruments"] for ch in ins["changes"] if ch["kind"] == "RATE_SUBSTITUTION"),
                  key=lambda pair: (pair[1]["issued"], pair[0]["effective"]))
    problems = []
    for ch, ins in subs:
        eff = _date(ch["effective"])
        earlier = [c for c, i in subs if c["code"] == ch["code"] and i["issued"] < ins["issued"] and _date(c["effective"]) <= day_before(eff)]
        expected = max(earlier, key=lambda c: c["effective"])["rate_cents"] if earlier else base[ch["code"]]
        if ch["previous_rate_cents"] != expected:
            problems.append(f"{ins['id']} {ch['code']}: previous rate {ch['previous_rate_cents']} but {expected} was in force")
    return problems


def validate_ambiguities(raw: dict) -> list[str]:
    problems: list[str] = []
    if (raw.get("schema"), raw.get("schema_version")) != AMBIGUITIES_SCHEMA:
        problems.append(f"schema/version {raw.get('schema')!r}/{raw.get('schema_version')!r}, expected {AMBIGUITIES_SCHEMA}")
        return problems
    seen = set()
    for a in raw["ambiguities"]:
        for key in ("id", "topic", "title", "source_locations", "issue", "readings", "preferred_reading", "preference_basis",
                    "confidence", "affects_totals", "resolve_in_phase", "status"):
            if key not in a:
                problems.append(f"{a.get('id')}: missing {key}")
        if a["id"] in seen:
            problems.append(f"duplicate ambiguity id {a['id']}")
        seen.add(a["id"])
        if len(a["readings"]) < 2:
            problems.append(f"{a['id']}: fewer than two readings")
        if a["status"] not in AmbiguityStatus.__members__:
            problems.append(f"{a['id']}: unknown status {a['status']}")
        reading_ids = {r["id"] for r in a["readings"]}
        if a["preferred_reading"] is not None and a["preferred_reading"] not in reading_ids:
            problems.append(f"{a['id']}: preferred reading {a['preferred_reading']} is not one of its readings")
        if (a["preferred_reading"] is None) != (a["confidence"] is None):
            problems.append(f"{a['id']}: confidence must be given exactly when a reading is preferred")
        if a["status"] == "RESOLVED_BY_TEXT" and a["confidence"] != "HIGH":
            problems.append(f"{a['id']}: resolved by text needs HIGH confidence")
    return problems


def ambiguity_refs(raw_terms: dict) -> set[str]:
    return {ref for _, key, value in _walk(raw_terms) if key in ("ambiguities", "class_factor_conflict", "class_rating_ambiguity")
            for ref in (value if isinstance(value, list) else [value])}


# --------------------------------------------------------------------------- typed construction
def load_ambiguities(path: Path) -> tuple[Ambiguity, ...]:
    raw = load_raw(path)
    problems = validate_ambiguities(raw)
    if problems:
        raise ContractTermsError("; ".join(problems))
    return tuple(
        Ambiguity(a["id"], a["topic"], a["title"], a["issue"],
                  tuple(Reading(r["id"], r["reading"], tuple(_prov(e) for e in r["evidence"])) for r in a["readings"]),
                  a["preferred_reading"], a["confidence"], a["affects_totals"], tuple(a["services"]), a["resolve_in_phase"],
                  AmbiguityStatus(a["status"]), tuple(sorted({loc["page"] for loc in a["source_locations"]})))
        for a in raw["ambiguities"])


def load_contract_terms(path: Path, ambiguities_path: Path | None = None) -> ContractTerms:
    """Validated terms. With `ambiguities_path`, every ambiguity the terms cite must exist in the register."""
    raw = load_raw(path)
    problems = validate_terms(raw)
    refs = ambiguity_refs(raw)
    if ambiguities_path is not None:
        registered = {a.id for a in load_ambiguities(ambiguities_path)}
        problems += [f"terms cite unregistered ambiguity {r}" for r in sorted(refs - registered)]
    if problems:
        raise ContractTermsError("; ".join(problems))
    return _build(raw, frozenset(refs))


def _build(raw: dict, refs: frozenset[str]) -> ContractTerms:
    ident = raw["identity"]
    pdf = next(f for f in raw["source_files"] if f["file"].endswith(".pdf"))
    services = {}
    for s in raw["services"]:
        sb = s["standby"]
        services[s["code"]] = ServiceDefinition(
            code=s["code"], series=s["series"], description=s["description"], unit=s["unit"],
            rate_basis=RateBasis(s["rate"]["basis"]), base_rate_cents=s["rate"]["base_rate_cents"],
            section_rated=s["section_rated"], class_rated=s["class_rated"],
            standby=Standby(StandbyTreatment(sb["treatment"]), _dec(sb["percent"]) if sb["percent"] is not None else None),
            daily_limit=DailyLimit(s["daily_limit"]["quantity"], s["daily_limit"]["unit"]) if s["daily_limit"] else None,
            once_per_well=s["once_per_well"], minimum_hours_operating_day=s["minimum_hours_operating_day"],
            record_part_required=s["record_part_required"], indexed=s["indexed"], monthly_republished_by=s["monthly_republished_by"],
            rate_amended_by=tuple(s["rate_amended_by"]), rate_discounted_by=tuple(s["rate_discounted_by"]),
            appendix_g_terms=tuple(s["appendix_g_terms"]), charged_for=s["charged_for"], charge_timing=s["charge_timing"],
            governing_clauses=tuple(s["governing_clauses"]), provenance=tuple(_prov(p) for p in s["provenance"]),
            personnel_normally_on_rig=s.get("personnel_normally_on_rig"))
    instruments = []
    for ins in raw["instruments"]:
        ch = ins["changes"]
        instruments.append(Instrument(
            id=ins["id"], title=ins["title"], reference=ins["reference"], issued=_date(ins["issued"]), effective=_date(ins["effective"]),
            page=ins["page"], cited_clauses=tuple(ins["cited_clauses"]),
            substitutions=tuple(RateSubstitution(ins["id"], c["code"], c["unit"], c["previous_rate_cents"], c["rate_cents"], _date(c["effective"]))
                                for c in ch if c["kind"] == "RATE_SUBSTITUTION"),
            monthly_rates=tuple(MonthlyRates(ins["id"], c["code"], c["index_reference"], dict(c["months"])) for c in ch if c["kind"] == "MONTHLY_RATES"),
            discounts=tuple(RateDiscount(ins["id"], _dec(c["percent"]), tuple(c["codes"]), _date(c["effective"])) for c in ch if c["kind"] == "RATE_DISCOUNT"),
            extensions=tuple(TermExtension(ins["id"], _date(c["new_expiry"]), c["extension_days"]) for c in ch if c["kind"] == "TERM_EXTENSION"),
            added_services=tuple(ins["added_services"]), removed_services=tuple(ins["removed_services"])))
    cb, lih, pi, disc = raw["cost_build_up"], raw["lost_in_hole"], raw["price_index"], raw["invoice_discount"]
    dep = lih["depreciation"]
    return ContractTerms(
        contract_ref=raw["contract_ref"], currency=ident["currency"]["value"], vat_percent=_dec(ident["vat_percent"]["value"]),
        commencement=_date(ident["commencement"]["value"]), original_expiry=_date(ident["original_expiry"]["value"]),
        source_sha256=pdf["sha256"],
        documents=tuple(Document(d["id"], d["title"], d["kind"], d["pages"][0], d["pages"][1], d["in_contents"], d["listed_in_clause_2"],
                                 d.get("reference"), _date(d["issued"]) if d.get("issued") else None,
                                 _date(d["effective"]) if d.get("effective") else None) for d in raw["documents"]),
        precedence=tuple(PrecedenceRule(r["id"], r["rule"], FactStatus(r["status"]), tuple(r.get("ambiguities", []))) for r in raw["precedence"]["rules"]),
        unranked_documents=tuple(raw["precedence"]["unranked_documents"]),
        services=services, instruments=tuple(instruments),
        section_factors={k: _dec(v) for k, v in cb["hole_section_factors"].items()},
        class_factors={k: _dec(v) for k, v in cb["well_class_factors"].items()},
        depth_bands=tuple(DepthBand(b["band"], b["over_m"], b["to_m"], b["rate_cents"]) for b in raw["depth_bands"]["bands"]),
        volume_tiers=tuple(VolumeTier(t["band"], t.get("from_m", t.get("above_m", 0) + 1), t.get("to_m"), _dec(t["percent_of_rate"]))
                           for t in raw["volume_tiers"]["tiers"]),
        price_index=PriceIndex(pi["name"], _dec(pi["base_index"]), {s["code"]: s["base_rate_cents"] for s in pi["services"]},
                               {m: _dec(v) for m, v in pi["monthly_index"].items()}),
        lost_in_hole=LostInHoleTerms(tuple(lih["services"]), {c: v["value_halalas"] for c, v in lih["replacement_values_sar"].items()},
                                     {c: v["value_cents"] for c, v in lih["replacement_values_usd_as_let"].items()},
                                     {m: _dec(v) for m, v in lih["exchange_rates"]["months"].items()},
                                     _dec(dep["percent_per_block"]), dep["block_hours"], _dec(dep["cap_percent"])),
        invoice_discount=InvoiceDiscount(disc["code"], disc["threshold_cents"], disc["comparison"], _dec(disc["percent"])),
        appendix_g=tuple(FieldTermMapping(r["row"], r["code"], r["schedule_1_description"], r["report_term"]) for r in raw["appendix_g"]["rows"]),
        contract_years=tuple(ContractYear(y["year"], _date(y["start"]), _date(y["end"]), FactStatus(y["status"]), tuple(y.get("ambiguities", [])))
                             for y in raw["contract_years"]["years"]),
        evidence_not_provided=tuple(e["id"] for e in raw["evidence_not_provided"]),
        ambiguity_refs=refs,
    )
