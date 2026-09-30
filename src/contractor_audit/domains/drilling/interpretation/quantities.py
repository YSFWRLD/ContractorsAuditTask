"""Daily quantities: what one day's report evidences, from that report alone.

Crew person-days, rental days, DD-120/DD-121/RM-530 hours, the counts of Clause 30, daily metres
(metre_source = DAILY_DEPTH_ADVANCE) and PD-210 metres split at the Schedule 2 band boundaries.
Part B run totals are never used here: they repeat on every day of a run.
"""

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DailyReport
from contractor_audit.domains.drilling.interpretation.common import (
    make_quantity, operating_day, performance_section, record_part, signed, standby_day,
)
from contractor_audit.domains.drilling.interpretation.models import Basis, MappingResult, MappingStatus, Quantity, Scope
from contractor_audit.domains.drilling.interpretation.provenance import field_ref
from contractor_audit.domains.drilling.interpretation.service_mapping import CREW, IN_THE_HOLE, READING_SWITCH, codes_under

# Clause 30: counts charged in the numbers recorded for an Operating day (Schedule 8 names the service for each).
COUNT_FIELDS = (("Gyro surveys", "DD-130", "C"), ("Pressure points", "LW-413", "B"), ("Wiper trips", "HC-610", None),
                ("Clean-out runs", "HC-630", None))
DD120, DD121, DD102, RM510, RM511, RM530, PD210 = "DD-120", "DD-121", "DD-102", "RM-510", "RM-511", "RM-530", "PD-210"


def _reading_sets(result: MappingResult, readings: tuple[str, ...]):
    """[(readings tag, codes)]: one entry when the mapping is reading-independent, else one per reading."""
    if result.status is MappingStatus.UNRESOLVED_INTERPRETATION:
        return [(((READING_SWITCH, r),), codes_under(result, r)) for r in readings]
    return [((), codes_under(result, readings[0]))]


