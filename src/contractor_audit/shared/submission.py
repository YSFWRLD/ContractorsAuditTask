"""The combined submission: every template row filled from its domain's frozen draft predictions.

Each domain's `run` writes `outputs/<domain>/draft_predictions.csv` in the template columns; that file is the
domain's frozen InvoiceResult per invoice. This module only joins them onto the upstream template, in the
template's order, after checking everything the README asks of a submission row. It never repairs a value: any
missing, duplicated, extra or malformed row stops it with an error that says what and where. Contract-neutral:
it knows the template, not the domains.
"""

import csv
import io
from collections import Counter
import math
import re
from dataclasses import dataclass
from pathlib import Path

COLUMNS = ["invoice_id", "flagged", "error_category", "expected_total_cents", "billed_total_cents", "confidence"]
FILENAME = "submission.csv"
_INT = re.compile(r"-?\d+")
_BAD_TEXT = {"nan", "none", "null", "inf", "-inf"}


class SubmissionError(ValueError):
    """The domain results cannot be combined into a valid submission as they stand."""


@dataclass(frozen=True)
class Source:
    domain: str
    path: Path


def _read(path: Path, what: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise SubmissionError(f"{what} not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise SubmissionError(f"{what} is empty: {path}") from None
        if header != COLUMNS:
            raise SubmissionError(f"{what} has columns {header}; expected {COLUMNS}: {path}")
        rows = []
        for n, row in enumerate(reader, start=2):
            if len(row) != len(COLUMNS):
                raise SubmissionError(f"{what} line {n}: {len(row)} fields, expected {len(COLUMNS)}: {path}")
            rows.append(dict(zip(COLUMNS, row)))
    return rows


def validate_row(row: dict[str, str], where: str) -> None:
    """The README's row rules; raises on the first violation."""
    for column, value in row.items():
        if value != value.strip() or value.strip().lower() in _BAD_TEXT:
            raise SubmissionError(f"{where}: {column} = {value!r} is not a valid value")
    if not row["invoice_id"]:
        raise SubmissionError(f"{where}: blank invoice_id")
    if row["flagged"] not in ("0", "1"):
        raise SubmissionError(f"{where}: flagged = {row['flagged']!r}, expected 0 or 1")
    if row["flagged"] == "1" and not row["error_category"]:
        raise SubmissionError(f"{where}: flagged without an error_category")
    if row["flagged"] == "0" and row["error_category"]:
        raise SubmissionError(f"{where}: error_category {row['error_category']!r} on an unflagged row")
    if not _INT.fullmatch(row["billed_total_cents"]):
        raise SubmissionError(f"{where}: billed_total_cents = {row['billed_total_cents']!r} is not integer minor units")
    if row["expected_total_cents"] and not _INT.fullmatch(row["expected_total_cents"]):
        raise SubmissionError(f"{where}: expected_total_cents = {row['expected_total_cents']!r} is not integer minor units (or blank)")
    try:
        confidence = float(row["confidence"])
    except ValueError:
        raise SubmissionError(f"{where}: confidence = {row['confidence']!r} is not a number") from None
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise SubmissionError(f"{where}: confidence {row['confidence']} outside [0, 1]")


def combine(template: Path, sources: list[Source]) -> list[dict[str, str]]:
    """Template rows filled from the domain rows, in template order; every row validated."""
    template_rows = _read(template, "submission template")
    template_ids = [r["invoice_id"] for r in template_rows]
    dup_template = sorted(i for i, n in Counter(template_ids).items() if n > 1)
    if dup_template:
        raise SubmissionError(f"the template repeats invoice ids: {dup_template[:10]}")
    results: dict[str, dict[str, str]] = {}
    origin: dict[str, str] = {}
    if not sources:
        raise SubmissionError("no domain results given")
    for source in sources:
        for n, row in enumerate(_read(source.path, f"{source.domain} results"), start=2):
            where = f"{source.domain} results line {n} ({row['invoice_id']})"
            validate_row(row, where)
            if row["invoice_id"] in results:
                raise SubmissionError(f"{where}: duplicate invoice id (also in {origin[row['invoice_id']]} results)")
            results[row["invoice_id"]] = row
            origin[row["invoice_id"]] = source.domain
    missing = [i for i in template_ids if i not in results]
    if missing:
        raise SubmissionError(f"{len(missing)} template invoice ids have no result, e.g. {missing[:10]}")
    extra = sorted(set(results) - set(template_ids))
    if extra:
        raise SubmissionError(f"{len(extra)} results are not template invoice ids, e.g. {extra[:10]}")
    return [results[i] for i in template_ids]


def render(rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    w.writerows([[r[c] for c in COLUMNS] for r in rows])
    return buf.getvalue()


def write(template: Path, sources: list[Source], out: Path) -> list[dict[str, str]]:
    rows = combine(template, sources)
    out.write_text(render(rows), encoding="utf-8", newline="\n")
    return rows
