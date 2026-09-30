"""Indexes keep every duplicate explicitly; timelines and BHA runs are reconstructed from observed data only."""

from datetime import date

import pytest

from contractor_audit.domains.drilling.ingestion.indexes import DuplicateKeyError, KeyIndex, build_indexes
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset
from contractor_audit.domains.drilling.ingestion.reports import parse_report_text
from contractor_audit.domains.drilling.ingestion.timelines import bha_runs, well_timelines


def report(day: date, run: int, first: date, last: date, hours: int = 5, run_hours: int = 10, well: str = "NGP-XX-001", start: int = 0, end: int = 10):
    text = f"""DAILY DRILLING REPORT
Report: DDR-{well[-3:]}-{day:%Y%m%d}
Contract: DDS-2025-118
Well: {well}
Rig: NG-Rig 99
Date: {day:%d-%b-%Y}

PART A — OPERATIONS SUMMARY
Hole section: 12-1/4"
Status: Operating
Depth start (m MD): {start}
Depth end (m MD): {end}
Circulating hours: {hours}
BHA run: {run}
In the hole: mud motor
Crew on tour: 2 directional hands
Gyro surveys: 0
Pressure points: 0
Wiper trips: 0
Back-reaming hours: 0
Clean-out runs: 0

PART B — BHA RUN RECORD
Run: {run}
Run first day: {first:%d-%b-%Y}
Run last day: {last:%d-%b-%Y}
Tools in run: mud motor
Run circulating hours: {run_hours}
Metres logged: 0
Metres reamed: 0
Radioactive source carried: No

Signed (Company Representative): A
Signed (lead directional driller): B
"""
    return parse_report_text(text, f"records/{day}.txt")


def synthetic(*reports):
    return DrillingDataset((), (), tuple(reports), ())


# --------------------------------------------------------------------------- KeyIndex
def test_key_index_never_overwrites_a_duplicate():
    ix = KeyIndex("t", ["a1", "b1", "a2"], lambda s: s[0])
    assert ix.get("a") == ("a1", "a2") and ix.one("b") == "b1"
    assert ix.duplicates() == {"a": ("a1", "a2")}
    with pytest.raises(DuplicateKeyError):
        ix.one("a")
    with pytest.raises(KeyError):
        ix.one("z")
    assert list(KeyIndex("t", ["b", "a", "c"], lambda s: s).keys()) == ["a", "b", "c"]
    none_keyed = KeyIndex("t", ["", "x"], lambda s: s or None)
    assert none_keyed.unkeyed == ("",) and list(none_keyed.keys()) == ["x"]


# --------------------------------------------------------------------------- real indexes
def test_real_indexes(indexes):
    assert len(indexes.invoices_by_id) == 1906 and not indexes.invoices_by_id.duplicates()
    assert len(indexes.lines_by_id) == 91244 and not indexes.lines_by_id.duplicates()
    assert len(indexes.reports_by_id) == 8151 and not indexes.reports_by_id.duplicates()
    assert len(indexes.reports_by_well_and_date) == 8151 and not indexes.reports_by_well_and_date.duplicates()
    assert len(indexes.invoices_by_well) == 214 and len(indexes.lines_by_invoice) == 1906
    assert len(indexes.lines_by_report_ref) == 8151 and len(indexes.lines_by_report_ref.unkeyed) == 63
    shared = sorted({l.invoice_no for l in indexes.lines_by_report_ref.get("DDR-063-20260427")})
    assert shared == ["MDS-01340", "MDS-01352"]
    r = indexes.reports_by_well_and_date.one(("NGP-BD-011", date(2026, 2, 25)))
    assert r.report_id == "DDR-011-20260225"
    assert [l.line_ref for l in indexes.lines_by_invoice.get("MDS-00001")][:2] == ["MDS-00001-001", "MDS-00001-002"]


def test_repeated_report_and_code_keys_are_visible(indexes):
    dup = indexes.lines_by_report_and_code.duplicates()
    by_code = {}
    for (_, code) in dup:
        by_code[code] = by_code.get(code, 0) + 1
    assert by_code == {"PD-210": 184, "MW-301": 2, "LW-401": 2, "LW-411": 1}


# --------------------------------------------------------------------------- timelines
def test_real_well_timelines(indexes):
    tl = well_timelines(indexes)
    assert len(tl) == 214
    assert all(not t.gaps and not t.report_days_outside_periods for t in tl.values())
    assert all(len(t.rigs) == 1 and len(t.well_classes_stated) == 1 for t in tl.values())
    t = tl["NGP-BD-173"]
    assert t.first_date == date.fromisoformat(min(str(d) for d in t.dates)) and t.dates == tuple(sorted(t.dates))
    assert ("MDS-01619", "MDS-01629") in t.overlapping_periods
    assert len(t.period_days_without_report) > 100


def test_synthetic_timeline_reports_gaps():
    d1, d2, d5 = date(2025, 3, 1), date(2025, 3, 2), date(2025, 3, 5)
    ds = synthetic(report(d1, 1, d1, d5), report(d2, 1, d1, d5), report(d5, 1, d1, d5))
    t = well_timelines(build_indexes(ds))["NGP-XX-001"]
    assert (t.first_date, t.last_date, t.gaps) == (d1, d5, ((date(2025, 3, 3), date(2025, 3, 4)),))
    assert t.report_ids == ("DDR-001-20250301", "DDR-001-20250302", "DDR-001-20250305")


# --------------------------------------------------------------------------- BHA runs
def test_real_bha_runs(indexes):
    runs = bha_runs(indexes)
    assert len(runs) == 1369
    assert all(r.recorded_first == r.observed_first and r.recorded_last == r.observed_last and r.contiguous for r in runs.values())
    assert all(not r.discrepancies for r in runs.values())
    first = runs[("NGP-BD-011", 1)]
    assert first.report_ids[0] == "DDR-011-20260225" and first.observed_first == date(2026, 2, 25)


def test_synthetic_run_discrepancies_are_recorded_not_repaired():
    d = [date(2025, 3, i) for i in range(1, 6)]
    ds = synthetic(report(d[0], 1, d[0], d[3], hours=5, run_hours=12),
                   report(d[1], 1, d[0], d[3], hours=5, run_hours=12),
                   report(d[3], 1, d[1], d[3], hours=5, run_hours=12))
    run = bha_runs(build_indexes(ds))[("NGP-XX-001", 1)]
    assert run.recorded_first_days == (d[0], d[1]) and run.recorded_first is None
    assert (run.observed_first, run.observed_last, run.observed_days, run.contiguous) == (d[0], d[3], 3, False)
    assert run.daily_circulating_hours_total == 15 and run.run_circulating_hours_recorded == (12,)
    notes = " | ".join(run.discrepancies)
    assert "2 first-day" in notes and "not on consecutive days" in notes and "sum to 15" in notes
