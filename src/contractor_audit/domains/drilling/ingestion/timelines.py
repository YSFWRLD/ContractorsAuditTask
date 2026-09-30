"""Structural reconstruction of each well's days and BHA runs from the reports. No eligibility or pricing."""

from dataclasses import dataclass
from datetime import date, timedelta

from contractor_audit.domains.drilling.ingestion.indexes import DrillingIndexes


@dataclass(frozen=True)
class InvoicePeriod:
    invoice_no: str
    start: date | None
    end: date | None
    invoice_date: date | None


@dataclass(frozen=True)
class WellTimeline:
    well: str
    rigs: tuple[str, ...]                   # every rig named for the well, reports and invoices together
    fields: tuple[str, ...]
    well_classes_stated: tuple[str, ...]    # as the invoices state them
    report_ids: tuple[str, ...]             # ordered by report date
    dates: tuple[date, ...]
    first_date: date | None
    last_date: date | None
    gaps: tuple[tuple[date, date], ...]     # (first missing day, last missing day) between reports
    invoice_periods: tuple[InvoicePeriod, ...]
    overlapping_periods: tuple[tuple[str, str], ...]
    report_days_outside_periods: tuple[date, ...]
    period_days_without_report: tuple[date, ...]


@dataclass(frozen=True)
class BhaRun:
    well: str
    run: int
    report_ids: tuple[str, ...]
    recorded_first_days: tuple[date, ...]   # every distinct value Part B states for the run
    recorded_last_days: tuple[date, ...]
    observed_first: date
    observed_last: date
    observed_days: int
    contiguous: bool
    tools_as_recorded: tuple[tuple[str, ...], ...]
    hole_sections: tuple[str, ...]
    run_circulating_hours_recorded: tuple[int, ...]
    daily_circulating_hours_total: int | None
    discrepancies: tuple[str, ...]

    @property
    def recorded_first(self) -> date | None:
        return self.recorded_first_days[0] if len(self.recorded_first_days) == 1 else None

    @property
    def recorded_last(self) -> date | None:
        return self.recorded_last_days[0] if len(self.recorded_last_days) == 1 else None


def _days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def well_timelines(ix: DrillingIndexes) -> dict[str, WellTimeline]:
    wells = sorted(set(ix.reports_by_well.keys()) | set(ix.invoices_by_well.keys()))
    out = {}
    for well in wells:
        reports = sorted((r for r in ix.reports_by_well.get(well) if r.date), key=lambda r: (r.date, r.report_id or ""))
        invoices = sorted(ix.invoices_by_well.get(well), key=lambda i: (i.period_start or date.min, i.invoice_no))
        dates = tuple(r.date for r in reports)
        gaps = tuple((a + timedelta(days=1), b - timedelta(days=1)) for a, b in zip(dates, dates[1:]) if (b - a).days > 1)
        periods = tuple(InvoicePeriod(i.invoice_no, i.period_start, i.period_end, i.invoice_date) for i in invoices)
        covered = {d for p in periods if p.start and p.end for d in _days(p.start, p.end)}
        overlaps = tuple((a.invoice_no, b.invoice_no) for k, a in enumerate(periods) for b in periods[k + 1:]
                         if a.start and a.end and b.start and b.end and a.start <= b.end and b.start <= a.end)
        out[well] = WellTimeline(
            well=well,
            rigs=tuple(sorted({r.rig for r in reports if r.rig} | {i.rig for i in invoices})),
            fields=tuple(sorted({i.field for i in invoices})),
            well_classes_stated=tuple(sorted({i.well_class_stated for i in invoices})),
            report_ids=tuple(r.report_id for r in reports if r.report_id),
            dates=dates, first_date=dates[0] if dates else None, last_date=dates[-1] if dates else None, gaps=gaps,
            invoice_periods=periods, overlapping_periods=overlaps,
            report_days_outside_periods=tuple(sorted(set(dates) - covered)),
            period_days_without_report=tuple(sorted(covered - set(dates))))
    return out


def bha_runs(ix: DrillingIndexes) -> dict[tuple[str, int], BhaRun]:
    groups: dict[tuple[str, int], list] = {}
    for well in ix.reports_by_well.keys():
        for r in ix.reports_by_well.get(well):
            if r.bha_run and r.bha_run.run is not None and r.date:
                groups.setdefault((well, r.bha_run.run), []).append(r)
    out = {}
    for key in sorted(groups):
        reports = sorted(groups[key], key=lambda r: r.date)
        runs = [r.bha_run for r in reports]
        firsts = tuple(sorted({b.run_first_day for b in runs if b.run_first_day}))
        lasts = tuple(sorted({b.run_last_day for b in runs if b.run_last_day}))
        observed_first, observed_last = reports[0].date, reports[-1].date
        contiguous = (observed_last - observed_first).days + 1 == len(reports)
        run_hours = tuple(sorted({b.run_circulating_hours for b in runs if b.run_circulating_hours is not None}))
        daily = [r.operations.circulating_hours for r in reports if r.operations]
        daily_total = sum(daily) if daily and all(h is not None for h in daily) else None
        notes = []
        if len(firsts) != 1 or len(lasts) != 1:
            notes.append(f"Part B states {len(firsts)} first-day and {len(lasts)} last-day values across the run")
        if len(firsts) == 1 and firsts[0] != observed_first:
            notes.append(f"recorded first day {firsts[0]} but first report {observed_first}")
        if len(lasts) == 1 and lasts[0] != observed_last:
            notes.append(f"recorded last day {lasts[0]} but last report {observed_last}")
        if not contiguous:
            notes.append("reports for the run are not on consecutive days")
        if len(run_hours) == 1 and daily_total is not None and run_hours[0] != daily_total:
            notes.append(f"run circulating hours {run_hours[0]} but daily hours sum to {daily_total}")
        if len(run_hours) > 1:
            notes.append(f"run circulating hours stated differently across days: {run_hours}")
        tools = tuple(dict.fromkeys(b.tools_in_run for b in runs))
        if len(tools) > 1:
            notes.append("tools in run stated differently across days")
        out[key] = BhaRun(key[0], key[1], tuple(r.report_id for r in reports), firsts, lasts, observed_first, observed_last,
                          len(reports), contiguous, tools, tuple(sorted({r.operations.hole_section for r in reports if r.operations and r.operations.hole_section})),
                          run_hours, daily_total, tuple(notes))
    return out
