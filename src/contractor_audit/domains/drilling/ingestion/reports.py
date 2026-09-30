"""Daily Drilling Report text -> DailyReport. Rig wording is kept verbatim; nothing is mapped to a service code.

Layout observed in the task files (see docs/drilling/phase2_data_inventory.md):

    DAILY DRILLING REPORT
    Report / Contract / Well / Rig / Date          header
    PART A — OPERATIONS SUMMARY ...                every report
    PART B — BHA RUN RECORD ...                    every report
    PART C / D / E ...                             only on some days
    Signed (<role>): <name>                        trailing signature block

The parser does not assume that layout holds: unknown sections or labels, duplicated labels, blank values,
non `Label: value` lines and missing fields become ParseIssues, and the affected value is None.
"""

import re
from pathlib import Path

from contractor_audit.domains.drilling.ingestion.models import (
    BhaRunRecord, CrewEntry, DailyReport, GyroSurveyRecord, LostInHoleRecord, OperationsSummary, ParseIssue, RawField,
    Severity, Signature, SourceHandlingRecord, SourceRef,
)
from contractor_audit.domains.drilling.ingestion.values import (
    is_blank_signature, parse_date, parse_int, parse_yes_no, split_list,
)

TITLE = "DAILY DRILLING REPORT"
PART_TITLES = {"A": "OPERATIONS SUMMARY", "B": "BHA RUN RECORD", "C": "GYRO SURVEY RECORD",
               "D": "RADIOACTIVE SOURCE HANDLING", "E": "LOST IN HOLE"}
_PART = re.compile(r"^PART ([A-Z]) — (.+)$")
_FIELD = re.compile(r"^([^:]+): ?(.*)$")
_SIGNED = re.compile(r"^Signed \((.+)\)$")
_CREW = re.compile(r"^(\d+) (.+)$")

# section -> label -> (kind, required)
SCHEMA: dict[str, dict[str, tuple[str, bool]]] = {
    "HEADER": {"Report": ("text", True), "Contract": ("text", True), "Well": ("text", True), "Rig": ("text", True), "Date": ("date", True)},
    "A": {"Hole section": ("text", True), "Status": ("text", True), "Depth start (m MD)": ("int", True), "Depth end (m MD)": ("int", True),
          "Circulating hours": ("int", True), "BHA run": ("int", True), "In the hole": ("list", True), "Crew on tour": ("crew", True),
          "Gyro surveys": ("int", True), "Pressure points": ("int", True), "Wiper trips": ("int", True),
          "Back-reaming hours": ("int", True), "Clean-out runs": ("int", True)},
    "B": {"Run": ("int", True), "Run first day": ("date", True), "Run last day": ("date", True), "Tools in run": ("list", True),
          "Run circulating hours": ("int", True), "Metres logged": ("int", True), "Metres reamed": ("int", True),
          "Radioactive source carried": ("yesno", True)},
    "C": {"Gyro surveys taken": ("int", True), "Surveyed section": ("text", True)},
    "D": {"Source run": ("int", True), "Sources handled": ("text", True), "Source handling certified": ("yesno", True)},
    "E": {"Lost in hole run": ("int", True), "Lost in hole tool": ("text", True), "Circulating hours accumulated on the well": ("int", True)},
}
EXPECTED_SIGNATORIES = ("Company Representative", "lead directional driller")


