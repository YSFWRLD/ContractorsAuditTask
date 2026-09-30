"""Structural validation of the drilling dataset.

Every result is an *observation* about the shape and consistency of the source data. None is a billing
finding: whether an observation matters contractually is decided by the audit phase, not here.
"""

import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from contractor_audit.domains.drilling.ingestion.indexes import DrillingIndexes, build_indexes
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset, Severity
from contractor_audit.domains.drilling.ingestion.timelines import BhaRun, WellTimeline, bha_runs, well_timelines


@dataclass(frozen=True)
class Observation:
    code: str
    category: str       # identity | reference | consistency | timing | report | arithmetic | parse
    severity: Severity
    subject: tuple[str, ...]
    message: str
    evidence: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StructuralReport:
    observations: tuple[Observation, ...]
    counts: dict
    variants: dict
    timelines: dict[str, WellTimeline]
    runs: dict[tuple[str, int], BhaRun]

    def by_code(self) -> dict[str, tuple[Observation, ...]]:
        out: dict[str, list] = {}
        for o in self.observations:
            out.setdefault(o.code, []).append(o)
        return {k: tuple(out[k]) for k in sorted(out)}


def validate(ds: DrillingDataset, ix: DrillingIndexes | None = None) -> StructuralReport:
    ix = ix or build_indexes(ds)
    obs: list[Observation] = []

    def add(code, category, severity, subject, message, **evidence):
        obs.append(Observation(code, category, severity, tuple(subject), message, evidence))

    # ------------------------------------------------------------------ parse issues
    for i in ds.issues:
        if i.code == "BLANK_SIGNATURE":
            continue  # reported once per report as BLANK_SIGNATURE below
        add(f"PARSE_{i.code}", "parse", i.severity, [x for x in (i.source.record_id, i.source.file) if x], i.message,
            file=i.source.file, line=i.source.line, field=i.field, raw=i.raw)

    # ------------------------------------------------------------------ identity
    for name, index in (("DUPLICATE_INVOICE_ID", ix.invoices_by_id), ("DUPLICATE_LINE_ID", ix.lines_by_id),
                        ("DUPLICATE_REPORT_ID", ix.reports_by_id), ("DUPLICATE_REPORT_WELL_DATE", ix.reports_by_well_and_date)):
        for key, members in index.duplicates().items():
            add(name, "identity", Severity.WARNING, [str(key)], f"{len(members)} records share {key}",
                sources=[m.source.file + (f":{m.source.line}" if m.source.line else "") for m in members])
    for r in ix.reports_by_id.unkeyed:
        add("REPORT_WITHOUT_ID", "identity", Severity.WARNING, [r.source.file], "report has no Report: value")
    for r in ds.reports:
        if r.report_id and r.well and r.date:
            number = r.well.rsplit("-", 1)[-1]
            if r.report_id != f"DDR-{number}-{r.date:%Y%m%d}":
                add("REPORT_ID_PATTERN_MISMATCH", "identity", Severity.INFO, [r.report_id], "Report id does not follow DDR-<well number>-<yyyymmdd>", well=r.well, date=str(r.date))
            expected_file = f"DDR_{r.well}_{r.date:%Y%m%d}.txt"
            if not r.source.file.endswith("/" + expected_file):
                add("REPORT_FILENAME_MISMATCH", "identity", Severity.INFO, [r.report_id], "file name does not match Well and Date", file=r.source.file)
    for inv in ds.invoices:
        lines = ix.lines_by_invoice.get(inv.invoice_no)
        if [l.line_no for l in lines] != list(range(1, len(lines) + 1)):
            add("LINE_NUMBERS_NOT_SEQUENTIAL", "identity", Severity.INFO, [inv.invoice_no], "line_no is not 1..n")
        for l in lines:
            if l.line_no is not None and l.line_ref != f"{l.invoice_no}-{l.line_no:03d}":
                add("LINE_REF_PATTERN_MISMATCH", "identity", Severity.INFO, [l.line_ref], "line_ref is not <invoice>-<line_no:03>")

    # ------------------------------------------------------------------ references
    for l in ds.lines:
        if l.invoice_no not in ix.invoices_by_id:
            add("LINE_INVOICE_MISSING", "reference", Severity.WARNING, [l.line_ref], f"invoice {l.invoice_no} not in invoices.csv")
        if l.report_ref is None:
            add("LINE_WITHOUT_REPORT_REF", "reference", Severity.INFO, [l.line_ref], f"{l.service_code} line carries no report reference",
                service_code=l.service_code, unit=l.unit)
        elif l.report_ref not in ix.reports_by_id:
            add("LINE_REPORT_REF_MISSING", "reference", Severity.WARNING, [l.line_ref], f"report {l.report_ref} not found", service_code=l.service_code)
    for inv in ds.invoices:
        if not ix.lines_by_invoice.get(inv.invoice_no):
            add("INVOICE_WITHOUT_LINES", "reference", Severity.WARNING, [inv.invoice_no], "invoice has no lines")
    for rid in ix.reports_by_id.keys():
        users = ix.lines_by_report_ref.get(rid)
        invoices = sorted({l.invoice_no for l in users})
        if not users:
            add("REPORT_NOT_REFERENCED", "reference", Severity.INFO, [rid], "no invoice line cites the report")
        elif len(invoices) > 1:
            add("REPORT_REFERENCED_BY_MULTIPLE_INVOICES", "reference", Severity.WARNING, [rid], f"cited by {len(invoices)} invoices",
                invoices=invoices, lines=[f"{l.line_ref} {l.service_code} {l.service_date}" for l in users if l.invoice_no != invoices[0]])
    for (rid, code), members in ix.lines_by_report_and_code.duplicates().items():
        intervals = {(m.depth_from_m, m.depth_to_m) for m in members}
        distinct = len(intervals) == len(members) and None not in {x for iv in intervals for x in iv}
        add("REPEATED_REPORT_AND_CODE", "reference", Severity.INFO if distinct else Severity.WARNING, [rid, code],
            f"{len(members)} lines cite {rid} for {code}" + (" with distinct depth intervals" if distinct else " without distinct depth intervals"),
            lines=[m.line_ref for m in members], invoices=sorted({m.invoice_no for m in members}), distinct_depth_intervals=distinct)

    # ------------------------------------------------------------------ consistency
    contract_refs = Counter(i.contract_ref for i in ds.invoices)
    usual = contract_refs.most_common(1)[0][0] if contract_refs else None
    report_refs = Counter(r.contract_ref for r in ds.reports if r.contract_ref)
    for inv in ds.invoices:
        if inv.contract_ref != usual:
            add("CONTRACT_REF_VARIANT", "consistency", Severity.WARNING, [inv.invoice_no],
                f"contract_ref {inv.contract_ref!r} differs from {usual!r} ({contract_refs[usual]} invoices, and every report: {dict(report_refs)})",
                raw=inv.contract_ref)
    for r in ds.reports:
        if r.contract_ref and r.contract_ref != usual:
            add("REPORT_CONTRACT_VARIANT", "consistency", Severity.WARNING, [r.report_id or r.source.file], f"Contract {r.contract_ref!r}")
    contractors = Counter(i.contractor for i in ds.invoices)
    for inv in ds.invoices:
        if len(contractors) > 1 and inv.contractor != contractors.most_common(1)[0][0]:
            add("CONTRACTOR_VARIANT", "consistency", Severity.WARNING, [inv.invoice_no], f"contractor {inv.contractor!r}")
    for l in ds.lines:
        inv = ix.invoices_by_id.get(l.invoice_no)
        if inv and l.well_name != inv[0].well_name:
            add("LINE_WELL_DIFFERS_FROM_INVOICE", "consistency", Severity.WARNING, [l.line_ref], f"{l.well_name} vs {inv[0].well_name}")
        reports = ix.reports_by_id.get(l.report_ref) if l.report_ref else ()
        if len(reports) == 1:
            r = reports[0]
            if r.well != l.well_name:
                add("LINE_WELL_DIFFERS_FROM_REPORT", "consistency", Severity.WARNING, [l.line_ref], f"line {l.well_name}, report {r.well}")
            if l.service_date and r.date and l.service_date != r.date:
                add("LINE_DATE_DIFFERS_FROM_REPORT", "consistency", Severity.WARNING, [l.line_ref, r.report_id],
                    f"service date {l.service_date} but report dated {r.date}", service_code=l.service_code, invoice=l.invoice_no)
            if r.operations and l.hole_section and r.operations.hole_section != l.hole_section:
                add("LINE_SECTION_DIFFERS_FROM_REPORT", "consistency", Severity.WARNING, [l.line_ref], f"{l.hole_section} vs {r.operations.hole_section}")
            if r.operations and l.day_status and r.operations.status != l.day_status:
                add("LINE_STATUS_DIFFERS_FROM_REPORT", "consistency", Severity.WARNING, [l.line_ref], f"{l.day_status} vs {r.operations.status}")
            if inv and r.rig and r.rig != inv[0].rig:
                add("INVOICE_RIG_DIFFERS_FROM_REPORT", "consistency", Severity.WARNING, [l.invoice_no, r.report_id], f"{inv[0].rig} vs {r.rig}")
    timelines = well_timelines(ix)
    for well, t in timelines.items():
        if len(t.rigs) > 1:
            add("WELL_HAS_SEVERAL_RIGS", "consistency", Severity.WARNING, [well], f"rigs {t.rigs}")
        if len(t.well_classes_stated) > 1:
            add("WELL_CLASS_STATED_DIFFERENTLY", "consistency", Severity.WARNING, [well], f"invoices state {t.well_classes_stated}")
        if not t.dates:
            add("WELL_WITHOUT_REPORTS", "consistency", Severity.WARNING, [well], "invoices exist but no report")
        if not t.invoice_periods:
            add("WELL_WITHOUT_INVOICES", "consistency", Severity.INFO, [well], "reports exist but no invoice")

    # ------------------------------------------------------------------ timing (shape only; no contractual window is applied)
    for inv in ds.invoices:
        if inv.period_start and inv.period_end and inv.period_start > inv.period_end:
            add("PERIOD_START_AFTER_END", "timing", Severity.WARNING, [inv.invoice_no], f"{inv.period_start} > {inv.period_end}")
        if inv.invoice_date and inv.period_end and inv.invoice_date < inv.period_end:
            add("INVOICE_DATED_BEFORE_PERIOD_END", "timing", Severity.WARNING, [inv.invoice_no],
                f"invoice dated {inv.invoice_date}, period ends {inv.period_end}")
    for l in ds.lines:
        inv = ix.invoices_by_id.get(l.invoice_no)
        if inv and l.service_date and inv[0].period_start and inv[0].period_end and not inv[0].period_start <= l.service_date <= inv[0].period_end:
            add("LINE_DATE_OUTSIDE_INVOICE_PERIOD", "timing", Severity.WARNING, [l.line_ref],
                f"service date {l.service_date} outside {inv[0].period_start}..{inv[0].period_end}", service_code=l.service_code)
    for well, t in timelines.items():
        for a, b in t.overlapping_periods:
            add("INVOICE_PERIODS_OVERLAP", "timing", Severity.WARNING, [well, a, b], f"periods of {a} and {b} overlap")
        for d in t.report_days_outside_periods:
            add("REPORT_DAY_OUTSIDE_INVOICE_PERIODS", "timing", Severity.INFO, [well, str(d)], "no invoice period covers the report day")
        for start, end in t.gaps:
            add("REPORT_GAP", "timing", Severity.INFO, [well], f"no reports from {start} to {end}")
        by_invoice = Counter()
        dates = set(t.dates)
        for p in t.invoice_periods:
            if p.start and p.end:
                missing = [d for d in _span(p.start, p.end) if d not in dates]
                if missing:
                    add("PERIOD_DAYS_WITHOUT_REPORT", "timing", Severity.INFO, [p.invoice_no], f"{len(missing)} day(s) of the period have no report",
                        first=str(missing[0]), last=str(missing[-1]), days=len(missing), well_last_report=str(t.last_date))
                    by_invoice[p.invoice_no] += len(missing)
        del by_invoice

    # ------------------------------------------------------------------ report-internal consistency
    for r in ds.reports:
        rid = r.report_id or r.source.file
        a, b = r.operations, r.bha_run
        if a and b and a.bha_run != b.run:
            add("PART_A_RUN_DIFFERS_FROM_PART_B", "report", Severity.WARNING, [rid], f"A {a.bha_run} vs B {b.run}")
        if a and b and a.in_the_hole != b.tools_in_run:
            add("TOOLS_IN_RUN_DIFFER_FROM_IN_THE_HOLE", "report", Severity.INFO, [rid], "Part B tools differ from Part A in the hole")
        if b and r.date and b.run_first_day and b.run_last_day and not b.run_first_day <= r.date <= b.run_last_day:
            add("REPORT_DATE_OUTSIDE_STATED_RUN", "report", Severity.WARNING, [rid], f"{r.date} outside {b.run_first_day}..{b.run_last_day}")
        if a and a.depth_start_m is not None and a.depth_end_m is not None and a.depth_end_m < a.depth_start_m:
            add("DEPTH_DECREASES", "report", Severity.WARNING, [rid], f"{a.depth_start_m} -> {a.depth_end_m}")
        if a and a.gyro_surveys is not None:
            has_c = r.gyro is not None
            if has_c != (a.gyro_surveys > 0):
                add("PART_C_PRESENCE_VS_GYRO_COUNT", "report", Severity.WARNING, [rid],
                    f"Part A records {a.gyro_surveys} gyro survey(s); Part C {'present' if has_c else 'absent'}")
            elif has_c and r.gyro.surveys_taken != a.gyro_surveys:
                add("PART_C_COUNT_DIFFERS_FROM_PART_A", "report", Severity.WARNING, [rid], f"{r.gyro.surveys_taken} vs {a.gyro_surveys}")
        if r.gyro and a and r.gyro.surveyed_section != a.hole_section:
            add("PART_C_SECTION_DIFFERS", "report", Severity.INFO, [rid], f"{r.gyro.surveyed_section} vs {a.hole_section}")
        if r.source_handling and b and b.radioactive_source_carried is False:
            add("PART_D_WITHOUT_SOURCE_FLAG", "report", Severity.WARNING, [rid], "Part D present but Part B says no source carried")
        if r.source_handling and b and r.source_handling.source_run != b.run:
            add("PART_D_RUN_DIFFERS", "report", Severity.WARNING, [rid], f"{r.source_handling.source_run} vs {b.run}")
        if r.lost_in_hole and b and r.lost_in_hole.run != b.run:
            add("PART_E_RUN_DIFFERS", "report", Severity.WARNING, [rid], f"{r.lost_in_hole.run} vs {b.run}")
        if r.lost_in_hole and a and r.lost_in_hole.tool not in a.in_the_hole:
            add("PART_E_TOOL_NOT_IN_THE_HOLE", "report", Severity.WARNING, [rid], f"{r.lost_in_hole.tool!r} not listed in the hole")
        if any(s.blank for s in r.signatures):
            add("BLANK_SIGNATURE", "report", Severity.WARNING, [rid], "blank: " + ", ".join(s.role for s in r.signatures if s.blank))
    for well, t in timelines.items():
        reports = [ix.reports_by_well_and_date.get((well, d)) for d in t.dates]
        chain = [rs[0] for rs in reports if len(rs) == 1]
        for prev, nxt in zip(chain, chain[1:]):
            if prev.operations and nxt.operations and prev.operations.depth_end_m != nxt.operations.depth_start_m:
                add("DEPTH_DISCONTINUITY", "report", Severity.INFO, [prev.report_id, nxt.report_id],
                    f"{prev.operations.depth_end_m} then {nxt.operations.depth_start_m}")
    runs = bha_runs(ix)
    for key, run in runs.items():
        for note in run.discrepancies:
            add("BHA_RUN_DISCREPANCY", "report", Severity.INFO, [f"{key[0]} run {key[1]}"], note)
    for well, t in timelines.items():
        numbers = sorted(n for (w, n) in runs if w == well)
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            add("BHA_RUN_NUMBERS_NOT_CONSECUTIVE", "report", Severity.INFO, [well], f"runs {numbers}")

    # ------------------------------------------------------------------ recorded arithmetic (descriptive only)
    for l in ds.lines:
        if l.quantity is not None and l.unit_rate is not None and l.amount_cents is not None and l.quantity * l.unit_rate * 100 != l.amount_cents:
            add("LINE_AMOUNT_NOT_QUANTITY_TIMES_RATE", "arithmetic", Severity.INFO, [l.line_ref],
                "stated amount differs from stated quantity x stated rate", quantity=str(l.quantity), unit_rate=str(l.unit_rate), amount=l.raw_value("amount"))
    for inv in ds.invoices:
        lines = ix.lines_by_invoice.get(inv.invoice_no)
        if inv.net_cents is not None and all(l.amount_cents is not None for l in lines) and sum(l.amount_cents for l in lines) != inv.net_cents:
            add("NET_NOT_SUM_OF_LINES", "arithmetic", Severity.INFO, [inv.invoice_no], "net_amount differs from the sum of line amounts")
        if None not in (inv.net_cents, inv.vat_cents, inv.total_cents) and inv.net_cents + inv.vat_cents != inv.total_cents:
            add("TOTAL_NOT_NET_PLUS_VAT", "arithmetic", Severity.INFO, [inv.invoice_no], "invoice_total differs from net_amount + vat_amount",
                net=inv.raw_value("net_amount"), vat=inv.raw_value("vat_amount"), total=inv.raw_value("invoice_total"))
        if inv.adjustment_cents:
            add("NONZERO_ADJUSTMENT", "arithmetic", Severity.INFO, [inv.invoice_no], f"adjustment {inv.raw_value('adjustment')}")

    lags = sorted((i.invoice_date - i.period_end).days for i in ds.invoices if i.invoice_date and i.period_end)
    counts = {
        "invoices": len(ds.invoices), "lines": len(ds.lines), "reports": len(ds.reports),
        "wells": len(timelines), "bha_runs": len(runs), "parse_issues": len(ds.issues),
        "parse_issues_by_severity": dict(sorted(Counter(i.severity.value for i in ds.issues).items())),
        "invoice_date_minus_period_end_days": {"min": lags[0], "median": statistics.median(lags), "max": lags[-1]} if lags else None,
        "service_dates": [str(min(l.service_date for l in ds.lines if l.service_date)), str(max(l.service_date for l in ds.lines if l.service_date))] if ds.lines else None,
        "report_dates": [str(min(r.date for r in ds.reports if r.date)), str(max(r.date for r in ds.reports if r.date))] if ds.reports else None,
    }
    variants = dict(sorted(Counter(r.variant for r in ds.reports).items(), key=lambda kv: (-kv[1], kv[0])))
    ordered = tuple(sorted(obs, key=lambda o: (o.category, o.code, o.subject)))
    return StructuralReport(ordered, counts, variants, timelines, runs)


def _span(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d = date.fromordinal(d.toordinal() + 1)
