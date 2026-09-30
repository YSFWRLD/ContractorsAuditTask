"""Parser for civilwork/records/*.txt site records.

A record is a title line, a block of `Key: value` headers, a free-text body
written in the site's own words, and two signature lines. The body is kept
verbatim: interpreting it (quantities, which item it evidences) belongs to a
later phase. Anything unexpected becomes a RecordIssue rather than an exception,
so one odd file never hides the other 2,168.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

# Reference prefix -> title printed on the record (Schedule 5 names the same series).
RECORD_TYPES: dict[str, str] = {
    "CT": "COMPACTION TEST CERTIFICATE",
    "CV": "CCTV SURVEY REPORT",
    "DW": "DEWATERING LOG",
    "DX": "DAILY EXCAVATION RECORD",
    "JS": "JOINT SURVEY SHEET",
    "MO": "METEOROLOGICAL RECORD",
    "PR": "CONCRETE POUR RECORD",
    "PS": "PLANT STANDING RECORD",
    "PT": "PRESSURE TEST CERTIFICATE",
}
WEEKLY_TYPES = {"DW"}

FOREMAN_KEY = "Signed (foreman)"
ENGINEER_KEY = "Countersigned (Engineer's representative)"
HEADER_KEYS = ("Ticket", "Job", "Area", "Date", "Ground", "Week beginning", "Days on")
_KEY_LINE = re.compile(r"^(?P<key>[A-Za-z' ()]+):[ \t]*(?P<value>.*)$")
_DAY_ON = re.compile(r"^(?P<dow>[A-Z][a-z]{2}) (?P<day>\d{2})/(?P<month>\d{2})$")
_TICKET = re.compile(r"^(?P<prefix>[A-Z]{2})-\d{5}$")
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class RecordIssue:
    source_file: str
    code: str
    message: str


@dataclass(frozen=True)
class Signature:
    present: bool          # the signature line exists in the record
    name: str | None       # None when the line is absent or left blank (e.g. "______")

    @property
    def signed(self) -> bool:
        return self.name is not None


@dataclass(frozen=True)
class SiteRecord:
    source_file: str
    ticket: str | None
    record_type: str | None          # reference prefix, e.g. "DX"
    title: str | None
    job: str | None
    area: str | None
    date: date | None                # single-day records
    week_beginning: date | None      # weekly records (DW)
    days_on: tuple[date, ...]        # weekly records (DW)
    ground: str | None               # DX and PT records state a ground class
    description: str                 # verbatim free-text body
    foreman: Signature
    engineer_rep: Signature
    headers: dict[str, str] = field(repr=False)
    raw_text: str = field(repr=False)

    @property
    def work_dates(self) -> tuple[date, ...]:
        if self.date is not None:
            return (self.date,)
        return self.days_on


@dataclass
class RecordSet:
    records: list[SiteRecord]
    issues: list[RecordIssue]

    def by_ticket(self) -> dict[str, SiteRecord]:
        """First record per ticket; duplicates are reported by the inventory, not silently merged."""
        out: dict[str, SiteRecord] = {}
        for rec in self.records:
            if rec.ticket and rec.ticket not in out:
                out[rec.ticket] = rec
        return out


def _parse_dmy(text: str) -> date:
    return datetime.strptime(text.strip(), "%d/%m/%Y").date()


def _signature(value: str | None) -> Signature:
    if value is None:
        return Signature(present=False, name=None)
    name = value.strip()
    if not name or set(name) <= {"_", "-", "."}:
        return Signature(present=True, name=None)
    return Signature(present=True, name=name)


def _resolve_days_on(text: str, week_beginning: date, issue) -> tuple[date, ...]:
    """'Tue 04/02, Wed 05/02' -> dates inside the 7 days starting at week_beginning (the year is not printed)."""
    window = {(d.day, d.month): d for d in (week_beginning + timedelta(n) for n in range(7))}
    days = []
    for part in (p.strip() for p in text.split(",")):
        m = _DAY_ON.match(part)
        if not m:
            issue("days_on_unparsed", f"cannot parse day {part!r}")
            continue
        resolved = window.get((int(m["day"]), int(m["month"])))
        if resolved is None:
            issue("days_on_outside_week", f"{part!r} is not within the week beginning {week_beginning}")
            continue
        if _WEEKDAYS[resolved.weekday()] != m["dow"]:
            issue("days_on_weekday_mismatch", f"{part!r} but {resolved} is a {_WEEKDAYS[resolved.weekday()]}")
        days.append(resolved)
    if len(set(days)) != len(days):
        issue("days_on_duplicate", f"a day is listed twice in {text!r}")
    return tuple(days)


def parse_record(text: str, source_file: str) -> tuple[SiteRecord, list[RecordIssue]]:
    issues: list[RecordIssue] = []

    def issue(code: str, message: str) -> None:
        issues.append(RecordIssue(source_file, code, message))

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    title = lines[0].strip() if lines and lines[0].strip() else None
    headers: dict[str, str] = {}
    signatures: dict[str, str] = {}
    body: list[str] = []
    for line in lines[1:]:
        m = _KEY_LINE.match(line)
        key = m["key"] if m else None
        if key in (FOREMAN_KEY, ENGINEER_KEY):
            if key in signatures:
                issue("duplicate_signature_line", f"{key!r} appears twice")
            signatures[key] = m["value"]
        elif key in HEADER_KEYS and not body:
            if key in headers:
                issue("duplicate_header", f"{key!r} appears twice")
            headers[key] = m["value"].strip()
        elif line.strip():
            body.append(line.strip())

    ticket = headers.get("Ticket") or None
    stem = Path(source_file).stem
    record_type = None
    if ticket is None:
        issue("missing_ticket", "no Ticket header")
    elif not _TICKET.match(ticket):
        issue("bad_ticket", f"ticket {ticket!r} is not of the form XX-00000")
    else:
        record_type = ticket[:2]
        if ticket != stem:
            issue("ticket_filename_mismatch", f"ticket {ticket!r} in file {source_file!r}")
    if record_type is None and _TICKET.match(stem):
        record_type = stem[:2]

    if title is None:
        issue("missing_title", "first line is blank")
    elif record_type in RECORD_TYPES and title != RECORD_TYPES[record_type]:
        issue("title_type_mismatch", f"title {title!r} does not match reference series {record_type}")
    if record_type is not None and record_type not in RECORD_TYPES:
        issue("unknown_record_type", f"reference series {record_type!r} is not a known record type")

    for key in ("Job", "Area"):
        if not headers.get(key):
            issue(f"missing_{key.lower()}", f"no {key} header")

    rec_date = week_beginning = None
    days_on: tuple[date, ...] = ()
    if record_type in WEEKLY_TYPES:
        if "Week beginning" not in headers:
            issue("missing_week_beginning", "weekly record without 'Week beginning'")
        else:
            try:
                week_beginning = _parse_dmy(headers["Week beginning"])
            except ValueError:
                issue("bad_date", f"cannot parse week beginning {headers['Week beginning']!r}")
        if "Days on" not in headers:
            issue("missing_days_on", "weekly record without 'Days on'")
        elif week_beginning is not None:
            days_on = _resolve_days_on(headers["Days on"], week_beginning, issue)
    elif "Date" not in headers:
        issue("missing_date", "no Date header")
    else:
        try:
            rec_date = _parse_dmy(headers["Date"])
        except ValueError:
            issue("bad_date", f"cannot parse date {headers['Date']!r}")

    foreman = _signature(signatures.get(FOREMAN_KEY))
    engineer = _signature(signatures.get(ENGINEER_KEY))
    for sig, label in ((foreman, "foreman"), (engineer, "engineer_rep")):
        if not sig.present:
            issue(f"missing_{label}_signature_line", f"no {label} signature line")
        elif not sig.signed:
            issue(f"unsigned_{label}", f"{label} signature line is blank")

    if not body:
        issue("empty_description", "no free-text description")
    elif len(body) > 1:
        issue("multi_line_description", f"description spans {len(body)} lines")

    record = SiteRecord(
        source_file=source_file,
        ticket=ticket,
        record_type=record_type,
        title=title,
        job=headers.get("Job") or None,
        area=headers.get("Area") or None,
        date=rec_date,
        week_beginning=week_beginning,
        days_on=days_on,
        ground=headers.get("Ground") or None,
        description="\n".join(body),
        foreman=foreman,
        engineer_rep=engineer,
        headers=headers,
        raw_text=text,
    )
    return record, issues


def load_records(records_dir: Path) -> RecordSet:
    records: list[SiteRecord] = []
    issues: list[RecordIssue] = []
    for path in sorted(records_dir.glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            issues.append(RecordIssue(path.name, "not_utf8", str(exc)))
            continue
        record, record_issues = parse_record(text, path.name)
        records.append(record)
        issues.extend(record_issues)
    return RecordSet(records, issues)