def parse_report_text(text: str, rel: str) -> DailyReport:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    issues: list[ParseIssue] = []
    fields: list[RawField] = []
    signatures: list[Signature] = []
    parts: list[str] = []
    report_id = None

    def src(line: int | None = None) -> SourceRef:
        return SourceRef(rel, line, report_id)

    def issue(code, message, line=None, field=None, raw=None, severity=Severity.WARNING):
        issues.append(ParseIssue(code, severity, message, src(line), field, raw))

    title = lines[0].strip() if lines else ""
    if title != TITLE:
        issue("UNEXPECTED_TITLE", f"first line is {title!r}, expected {TITLE!r}", 1, raw=title)
    section = "HEADER"
    for n, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        m = _PART.match(line)
        if m:
            letter, part_title = m.groups()
            if letter not in PART_TITLES:
                issue("UNKNOWN_SECTION", f"unknown part {letter}", n, raw=line)
            elif part_title != PART_TITLES[letter]:
                issue("SECTION_TITLE_MISMATCH", f"part {letter} titled {part_title!r}", n, raw=line)
            if letter in parts:
                issue("DUPLICATE_SECTION", f"part {letter} appears twice", n, raw=line)
            parts.append(letter)
            section = letter
            continue
        m = _FIELD.match(line)
        if not m:
            issue("MALFORMED_LINE", "line is not `Label: value`", n, raw=line)
            continue
        label, value = m.group(1).strip(), m.group(2).strip()
        signed = _SIGNED.match(label)
        if signed:
            fields.append(RawField("SIGNATURES", label, value, n))
            signatures.append(Signature(signed.group(1), None if is_blank_signature(value) else value, value))
            if is_blank_signature(value):
                issue("BLANK_SIGNATURE", f"{label} is blank", n, label, value, Severity.INFO)
            section = "SIGNATURES"
            continue
        if section == "SIGNATURES":
            issue("FIELD_AFTER_SIGNATURES", f"{label} follows the signature block", n, label, value)
        fields.append(RawField(section, label, value, n))
        if label == "Report" and section == "HEADER" and report_id is None:
            report_id = value or None

    # structural checks on the collected fields
    by_section: dict[str, dict[str, RawField]] = {}
    for f in fields:
        if f.section == "SIGNATURES":
            continue
        known = SCHEMA.get(f.section, {})
        if f.label not in known:
            issue("UNKNOWN_FIELD", f"unexpected label {f.label!r} in {f.section}", f.line, f.label, f.value)
        slot = by_section.setdefault(f.section, {})
        if f.label in slot:
            issue("DUPLICATE_LABEL", f"{f.label!r} repeated in {f.section}; the first value is used", f.line, f.label, f.value)
            continue
        slot[f.label] = f
        if f.value == "":
            issue("BLANK_VALUE", f"{f.label} is blank", f.line, f.label, "")
    for letter in ("A", "B"):
        if letter not in parts:
            issue("MISSING_SECTION", f"part {letter} is missing", severity=Severity.ERROR)
    for section, labels in SCHEMA.items():
        if section != "HEADER" and section not in parts:
            continue
        for label, (_, required) in labels.items():
            if required and label not in by_section.get(section, {}):
                issue("MISSING_FIELD", f"{label} missing from {section}", field=label)
    roles = [s.role for s in signatures]
    for role in EXPECTED_SIGNATORIES:
        if role not in roles:
            issue("MISSING_SIGNATURE_LINE", f"no signature line for {role}", field=role)
    for role in roles:
        if role not in EXPECTED_SIGNATORIES:
            issue("UNEXPECTED_SIGNATORY", f"signature line for {role!r}", field=role, severity=Severity.INFO)

    def get(section: str, label: str):
        f = by_section.get(section, {}).get(label)
        if f is None or f.value == "":
            return None
        kind = SCHEMA[section][label][0]
        if kind == "text":
            return f.value
        if kind == "list":
            return split_list(f.value)
        if kind == "crew":
            entries = []
            for item in split_list(f.value):
                cm = _CREW.match(item)
                if not cm:
                    issue("MALFORMED_CREW_ENTRY", f"crew entry {item!r} is not `<count> <role>`", f.line, label, item)
                entries.append(CrewEntry(int(cm.group(1)) if cm else None, cm.group(2) if cm else item, item))
            return tuple(entries)
        parser = {"int": parse_int, "date": parse_date, "yesno": parse_yes_no}[kind]
        value, problem = parser(f.value, src(f.line), label)
        if problem:
            issues.append(problem)
        return value

    ops = OperationsSummary(get("A", "Hole section"), get("A", "Status"), get("A", "Depth start (m MD)"), get("A", "Depth end (m MD)"),
                            get("A", "Circulating hours"), get("A", "BHA run"), get("A", "In the hole") or (), get("A", "Crew on tour") or (),
                            get("A", "Gyro surveys"), get("A", "Pressure points"), get("A", "Wiper trips"), get("A", "Back-reaming hours"),
                            get("A", "Clean-out runs")) if "A" in parts else None
    run = BhaRunRecord(get("B", "Run"), get("B", "Run first day"), get("B", "Run last day"), get("B", "Tools in run") or (),
                       get("B", "Run circulating hours"), get("B", "Metres logged"), get("B", "Metres reamed"),
                       get("B", "Radioactive source carried")) if "B" in parts else None
    gyro = GyroSurveyRecord(get("C", "Gyro surveys taken"), get("C", "Surveyed section")) if "C" in parts else None
    source = SourceHandlingRecord(get("D", "Source run"), get("D", "Sources handled"), get("D", "Source handling certified")) if "D" in parts else None
    lost = LostInHoleRecord(get("E", "Lost in hole run"), get("E", "Lost in hole tool"),
                            get("E", "Circulating hours accumulated on the well")) if "E" in parts else None
    return DailyReport(
        report_id=report_id, title=title, contract_ref=get("HEADER", "Contract"), well=get("HEADER", "Well"), rig=get("HEADER", "Rig"),
        date=get("HEADER", "Date"), parts=tuple(parts), operations=ops, bha_run=run, gyro=gyro, source_handling=source,
        lost_in_hole=lost, signatures=tuple(signatures), fields=tuple(fields), issues=tuple(issues), source=SourceRef(rel, None, report_id))


def load_reports(records_dir: Path, rel_dir: str) -> tuple[DailyReport, ...]:
    """Every `.txt` file directly under `records_dir`, in file-name order. A file that cannot be decoded is an ERROR report."""
    reports = []
    for path in sorted(p for p in records_dir.iterdir() if p.is_file()):
        rel = f"{rel_dir}/{path.name}"
        if path.suffix != ".txt":
            reports.append(_unreadable(rel, "UNEXPECTED_FILE", f"{path.name} is not a .txt report"))
            continue
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            reports.append(_unreadable(rel, "UNDECODABLE_FILE", f"not UTF-8: {exc}"))
            continue
        reports.append(parse_report_text(text, rel))
    return tuple(reports)


def _unreadable(rel: str, code: str, message: str) -> DailyReport:
    issue = ParseIssue(code, Severity.ERROR, message, SourceRef(rel, None, None))
    return DailyReport(None, "", None, None, None, None, (), None, None, None, None, None, (), (), (issue,), SourceRef(rel, None, None))
