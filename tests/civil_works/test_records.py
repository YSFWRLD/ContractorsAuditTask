from datetime import date

import pytest

from contractor_audit.domains.civil_works.records import RECORD_TYPES, parse_record

SIGS = "Signed (foreman): K. Doyle\nCountersigned (Engineer's representative): N. Basri\n"


def _record(prefix, number="00001", headers="Date: 09/01/2025\n", body="some words 12 units", sigs=SIGS, title=None):
    title = RECORD_TYPES[prefix] if title is None else title
    return (f"{title}\nTicket: {prefix}-{number}\nJob: Northern Access Road, Package 4\nArea: S-01 Platform North\n"
            f"{headers}\n{body}\n\n{sigs}")


def _parse(text, name):
    return parse_record(text, name)


# One realistic body per type, in the phrasing the site actually uses.
SAMPLES = {
    "CT": ("Date: 09/01/2025\n", "792 square metres of sub-base in and compacted"),
    "CV": ("Date: 26/01/2025\n", "surveyed 377 m of the finished run with the camera"),
    "DX": ("Date: 18/01/2025\nGround: G1 Loose Sand\n", "trench dig 210 cube, 3 m deep section"),
    "JS": ("Date: 11/01/2025\n", "set out and agreed 4 chainage band with the Engineer"),
    "MO": ("Date: 22/01/2025\n", "rained off -- crew and plant stood for 5 hours"),
    "PR": ("Date: 14/01/2025\n", "wall pour 335 m3, 32/40 mix"),
    "PS": ("Date: 18/01/2025\n", "tracked machine stood idle 9 hours waiting on access"),
    "PT": ("Date: 17/01/2025\nGround: G4 Weathered Rock\n", "built 3 large chamber, 1800 dia precast"),
}


@pytest.mark.parametrize("prefix", sorted(SAMPLES))
def test_each_single_day_type_parses(prefix):
    headers, body = SAMPLES[prefix]
    rec, issues = _parse(_record(prefix, headers=headers, body=body), f"{prefix}-00001.txt")
    assert issues == []
    assert rec.record_type == prefix and rec.ticket == f"{prefix}-00001" and rec.title == RECORD_TYPES[prefix]
    assert rec.area == "S-01 Platform North" and rec.job == "Northern Access Road, Package 4"
    assert rec.description == body            # kept verbatim
    assert rec.date is not None and rec.work_dates == (rec.date,)
    assert rec.foreman.name == "K. Doyle" and rec.engineer_rep.name == "N. Basri"
    assert rec.ground == (headers.split("Ground: ")[1].strip() if "Ground" in headers else None)


def test_dewatering_log_resolves_days_on():
    headers = "Week beginning: 03/02/2025\nDays on: Tue 04/02, Wed 05/02, Thu 06/02, Fri 07/02, Sat 08/02, Sun 09/02\n"
    rec, issues = _parse(_record("DW", headers=headers, body="pumps kept going 1 week this period"), "DW-00001.txt")
    assert issues == []
    assert rec.date is None and rec.week_beginning == date(2025, 2, 3)
    assert rec.days_on == tuple(date(2025, 2, d) for d in range(4, 10))
    assert rec.work_dates == rec.days_on


def test_dewatering_log_across_year_end():
    headers = "Week beginning: 29/12/2025\nDays on: Mon 29/12, Wed 31/12, Thu 01/01, Fri 02/01, Sat 03/01\n"
    rec, issues = _parse(_record("DW", headers=headers), "DW-00001.txt")
    assert issues == []
    assert rec.days_on[-1] == date(2026, 1, 3) and rec.days_on[1] == date(2025, 12, 31)


def test_dewatering_day_outside_week_and_wrong_weekday():
    headers = "Week beginning: 03/02/2025\nDays on: Mon 04/02, Tue 20/02\n"
    rec, issues = _parse(_record("DW", headers=headers), "DW-00001.txt")
    assert {i.code for i in issues} == {"days_on_weekday_mismatch", "days_on_outside_week"}
    assert rec.days_on == (date(2025, 2, 4),)


def test_blank_countersignature_is_unsigned_not_missing():
    sigs = "Signed (foreman): S. Raman\nCountersigned (Engineer's representative): ____________________\n"
    rec, issues = _parse(_record("DX", headers="Date: 01/03/2025\nGround: G2 Firm Sabkha\n", sigs=sigs), "DX-00001.txt")
    assert rec.engineer_rep.present and not rec.engineer_rep.signed
    assert rec.foreman.signed
    assert [i.code for i in issues] == ["unsigned_engineer_rep"]


def test_missing_signature_line():
    rec, issues = _parse(_record("CT", sigs="Signed (foreman): K. Doyle\n"), "CT-00001.txt")
    assert not rec.engineer_rep.present
    assert "missing_engineer_rep_signature_line" in {i.code for i in issues}


@pytest.mark.parametrize("text_change, name, code", [
    (lambda t: t.replace("Date: 09/01/2025", "Date: 2025-01-09"), "CT-00001.txt", "bad_date"),
    (lambda t: t.replace("Date: 09/01/2025\n", ""), "CT-00001.txt", "missing_date"),
    (lambda t: t, "CT-00002.txt", "ticket_filename_mismatch"),
    (lambda t: t.replace("COMPACTION TEST CERTIFICATE", "CONCRETE POUR RECORD"), "CT-00001.txt", "title_type_mismatch"),
    (lambda t: t.replace("some words 12 units", ""), "CT-00001.txt", "empty_description"),
    (lambda t: t.replace("Ticket: CT-00001", "Ticket: 12345"), "CT-00001.txt", "bad_ticket"),
    (lambda t: t.replace("Area: S-01 Platform North\n", ""), "CT-00001.txt", "missing_area"),
])
def test_malformed_records_become_issues(text_change, name, code):
    rec, issues = _parse(text_change(_record("CT")), name)
    assert code in {i.code for i in issues}
    assert rec.source_file == name


def test_unknown_series_is_reported():
    text = _record("CT").replace("CT-00001", "ZZ-00001").replace("COMPACTION TEST CERTIFICATE", "SOMETHING ELSE")
    rec, issues = _parse(text, "ZZ-00001.txt")
    assert rec.record_type == "ZZ" and "unknown_record_type" in {i.code for i in issues}


def test_crlf_and_raw_text_preserved():
    text = _record("PR").replace("\n", "\r\n")
    rec, issues = _parse(text, "PR-00001.txt")
    assert issues == [] and rec.raw_text == text and rec.description == "some words 12 units"


# --------------------------------------------------------------------------- real task data

def test_all_real_records_parse(record_set):
    assert len(record_set.records) == 2169
    counts = {p: sum(r.record_type == p for r in record_set.records) for p in RECORD_TYPES}
    assert counts == {"CT": 381, "CV": 120, "DW": 114, "DX": 266, "JS": 368, "MO": 142, "PR": 365, "PS": 143, "PT": 270}
    assert [(i.source_file, i.code) for i in record_set.issues] == [("DX-00089.txt", "unsigned_engineer_rep")]
    assert all(r.work_dates for r in record_set.records)
