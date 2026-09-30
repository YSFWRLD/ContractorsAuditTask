"""The submission combiner rejects everything the README does not allow, and never repairs a value."""

import pytest

from contractor_audit.shared.submission import COLUMNS, Source, SubmissionError, combine, render, validate_row, write

HEADER = ",".join(COLUMNS) + "\n"


def _file(path, rows, header=HEADER):
    path.write_text(header + "".join(",".join(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    return path


@pytest.fixture
def world(tmp_path):
    template = _file(tmp_path / "template.csv", [["PA-1", "", "", "", "", ""], ["MDS-1", "", "", "", "", ""], ["PA-2", "", "", "", "", ""]])
    a = _file(tmp_path / "a.csv", [["PA-1", "0", "", "100", "100", "0.95"], ["PA-2", "1", "unit_rate_mismatch", "", "250", "0.75"]])
    b = _file(tmp_path / "b.csv", [["MDS-1", "1", "duplicate_charge", "", "999", "0.55"]])
    return tmp_path, template, [Source("a", a), Source("b", b)]


def test_rows_follow_the_template_order_and_keep_values_verbatim(world):
    tmp, template, sources = world
    rows = write(template, sources, tmp / "submission.csv")
    assert [r["invoice_id"] for r in rows] == ["PA-1", "MDS-1", "PA-2"]
    text = (tmp / "submission.csv").read_bytes()
    assert text == render(rows).encode() and b"\r" not in text
    assert text.splitlines()[3] == b"PA-2,1,unit_rate_mismatch,,250,0.75"          # a blank expected total stays blank


def test_missing_domain_results(world):
    tmp, template, sources = world
    with pytest.raises(SubmissionError, match="not found"):
        combine(template, sources + [Source("c", tmp / "missing.csv")])
    with pytest.raises(SubmissionError, match="no domain results"):
        combine(template, [])


def test_missing_extra_and_duplicate_ids(world):
    tmp, template, (a, b) = world
    with pytest.raises(SubmissionError, match="have no result"):
        combine(template, [a])
    extra = _file(tmp / "extra.csv", [["MDS-1", "0", "", "1", "1", "0.95"], ["MDS-9", "0", "", "1", "1", "0.95"]])
    with pytest.raises(SubmissionError, match="not template invoice ids"):
        combine(template, [a, Source("b", extra)])
    dup = _file(tmp / "dup.csv", [["MDS-1", "0", "", "1", "1", "0.95"], ["PA-1", "0", "", "100", "100", "0.95"]])
    with pytest.raises(SubmissionError, match="duplicate invoice id"):
        combine(template, [a, Source("b", dup)])
    twice = _file(tmp / "twice.csv", [["MDS-1", "0", "", "1", "1", "0.95"], ["MDS-1", "0", "", "1", "1", "0.95"]])
    with pytest.raises(SubmissionError, match="duplicate invoice id"):
        combine(template, [a, Source("b", twice)])
    bad_template = _file(tmp / "t2.csv", [["PA-1", "", "", "", "", ""], ["PA-1", "", "", "", "", ""]])
    with pytest.raises(SubmissionError, match="template repeats"):
        combine(bad_template, [a, b])


def test_bad_schema(world):
    tmp, template, (a, b) = world
    wrong = _file(tmp / "wrong.csv", [["MDS-1", "0", "", "1", "1"]], header="invoice_id,flagged,error_category,expected_total_cents,billed_total_cents\n")
    with pytest.raises(SubmissionError, match="columns"):
        combine(template, [a, Source("b", wrong)])
    ragged = _file(tmp / "ragged.csv", [["MDS-1", "0", "", "1", "1"]])
    with pytest.raises(SubmissionError, match="fields"):
        combine(template, [a, Source("b", ragged)])


def _row(**kw):
    row = dict(zip(COLUMNS, ["MDS-1", "0", "", "", "100", "0.75"]))
    row.update(kw)
    return row


@pytest.mark.parametrize("changes,message", [
    (dict(flagged="2"), "0 or 1"),
    (dict(flagged="1"), "without an error_category"),
    (dict(error_category="duplicate_charge"), "unflagged"),
    (dict(billed_total_cents="100.50"), "integer minor units"),
    (dict(billed_total_cents=""), "integer minor units"),
    (dict(expected_total_cents="1e3"), "integer minor units"),
    (dict(expected_total_cents="nan"), "not a valid value"),
    (dict(expected_total_cents="None"), "not a valid value"),
    (dict(confidence="1.5"), r"outside \[0, 1\]"),
    (dict(confidence="-0.1"), r"outside \[0, 1\]"),
    (dict(confidence="high"), "not a number"),
    (dict(confidence="nan"), "not a valid value"),
    (dict(invoice_id=" MDS-1"), "not a valid value"),
    (dict(invoice_id=""), "blank invoice_id"),
])
def test_invalid_rows_are_rejected_not_repaired(changes, message):
    with pytest.raises(SubmissionError, match=message):
        validate_row(_row(**changes), "row")


@pytest.mark.parametrize("changes", [dict(), dict(expected_total_cents="0"), dict(expected_total_cents="-500"), dict(confidence="0"),
                                     dict(confidence="1"), dict(flagged="1", error_category="x", expected_total_cents="")])
def test_valid_rows_pass(changes):
    validate_row(_row(**changes), "row")
