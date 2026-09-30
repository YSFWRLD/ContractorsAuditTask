from datetime import date
from decimal import Decimal

from contractor_audit.domains.civil_works.models import Application, ApplicationLine
from contractor_audit.domains.civil_works.profiling import description_pattern, record_inventory, source_profile
from contractor_audit.domains.civil_works.records import RecordSet, parse_record


def _app(no, total, retention, net, contract_ref="CW-2025-0417-CIV", applied=date(2025, 3, 20)):
    return Application(no, contract_ref, "Ridgeway Civil Engineering LLC", "S-01 Platform North", "Z1 Compound",
                       date(2025, 3, 1), date(2025, 3, 10), applied, total, retention, net, 0, 0, 2, {})


def _line(app, n, code, qty, rate, amount_cents, ref=None, work_date=date(2025, 3, 5), unit="m3"):
    return ApplicationLine(f"{app}-{n:02d}", app, n, work_date, "S-01 Platform North", code, "desc", unit,
                           "Z1 Compound", None, Decimal(qty), Decimal(rate), amount_cents, False, ref, 2, {})


def _rec(ticket, area="S-01 Platform North", day="05/03/2025"):
    from contractor_audit.domains.civil_works.records import RECORD_TYPES
    text = (f"{RECORD_TYPES[ticket[:2]]}\nTicket: {ticket}\nJob: J\nArea: {area}\nDate: {day}\n\npoured 10 m3\n\n"
            "Signed (foreman): A\nCountersigned (Engineer's representative): B\n")
    return parse_record(text, f"{ticket}.txt")[0]


def _synthetic(terms):
    apps = [_app("PA-1", 100000, 5000, 95000), _app("PA-2", 99999, 4000, 95999, contract_ref="CW-2024-0417-CIV")]
    lines = [
        _line("PA-1", 1, "B.21.020", "100", "400.00", 1000_00, ref="PR-00001"),   # 100 x 400.00 = 40000.00, billed 1000.00
        _line("PA-1", 2, "B.21.020", "1", "990.00", 990_00, ref="PR-00001"),                     # reference reused
        _line("PA-2", 1, "A.12.030", "2", "10.00", 20_00, ref="DX-00009"),                       # reference with no file
        _line("PA-2", 2, "A.12.040", "3", "10.00", 30_00),                                       # Schedule 5 item without reference
        _line("PA-2", 3, "B.21.030", "1", "1.00", 1_00, ref="PR-00002", work_date=date(2025, 3, 6)),
    ]
    records = RecordSet([_rec("PR-00001"), _rec("PR-00002", area="S-02 Platform South"), _rec("PR-00003")], [])
    return apps, lines, records


def test_profile_counts_references(terms):
    apps, lines, records = _synthetic(terms)
    refs = source_profile(apps, lines, records, terms)["record_references"]
    assert refs["lines_with_reference"] == 4 and refs["lines_without_reference"] == 1
    assert refs["references_without_record_file"] == ["DX-00009"]
    assert refs["references_used_on_more_than_one_line"] == {"PR-00001": ["PA-1-01", "PA-1-02"]}
    assert refs["records_never_referenced"] == ["PR-00003"]
    assert refs["schedule_5_items_without_reference"]["lines"] == ["PA-2-02"]
    assert refs["referenced_record_vs_line"] == {"area_equal": 2, "date_equal": 2, "area_differs": 1, "date_differs": 1}


def test_profile_arithmetic_is_descriptive(terms):
    apps, lines, records = _synthetic(terms)
    ar = source_profile(apps, lines, records, terms)["arithmetic"]
    line_ar = ar["line_amount_vs_quantity_times_rate"]
    assert line_ar["exact"] == 4 and line_ar["mismatch"] == 1
    assert line_ar["largest_mismatches"][0]["difference"] == "-39000.00"
    assert ar["application_total_vs_sum_of_line_amounts"]["differ"] == 2
    # 5% of 999.99 = 49.9995 -> floor 49.99 (4999 cents); 4000 printed.
    ret = ar["retention_vs_floor_5_percent_of_total"]
    assert ret["agree"] == 1 and ret["differences"][0] == {"application_no": "PA-2", "difference": "-9.99"}


def test_profile_contract_refs_and_dates(terms):
    apps, lines, records = _synthetic(terms)
    p = source_profile(apps, lines, records, terms)
    assert p["applications"]["contract_refs"]["CW-2024-0417-CIV"] == {"count": 1, "applications": ["PA-2"]}
    assert sum(b["lines"] for b in p["date_relationships"]["line_work_dates_by_interval"]) == len(lines)


def test_record_inventory_duplicates_and_signatures():
    a = _rec("PR-00001")
    dup = _rec("PR-00001")
    inv = record_inventory(RecordSet([a, dup, _rec("PR-00004")], []))
    assert inv["duplicate_tickets"] == ["PR-00001"]
    assert inv["ticket_numbering_gaps"] == {"PR": [2, 3]}
    assert inv["types"]["PR"]["description_patterns"][0] == {"pattern": "poured N mN", "count": 3, "example": "poured 10 m3"}


def test_description_pattern_masks_numbers():
    assert description_pattern("wall pour 335 m3, 32/40 mix") == "wall pour N mN, N/N mix"
    assert description_pattern("laid 1,200 m") == "laid N m"


# --------------------------------------------------------------------------- real task data

def test_real_profile_headlines(applications, lines, record_set, terms):
    p = source_profile(applications, lines, record_set, terms)
    assert p["applications"]["contract_refs"]["CW-2024-0417-CIV"]["applications"] == ["PA-00560", "PA-00711"]
    assert p["lines"]["distinct_item_codes"] == 60 and p["lines"]["item_codes_not_in_schedule_1"] == []
    refs = p["record_references"]
    assert refs["references_without_record_file"] == ["CT-00126", "MO-00089", "PS-00039"]
    assert len(refs["references_used_on_more_than_one_line"]) == 20
    assert refs["records_never_referenced"] == []
    assert p["arithmetic"]["line_amount_vs_quantity_times_rate"]["exact"] + p["arithmetic"]["line_amount_vs_quantity_times_rate"]["mismatch"] == 7746


def test_real_inventory_headlines(record_set):
    inv = record_inventory(record_set)
    assert inv["total_records"] == 2169 and inv["duplicate_tickets"] == []
    assert inv["missing_engineer_signature"] == ["DX-00089.txt"] and inv["missing_foreman_signature"] == []
    assert inv["ticket_numbering_gaps"] == {"CT": [126], "JS": [189], "MO": [89], "PS": [39]}
