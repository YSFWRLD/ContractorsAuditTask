"""Daily Drilling Reports: keyed by their own Report field, rig words verbatim, variants and anomalies explicit."""

from collections import Counter
from datetime import date

from contractor_audit.domains.drilling.ingestion.models import Severity
from contractor_audit.domains.drilling.ingestion.reports import load_reports, parse_report_text

GOOD = """DAILY DRILLING REPORT
Report: DDR-011-20260225
Contract: DDS-2025-118
Well: NGP-BD-011
Rig: NG-Rig 11
Date: 25-Feb-2026

PART A — OPERATIONS SUMMARY
Hole section: 26"
Status: Operating
Depth start (m MD): 0
Depth end (m MD): 275
Circulating hours: 15
BHA run: 1
In the hole: MWD collar, drilling jars, mud motor, real-time link
Crew on tour: 2 directional hands, 1 night man, 2 MWD engineers
Gyro surveys: 1
Pressure points: 0
Wiper trips: 0
Back-reaming hours: 0
Clean-out runs: 0

PART B — BHA RUN RECORD
Run: 1
Run first day: 25-Feb-2026
Run last day: 28-Feb-2026
Tools in run: MWD collar, drilling jars, mud motor, real-time link
Run circulating hours: 59
Metres logged: 0
Metres reamed: 0
Radioactive source carried: No

PART C — GYRO SURVEY RECORD
Gyro surveys taken: 1
Surveyed section: 26"

Signed (Company Representative): P. Lindqvist
Signed (lead directional driller): M. Farouk
"""


def codes(report):
    return sorted(i.code for i in report.issues)


def test_every_report_parses_and_is_keyed_by_its_report_field(dataset):
    assert len(dataset.reports) == 8151
    assert all(r.report_id and r.report_id.startswith("DDR-") for r in dataset.reports)
    assert len({r.report_id for r in dataset.reports}) == 8151
    r = next(r for r in dataset.reports if r.report_id == "DDR-011-20260225")
    assert r.source.file == "drilling_services/records/DDR_NGP-BD-011_20260225.txt"  # the file name is not the key
    assert (r.well, r.rig, r.date, r.contract_ref) == ("NGP-BD-011", "NG-Rig 11", date(2026, 2, 25), "DDS-2025-118")


def test_the_six_part_variants(dataset):
    assert Counter(r.variant for r in dataset.reports) == {"A+B": 7258, "A+B+C": 476, "A+B+D": 363, "A+B+E": 47, "A+B+D+E": 4, "A+B+C+E": 3}
    assert sum(r.gyro is not None for r in dataset.reports) == 479
    assert sum(r.source_handling is not None for r in dataset.reports) == 367
    assert sum(r.lost_in_hole is not None for r in dataset.reports) == 54


def test_only_blank_signatures_are_reported_as_parse_issues(dataset):
    issues = Counter((i.code, i.severity) for r in dataset.reports for i in r.issues)
    assert issues == {("BLANK_SIGNATURE", Severity.INFO): 6}
    blank = sorted(r.report_id for r in dataset.reports if any(s.blank for s in r.signatures))
    assert blank == ["DDR-055-20250503", "DDR-149-20251122", "DDR-218-20251029"]


def test_parts_are_typed_and_rig_words_are_verbatim():
    r = parse_report_text(GOOD, "x.txt")
    assert codes(r) == [] and r.variant == "A+B+C"
    a, b = r.operations, r.bha_run
    assert (a.hole_section, a.status, a.depth_start_m, a.depth_end_m, a.circulating_hours, a.bha_run) == ('26"', "Operating", 0, 275, 15, 1)
    assert a.in_the_hole == ("MWD collar", "drilling jars", "mud motor", "real-time link")
    assert [(c.count, c.role) for c in a.crew] == [(2, "directional hands"), (1, "night man"), (2, "MWD engineers")]
    assert (b.run, b.run_first_day, b.run_last_day, b.run_circulating_hours, b.radioactive_source_carried) == (1, date(2026, 2, 25), date(2026, 2, 28), 59, False)
    assert (r.gyro.surveys_taken, r.gyro.surveyed_section) == (1, '26"')
    assert [(s.role, s.name) for s in r.signatures] == [("Company Representative", "P. Lindqvist"), ("lead directional driller", "M. Farouk")]
    assert r.raw_value("A", "Crew on tour") == "2 directional hands, 1 night man, 2 MWD engineers"
    assert next(f for f in r.fields if f.label == "Report").line == 2


