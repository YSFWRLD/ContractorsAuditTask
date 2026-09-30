"""Quantities: provenance, daily/run/well scope, no summed run totals, PD-210 bands, standby, AMB-22/24 dependencies."""

from collections import Counter, defaultdict
from decimal import Decimal

from contractor_audit.domains.drilling.ingestion.models import DrillingDataset
from contractor_audit.domains.drilling.interpretation.engine import interpret
from contractor_audit.domains.drilling.interpretation.models import Basis, Scope


def by_code(result, code, **readings):
    return [q for q in result.quantities if q.service_code == code and all((k, v) in q.readings for k, v in readings.items())]


def test_every_quantity_traces_to_real_report_fields(interpretation, reports_by_id):
    assert len({q.qid for q in interpretation.quantities}) == len(interpretation.quantities)
    for q in interpretation.quantities:
        assert q.report_ids and q.evidence, q.qid
        for e in q.evidence:
            r = reports_by_id[e.report_id]
            raw = next(f for f in r.fields if f.section == e.section and f.label == e.label and f.line == e.line)
            assert raw.value == e.raw_value and r.source.file == e.source_file
        assert q.unit == q.unit and q.quantity >= 0


def test_daily_quantities_use_only_that_days_report(interpretation, reports_by_id):
    for q in interpretation.quantities:
        if q.scope is Scope.DAY:
            (rid,) = q.report_ids
            assert {e.report_id for e in q.evidence} == {rid}
            assert q.date == reports_by_id[rid].date and q.well == reports_by_id[rid].well


def test_crew_person_days_are_the_printed_counts(interpretation, reports_by_id):
    for q in by_code(interpretation, "DD-101"):
        r = reports_by_id[q.report_id]
        assert q.quantity == next(c.count for c in r.operations.crew if c.role == dict(q.detail)["role"])
    assert sum(q.quantity for q in by_code(interpretation, "DD-101")) == Decimal(2 * 8151)


def test_rental_days_only_where_the_tool_is_recorded(interpretation, reports_by_id):
    for q in by_code(interpretation, "HC-601"):
        assert dict(q.detail)["term"] in reports_by_id[q.report_id].operations.in_the_hole and q.quantity == 1
    assert len(by_code(interpretation, "HC-601")) == 1767


def test_run_level_items_once_per_run(interpretation, indexes):
    from contractor_audit.domains.drilling.ingestion.timelines import bha_runs
    runs = bha_runs(indexes)
    dd111 = Counter((q.well, q.run) for q in by_code(interpretation, "DD-111"))
    assert set(dd111.values()) == {1} and len(dd111) == sum(1 for r in runs.values() if "mud motor" in r.tools_as_recorded[0]) == 654
    for q in by_code(interpretation, "DD-111"):
        assert q.date == runs[(q.well, q.run)].recorded_last
    lw420 = Counter((q.well, q.run) for q in by_code(interpretation, "LW-420"))
    assert set(lw420.values()) == {1} and len(lw420) == 369
    for q in by_code(interpretation, "LW-420"):
        assert q.date == runs[(q.well, q.run)].recorded_first
    assert sorted(q.report_id for q in by_code(interpretation, "LW-420") if not dict((c.code, c.satisfied) for c in q.conditions)["RECORD_PART_D"]) == \
        ["DDR-029-20260515", "DDR-201-20251115"]


def test_part_b_run_totals_are_never_summed_over_days(interpretation, reports_by_id):
    for q in by_code(interpretation, "LW-410", metre_source="PART_B_RUN_METRES"):
        first = reports_by_id[q.evidence[0].report_id]
        assert q.quantity == first.bha_run.metres_logged and q.scope is Scope.RUN
    per_run = Counter((q.well, q.run, q.readings) for q in by_code(interpretation, "LW-410", metre_source="PART_B_RUN_METRES"))
    assert set(per_run.values()) == {1}
    # the daily reading sums daily depth advances instead, and the two agree run by run (Phase 2 evidence)
    daily = defaultdict(Decimal)
    for q in by_code(interpretation, "LW-410", metre_source="DAILY_DEPTH_ADVANCE", appendix_g_reading="LITERAL"):
        daily[(q.well, reports_by_id[q.report_id].bha_run.run)] += q.quantity
    run_level = {(q.well, q.run): q.quantity for q in by_code(interpretation, "LW-410", metre_source="PART_B_RUN_METRES", appendix_g_reading="LITERAL")}
    assert daily == run_level


def test_synthetic_run_values_are_read_once(dataset, terms, ambiguities):
    well = "NGP-BD-011"
    reports = [r for r in dataset.reports if r.well == well]
    result = interpret(reports, terms, ambiguities)
    run1 = [r for r in reports if r.bha_run.run == 1]
    assert len(run1) > 1
    assert len([q for q in result.quantities if q.service_code == "DD-111" and q.run == 1]) <= 1
    assert all(q.quantity == run1[0].bha_run.metres_logged for q in result.quantities if q.derivation == "PART_B_METRES_LOGGED" and q.run == 1)


