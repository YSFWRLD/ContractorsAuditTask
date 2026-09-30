from datetime import date
from decimal import Decimal

import pytest

from contractor_audit.domains.civil_works.loaders import (APPLICATION_COLUMNS, LINE_COLUMNS, LoadError,
                                                          load_application_lines, load_applications, parse_iso_date)

APP_ROW = "PA-00001,CW-2025-0417-CIV,Ridgeway Civil Engineering LLC,S-03 Access Road,Z2 North Spur,2025-09-18,2025-10-04,2025-10-20,265123.89,13256.19,251867.70,0.00,0.00"
LINE_ROW = 'PA-00001-01,PA-00001,1,2025-09-25,S-03 Access Road,D.43.010,"Road marking, thermoplastic, 100 mm line",lm,Z2 North Spur,,299,19.61,5863.39,Y,'


def _write(tmp_path, name, header, *rows):
    path = tmp_path / name
    path.write_text("\n".join([",".join(header), *rows]) + "\n", encoding="utf-8")
    return path


def test_application_row_is_typed(tmp_path):
    [app] = load_applications(_write(tmp_path, "a.csv", APPLICATION_COLUMNS, APP_ROW))
    assert app.application_no == "PA-00001"
    assert app.period_from == date(2025, 9, 18) and app.application_date == date(2025, 10, 20)
    assert app.application_total_cents == 26512389
    assert app.retention_cents == 1325619 and app.net_payable_cents == 25186770
    assert app.adjustment_cents == 0 and app.retention_released_cents == 0
    assert app.source_row == 2 and app.raw["application_total"] == "265123.89"


def test_line_row_is_typed(tmp_path):
    [line] = load_application_lines(_write(tmp_path, "l.csv", LINE_COLUMNS, LINE_ROW))
    assert line.quantity == Decimal("299") and line.rate_applied == Decimal("19.61")
    assert line.amount_cents == 586339
    assert line.night_work is True
    assert line.ground_class is None and line.record_ref is None
    assert line.description == "Road marking, thermoplastic, 100 mm line"
    assert line.series == "D" and line.work_area == "S-03 Access Road"


@pytest.mark.parametrize("bad, column", [
    (LINE_ROW.replace("2025-09-25", "25/09/2025"), "work_date"),
    (LINE_ROW.replace(",Y,", ",yes,"), "night_work"),
    (LINE_ROW.replace(",299,", ",abc,"), "quantity"),
    (LINE_ROW.replace(",5863.39,", ",5863.391,"), "amount"),
    (LINE_ROW.replace("PA-00001,1,", "PA-00001,x,"), "line_no"),
])
def test_bad_line_values_raise_with_location(tmp_path, bad, column):
    path = _write(tmp_path, "l.csv", LINE_COLUMNS, LINE_ROW, bad)
    with pytest.raises(LoadError) as exc:
        load_application_lines(path)
    assert exc.value.row == 3 and exc.value.column == column


def test_unexpected_header_is_rejected(tmp_path):
    with pytest.raises(LoadError):
        load_applications(_write(tmp_path, "a.csv", APPLICATION_COLUMNS[:-1], APP_ROW))


def test_short_row_is_rejected(tmp_path):
    with pytest.raises(LoadError):
        load_applications(_write(tmp_path, "a.csv", APPLICATION_COLUMNS, APP_ROW.rsplit(",", 1)[0]))


def test_iso_date_is_strict():
    assert parse_iso_date("2026-02-28") == date(2026, 2, 28)
    for text in ("2026-2-28", "28/02/2026", "2026-02-30"):
        with pytest.raises(ValueError):
            parse_iso_date(text)


# --------------------------------------------------------------------------- real task data

def test_real_applications_load(applications):
    assert len(applications) == 900
    first = applications[0]
    assert first.application_no == "PA-00001" and first.application_total_cents == 26512389


def test_real_lines_load(lines):
    assert len(lines) == 7746
    assert lines[0].line_ref == "PA-00001-01"
    assert all(l.amount_cents >= 0 and l.quantity > 0 for l in lines)
