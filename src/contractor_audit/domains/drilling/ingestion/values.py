"""Strict value parsers for drilling sources. Each returns (value, issue); a bad value becomes None plus an issue."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from contractor_audit.domains.drilling.ingestion.models import ParseIssue, Severity, SourceRef
from contractor_audit.shared.money import parse_amount, to_minor_units

_MONTHS = {m: i + 1 for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"))}
_DATE = re.compile(r"^(\d{2})-([A-Z][a-z]{2})-(\d{4})$")
_INT = re.compile(r"^-?\d+$")
_MONEY = re.compile(r"^-?\d+\.\d{2}$")
_BLANK_SIGNATURE = re.compile(r"^_*$")


def _issue(code, message, source, field, raw, severity=Severity.WARNING):
    return ParseIssue(code, severity, message, source, field, raw)


def parse_date(raw: str, source: SourceRef, field: str, *, nullable: bool = False):
    """DD-Mon-YYYY with English month abbreviations, independent of the locale."""
    if raw == "":
        return None, None if nullable else _issue("BLANK_VALUE", f"{field} is blank", source, field, raw)
    m = _DATE.match(raw)
    if not m or m.group(2) not in _MONTHS:
        return None, _issue("MALFORMED_DATE", f"{field} {raw!r} is not DD-Mon-YYYY", source, field, raw)
    try:
        return date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1))), None
    except ValueError:
        return None, _issue("IMPOSSIBLE_DATE", f"{field} {raw!r} is not a calendar date", source, field, raw)


def parse_int(raw: str, source: SourceRef, field: str, *, nullable: bool = False):
    if raw == "":
        return None, None if nullable else _issue("BLANK_VALUE", f"{field} is blank", source, field, raw)
    if not _INT.match(raw):
        return None, _issue("MALFORMED_NUMBER", f"{field} {raw!r} is not a whole number", source, field, raw)
    return int(raw), None


def parse_decimal(raw: str, source: SourceRef, field: str):
    if raw == "":
        return None, _issue("BLANK_VALUE", f"{field} is blank", source, field, raw)
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None, _issue("MALFORMED_NUMBER", f"{field} {raw!r} is not a number", source, field, raw)
    if not value.is_finite():
        return None, _issue("MALFORMED_NUMBER", f"{field} {raw!r} is not finite", source, field, raw)
    return value, None


def parse_cents(raw: str, source: SourceRef, field: str):
    """Money printed with exactly two decimals -> integer cents. Never rounds."""
    if raw == "":
        return None, _issue("BLANK_VALUE", f"{field} is blank", source, field, raw)
    if not _MONEY.match(raw):
        return None, _issue("MALFORMED_MONEY", f"{field} {raw!r} is not an amount with two decimals", source, field, raw)
    return to_minor_units(parse_amount(raw)), None


def parse_yes_no(raw: str, source: SourceRef, field: str):
    if raw in ("Yes", "No"):
        return raw == "Yes", None
    if raw == "":
        return None, _issue("BLANK_VALUE", f"{field} is blank", source, field, raw)
    return None, _issue("UNEXPECTED_VALUE", f"{field} {raw!r} is not Yes/No", source, field, raw)


def split_list(raw: str) -> tuple[str, ...]:
    """Comma-separated rig words, verbatim and in printed order."""
    return tuple(item.strip() for item in raw.split(",")) if raw.strip() else ()


def is_blank_signature(raw: str) -> bool:
    return bool(_BLANK_SIGNATURE.match(raw.strip()))