def test_real_part_d_and_e_records(dataset):
    r = next(r for r in dataset.reports if r.report_id == "DDR-152-20260410")
    assert r.variant == "A+B+D+E"
    assert (r.source_handling.source_run, r.source_handling.sources_handled, r.source_handling.certified) == (5, "density and neutron", True)
    assert (r.lost_in_hole.run, r.lost_in_hole.tool, r.lost_in_hole.circulating_hours_accumulated_on_well) == (5, "gamma tool", 14)


def test_crlf_and_lf_parse_identically():
    assert parse_report_text(GOOD.replace("\n", "\r\n"), "x.txt") == parse_report_text(GOOD, "x.txt")


def test_malformed_reports_fail_safely_without_defaults():
    text = (GOOD.replace("Status: Operating", "Status: Operating\nStatus: Standby")          # duplicated label
                .replace("Wiper trips: 0", "Wiper trips: two")                                # not a number
                .replace("Run last day: 28-Feb-2026", "Run last day: 31-Feb-2026")            # impossible date
                .replace("Clean-out runs: 0", "Clean-out runs: 0\nMud weight: 1.2\nsome free text")  # unknown label, non key-value
                .replace("Crew on tour: 2 directional hands", "Crew on tour: two directional hands")
                .replace("Signed (lead directional driller): M. Farouk", "Signed (lead directional driller): ____"))
    r = parse_report_text(text, "x.txt")
    assert codes(r) == ["BLANK_SIGNATURE", "DUPLICATE_LABEL", "IMPOSSIBLE_DATE", "MALFORMED_CREW_ENTRY", "MALFORMED_LINE", "MALFORMED_NUMBER", "UNKNOWN_FIELD"]
    assert r.operations.status == "Operating"          # first value kept, the duplicate reported
    assert r.operations.wiper_trips is None and r.bha_run.run_last_day is None
    assert r.operations.crew[0].count is None and r.operations.crew[0].role == "two directional hands"
    assert r.signatures[1].blank and r.signatures[1].raw == "____"


def test_missing_parts_fields_and_blanks_are_explicit():
    no_b = GOOD[:GOOD.index("PART B")] + "Signed (Company Representative): X\n"
    r = parse_report_text(no_b, "x.txt")
    assert r.bha_run is None and "MISSING_SECTION" in codes(r) and "MISSING_SIGNATURE_LINE" in codes(r)
    r = parse_report_text(GOOD.replace("Pressure points: 0\n", "").replace("Depth end (m MD): 275", "Depth end (m MD):"), "x.txt")
    assert r.operations.pressure_points is None and r.operations.depth_end_m is None
    assert {"MISSING_FIELD", "BLANK_VALUE"} <= set(codes(r))
    r = parse_report_text(GOOD.replace("PART C — GYRO SURVEY RECORD", "PART F — SOMETHING ELSE"), "x.txt")
    assert "UNKNOWN_SECTION" in codes(r) and "UNKNOWN_FIELD" in codes(r) and r.gyro is None
    r = parse_report_text(GOOD.replace("DAILY DRILLING REPORT", "DAILY REPORT") + "Status: late\n", "x.txt")
    assert {"UNEXPECTED_TITLE", "FIELD_AFTER_SIGNATURES"} <= set(codes(r))


def test_unreadable_files_become_error_records(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"\xff\xfe not utf-8")
    (tmp_path / "b.csv").write_text("x", encoding="utf-8")
    (tmp_path / "c.txt").write_text(GOOD, encoding="utf-8")
    reports = load_reports(tmp_path, "records")
    assert [(r.source.file, r.report_id, [i.code for i in r.issues]) for r in reports] == [
        ("records/a.txt", None, ["UNDECODABLE_FILE"]), ("records/b.csv", None, ["UNEXPECTED_FILE"]), ("records/c.txt", "DDR-011-20260225", [])]