def test_well_level_items_once_per_well(interpretation, indexes):
    for code in ("MB-701", "DD-140", "MB-702", "LW-430"):
        counts = Counter(q.well for q in by_code(interpretation, code))
        assert set(counts.values()) == {1} and len(counts) == 214, code
    for q in by_code(interpretation, "MB-701"):
        assert q.date == min(r.date for r in indexes.reports_by_well.get(q.well))
    for q in by_code(interpretation, "MB-702"):
        assert q.date == max(r.date for r in indexes.reports_by_well.get(q.well))


def test_pd210_bands_split_the_day_without_double_counting(interpretation, reports_by_id, terms):
    per_report = defaultdict(list)
    for q in by_code(interpretation, "PD-210"):
        per_report[q.report_id].append(q)
    for rid, qs in per_report.items():
        ops = reports_by_id[rid].operations
        assert sum(q.quantity for q in qs) == ops.depth_end_m - ops.depth_start_m
        spans = sorted((int(dict(q.detail)["from_m"]), int(dict(q.detail)["to_m"])) for q in qs)
        assert spans[0][0] == ops.depth_start_m and spans[-1][1] == ops.depth_end_m
        assert all(a[1] == b[0] for a, b in zip(spans, spans[1:]))
        for q in qs:
            band = next(b for b in terms.depth_bands if b.band == int(dict(q.detail)["band"]))
            lo, hi = int(dict(q.detail)["from_m"]), int(dict(q.detail)["to_m"])
            assert lo >= band.over_m and (band.to_m is None or hi <= band.to_m)
    assert sum(len(v) > 1 for v in per_report.values()) > 0


def test_pd210_performance_section_is_unknown_or_impossible_never_assumed(interpretation):
    for q in by_code(interpretation, "PD-210"):
        cond = next(c for c in q.conditions if c.code == "PERFORMANCE_SECTION_NOMINATED")
        assert cond.satisfied is (None if q.hole_section in ('12-1/4"', '8-1/2"') else False)


def test_standby_days_keep_their_circulating_hours(interpretation, reports_by_id):
    standby = [q for q in by_code(interpretation, "DD-120", dd120_hours="CIRCULATING_ONLY") if q.day_status == "Standby"]
    assert standby and all(q.quantity > 0 for q in standby)
    assert all(dict((c.code, c.satisfied) for c in q.conditions)["OPERATING_DAY"] is False for q in standby)
    dd121 = {r: len(by_code(interpretation, "DD-121", dd121_condition=r)) for r in ("STANDBY_DAY_RSS_IN_HOLE", "EVERY_STANDBY_DAY_OF_RSS_WELL")}
    assert dd121 == {"STANDBY_DAY_RSS_IN_HOLE": 241, "EVERY_STANDBY_DAY_OF_RSS_WELL": 0}   # reading B: rejected Assumption 3, not derived
    for q in by_code(interpretation, "DD-121"):
        assert "rotary steerable" in reports_by_id[q.report_id].operations.in_the_hole and q.day_status == "Standby"


def test_dd120_hour_readings(interpretation, reports_by_id):
    circ = {q.report_id: q.quantity for q in by_code(interpretation, "DD-120", dd120_hours="CIRCULATING_ONLY")}
    plus = {q.report_id: q.quantity for q in by_code(interpretation, "DD-120", dd120_hours="CIRCULATING_PLUS_BACK_REAMING")}
    assert circ.keys() == plus.keys()
    for rid, value in circ.items():
        ops = reports_by_id[rid].operations
        assert value == ops.circulating_hours and plus[rid] == ops.circulating_hours + ops.back_reaming_hours


def test_lost_in_hole_keeps_amb22_explicit(interpretation):
    lih = [q for q in interpretation.quantities if q.basis is Basis.LOST_IN_HOLE]
    assert len({q.report_id for q in lih}) == 54
    for q in lih:
        d = dict(q.detail)
        assert "AMB-22" in q.ambiguity_ids and "lih_hours" in q.depends_on
        assert {"lih_hours.PART_E_STATED", "lih_hours.TOOL_ACCUMULATED"} <= set(d) and q.quantity == 1
    assert all(dict(q.detail)["readings_agree"] == "True" for q in lih)


def test_metres_keep_amb24_explicit(interpretation):
    for code in ("LW-410", "LW-411", "RM-510"):
        sources = {dict(q.readings).get("metre_source") for q in by_code(interpretation, code)}
        assert sources == {"DAILY_DEPTH_ADVANCE", "PART_B_RUN_METRES"}, code
    assert all("AMB-24" in q.ambiguity_ids for q in interpretation.quantities if dict(q.readings).get("metre_source"))


def test_counts_come_from_their_fields(interpretation, reports_by_id):
    for code, attr in (("DD-130", "gyro_surveys"), ("LW-413", "pressure_points"), ("HC-610", "wiper_trips")):
        qs = by_code(interpretation, code)
        assert qs and all(q.quantity == getattr(reports_by_id[q.report_id].operations, attr) for q in qs)
    gyro_c = [q for q in by_code(interpretation, "DD-130") if not dict((c.code, c.satisfied) for c in q.conditions)["RECORD_PART_C"]]
    assert [q.report_id for q in gyro_c] == ["DDR-009-20251211"]


def test_unparsed_or_empty_input_yields_nothing(terms, ambiguities):
    empty = interpret((), terms, ambiguities)
    assert empty.quantities == () and empty.reports_interpreted == 0
    assert DrillingDataset((), (), (), ()).reports == ()