def daily_quantities(terms: ContractTerms, report: DailyReport, mappings: tuple[MappingResult, ...], readings: tuple[str, ...]) -> list[Quantity]:
    ops = report.operations
    if ops is None or report.report_id is None:
        return []
    q: list[Quantity] = []
    base = dict(well=report.well, day=report.date, reports=(report,), run=ops.bha_run)
    sig = signed(report)
    tools = [m for m in mappings if m.source_field.label == IN_THE_HOLE[1]]
    crew = [m for m in mappings if m.source_field.label == CREW[1]]
    in_hole = field_ref(report, *IN_THE_HOLE)
    status_ref = field_ref(report, "A", "Status")

    # crew: one person-day quantity per recorded role, count as printed
    for m, entry in zip(crew, ops.crew):
        for tag, codes in _reading_sets(m, readings):
            for code in codes:
                if code == DD102:
                    tag = tag + (("dd102_basis", "PER_COORDINATOR_RECORDED"),)
                staffing = terms.services[code].personnel_normally_on_rig or ""
                conds = (sig,) + ((performance_section(report),) if "performance-drilled" in staffing else ())
                q.append(make_quantity(terms, code, entry.count or 0, Basis.PERSON_DAY, Scope.DAY, **base, derivation="CREW_COUNT",
                                       clauses=("22", "P7", "Schedule 4"), evidence=(m.source_field,), status=m.status, conditions=conds,
                                       readings=tag, ambiguity_ids=tuple(c for cand in m.candidates for c in cand.ambiguity_ids),
                                       detail=(("role", entry.role), ("raw", entry.raw))))
    if ops.in_the_hole:
        q.append(make_quantity(terms, DD102, 1, Basis.RENTAL_DAY, Scope.DAY, **base, derivation="ANY_TOOL_IN_HOLE", clauses=("Schedule 8",),
                               evidence=(in_hole,), status=MappingStatus.UNRESOLVED_INTERPRETATION, conditions=(sig,),
                               readings=(("dd102_basis", "PER_DAY_TOOL_IN_HOLE"),), ambiguity_ids=("AMB-18",)))

    # tools in the hole: rental days, and the hour/metre services a tool gates
    advance = (ops.depth_end_m or 0) - (ops.depth_start_m or 0)
    rss_status = None
    for m in tools:
        for tag, codes in _reading_sets(m, readings):
            for code in codes:
                service = terms.services[code]
                amb = tuple(c for cand in m.candidates for c in cand.ambiguity_ids)
                if service.unit == "day":
                    q.append(make_quantity(terms, code, 1, Basis.RENTAL_DAY, Scope.DAY, **base, derivation="TOOL_IN_HOLE",
                                           clauses=("28", "P6"), evidence=(m.source_field,), status=m.status, conditions=(sig,),
                                           readings=tag, ambiguity_ids=amb, detail=(("term", m.term),)))
                elif code == DD120:
                    rss_status = m.status
                elif service.unit == "metre" and advance > 0:
                    q.append(make_quantity(terms, code, advance, Basis.METRE, Scope.DAY, **base, derivation="DAILY_DEPTH_ADVANCE",
                                           clauses=("24", "25A"), evidence=(m.source_field, field_ref(report, "A", "Depth start (m MD)"), field_ref(report, "A", "Depth end (m MD)")),
                                           status=m.status, conditions=(operating_day(report, "cl. 24"), record_part(report, "B"), sig),
                                           readings=(("metre_source", "DAILY_DEPTH_ADVANCE"),) + tag, ambiguity_ids=amb + ("AMB-24",),
                                           detail=(("term", m.term),)))
                if code == RM511 and advance > 0:
                    q.append(make_quantity(terms, RM510, advance, Basis.METRE, Scope.DAY, **base, derivation="DAILY_DEPTH_ADVANCE_UNDERREAMER",
                                           clauses=("25", "25A"), evidence=(m.source_field, field_ref(report, "A", "Depth start (m MD)"), field_ref(report, "A", "Depth end (m MD)")),
                                           status=m.status, conditions=(operating_day(report, "cl. 25"), record_part(report, "B"), sig),
                                           readings=(("metre_source", "DAILY_DEPTH_ADVANCE"),) + tag, ambiguity_ids=amb + ("AMB-24",),
                                           detail=(("underreamer_term", m.term),)))
    rss_in_hole = rss_status is not None

    # DD-120 hours (cl. 21) and DD-121 (Standby, in place of DD-120)
    circ = field_ref(report, "A", "Circulating hours")
    back = field_ref(report, "A", "Back-reaming hours")
    if rss_in_hole and (ops.status == "Operating" or ops.circulating_hours):
        cond = (operating_day(report, "cl. 21"), sig)
        for value, reading, evidence in ((ops.circulating_hours or 0, "CIRCULATING_ONLY", (in_hole, circ)),
                                         ((ops.circulating_hours or 0) + (ops.back_reaming_hours or 0), "CIRCULATING_PLUS_BACK_REAMING", (in_hole, circ, back))):
            q.append(make_quantity(terms, DD120, value, Basis.HOUR, Scope.DAY, **base, derivation="DAILY_HOURS", clauses=("21", "P10"),
                                   evidence=evidence, status=rss_status, conditions=cond,
                                   readings=(("dd120_hours", reading),), ambiguity_ids=("AMB-06", "AMB-05")))
    if ops.status == "Standby":
        if rss_in_hole:
            q.append(make_quantity(terms, DD121, 1, Basis.STANDBY_DAY, Scope.DAY, **base, derivation="STANDBY_WITH_RSS_IN_HOLE",
                                   clauses=("21", "Schedule 3 Part 4", "28"), evidence=(status_ref, in_hole), status=MappingStatus.IDENTIFIED,
                                   conditions=(standby_day(report, "cl. 21"), sig), readings=(("dd121_condition", "STANDBY_DAY_RSS_IN_HOLE"),),
                                   ambiguity_ids=("AMB-20",)))
        # dd121_condition reading B is not derived: its only concrete definition (Phase 3 Assumption 3) was rejected.

    # Clause 30 counts and RM-530 back-reaming hours
    for label, code, part in COUNT_FIELDS:
        value = getattr(ops, {"Gyro surveys": "gyro_surveys", "Pressure points": "pressure_points", "Wiper trips": "wiper_trips",
                              "Clean-out runs": "clean_out_runs"}[label])
        if value:
            conds = (operating_day(report, "cl. 30"),) + ((record_part(report, part),) if part else ()) + (sig,)
            tag = (("hc630_basis", "DAILY_COUNT"),) if code == "HC-630" else ()
            q.append(make_quantity(terms, code, value, Basis.COUNT, Scope.DAY, **base, derivation="COUNT_FIELD", clauses=("30",),
                                   evidence=(field_ref(report, "A", label),), status=MappingStatus.IDENTIFIED, conditions=conds,
                                   readings=tag, ambiguity_ids=("AMB-19",) if code == "HC-630" else ()))
    if ops.back_reaming_hours:
        q.append(make_quantity(terms, RM530, ops.back_reaming_hours, Basis.HOUR, Scope.DAY, **base, derivation="COUNT_FIELD",
                               clauses=("30",), evidence=(back,), status=MappingStatus.IDENTIFIED,
                               conditions=(operating_day(report, "cl. 30"), sig), ambiguity_ids=("AMB-05", "AMB-06")))

    # PD-210: metres drilled on the day, one quantity per Schedule 2 band the interval touches
    if advance > 0:
        start, end = ops.depth_start_m, ops.depth_end_m
        for band in terms.depth_bands:
            lo, hi = max(start, band.over_m), min(end, band.to_m if band.to_m is not None else end)
            if hi > lo:
                q.append(make_quantity(terms, PD210, hi - lo, Basis.METRE, Scope.DAY, **base, derivation="DEPTH_BAND_SPLIT",
                                       clauses=("23", "Schedule 2", "25A"),
                                       evidence=(field_ref(report, "A", "Depth start (m MD)"), field_ref(report, "A", "Depth end (m MD)")),
                                       status=MappingStatus.IDENTIFIED, conditions=(performance_section(report), sig),
                                       ambiguity_ids=("AMB-13",), detail=(("band", str(band.band)), ("from_m", str(lo)), ("to_m", str(hi)))))
    return q
