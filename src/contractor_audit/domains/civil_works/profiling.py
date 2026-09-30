"""Descriptive profiles of the civil works sources.

These functions count and cross-tabulate; they do not decide that anything is wrong.
Where a comparison against the contract is shown (unit, description, record series),
it is reported as agreement counts, not as findings.
"""

import re
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import ROUND_FLOOR, Decimal

from contractor_audit.domains.civil_works.contract import ContractTerms
from contractor_audit.domains.civil_works.models import Application, ApplicationLine
from contractor_audit.domains.civil_works.records import RECORD_TYPES, RecordSet

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _summary(values: list) -> dict:
    if not values:
        return {"count": 0}
    return {"count": len(values), "min": min(values), "median": statistics.median(values), "max": max(values)}


def _cents_str(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100}.{abs(cents) % 100:02d}"


def _money_summary(cents: list[int]) -> dict:
    if not cents:
        return {"count": 0}
    return {"count": len(cents), "min": _cents_str(min(cents)), "median": _cents_str(int(statistics.median(cents))),
            "max": _cents_str(max(cents)), "sum": _cents_str(sum(cents))}


def description_pattern(text: str) -> str:
    """The description with every number replaced by N, so phrasing variants can be counted."""
    return _NUMBER.sub("N", text)


# --------------------------------------------------------------------------- records

def record_inventory(record_set: RecordSet) -> dict:
    records = record_set.records
    by_type: dict[str, list] = defaultdict(list)
    for rec in records:
        by_type[rec.record_type or "?"].append(rec)
    tickets = Counter(r.ticket for r in records if r.ticket)
    duplicate_tickets = sorted(t for t, n in tickets.items() if n > 1)
    issue_codes = Counter(i.code for i in record_set.issues)
    issues_by_code: dict[str, list[str]] = defaultdict(list)
    for issue in record_set.issues:
        issues_by_code[issue.code].append(f"{issue.source_file}: {issue.message}")

    types = {}
    for prefix in sorted(by_type):
        recs = by_type[prefix]
        patterns = Counter(description_pattern(r.description) for r in recs)
        examples = {}
        for r in recs:
            examples.setdefault(description_pattern(r.description), r.description)
        dates = [d for r in recs for d in r.work_dates]
        types[prefix] = {
            "title": RECORD_TYPES.get(prefix),
            "count": len(recs),
            "date_range": [min(dates).isoformat(), max(dates).isoformat()] if dates else None,
            "areas": dict(Counter(r.area for r in recs).most_common()),
            "ground": dict(Counter(r.ground for r in recs if r.ground).most_common()),
            "description_patterns": [{"pattern": p, "count": n, "example": examples[p]} for p, n in patterns.most_common()],
            "weekday_of_date": dict(Counter(WEEKDAYS[d.weekday()] for d in dates)),
        }
        if prefix == "DW":
            types[prefix]["days_on_count"] = dict(sorted(Counter(len(r.days_on) for r in recs).items()))
            types[prefix]["week_beginning_weekday"] = dict(Counter(WEEKDAYS[r.week_beginning.weekday()] for r in recs if r.week_beginning))

    ticket_numbers: dict[str, list[int]] = defaultdict(list)
    for r in records:
        if r.ticket:
            ticket_numbers[r.ticket[:2]].append(int(r.ticket[3:]))
    numbering_gaps = {p: sorted(set(range(1, max(n) + 1)) - set(n)) for p, n in sorted(ticket_numbers.items())}

    return {
        "total_records": len(records),
        "count_by_type": {p: len(by_type[p]) for p in sorted(by_type)},
        "parse_issue_counts": dict(issue_codes),
        "parse_issues": dict(issues_by_code),
        "malformed_records": sorted({i.source_file for i in record_set.issues
                                     if not i.code.startswith(("unsigned_", "multi_line"))}),
        "duplicate_tickets": duplicate_tickets,
        "ticket_numbering_gaps": {p: g for p, g in numbering_gaps.items() if g},
        "records_without_date": sorted(r.source_file for r in records if not r.work_dates),
        "missing_foreman_signature": sorted(r.source_file for r in records if not r.foreman.signed),
        "missing_engineer_signature": sorted(r.source_file for r in records if not r.engineer_rep.signed),
        "jobs": dict(Counter(r.job for r in records)),
        "foremen": dict(Counter(r.foreman.name for r in records if r.foreman.signed).most_common()),
        "engineer_reps": dict(Counter(r.engineer_rep.name for r in records if r.engineer_rep.signed).most_common()),
        "types": types,
    }


# --------------------------------------------------------------------------- applications and lines

def _application_profile(apps: list[Application], lines: list[ApplicationLine], terms: ContractTerms) -> dict:
    ids = Counter(a.application_no for a in apps)
    lines_by_app: dict[str, list[ApplicationLine]] = defaultdict(list)
    for line in lines:
        lines_by_app[line.application_no].append(line)
    lag = [(a.application_date - a.period_to).days for a in apps]
    span = [(a.period_to - a.period_from).days + 1 for a in apps]
    refs: dict[str, list[str]] = defaultdict(list)
    for a in apps:
        refs[a.contract_ref].append(a.application_no)
    return {
        "count": len(apps),
        "unique_ids": len(ids),
        "duplicate_ids": sorted(i for i, n in ids.items() if n > 1),
        "applications_without_lines": sorted(a.application_no for a in apps if a.application_no not in lines_by_app),
        "contract_refs": {ref: {"count": len(ids_), "applications": sorted(ids_) if ref != terms.contract_ref else None}
                          for ref, ids_ in sorted(refs.items())},
        "subcontractors": dict(Counter(a.subcontractor for a in apps)),
        "sites": dict(Counter(a.site for a in apps).most_common()),
        "site_zones": dict(Counter(a.site_zone for a in apps).most_common()),
        "application_date_range": [min(a.application_date for a in apps).isoformat(), max(a.application_date for a in apps).isoformat()],
        "period_range": [min(a.period_from for a in apps).isoformat(), max(a.period_to for a in apps).isoformat()],
        "period_length_days": _summary(span),
        "days_from_period_end_to_application": {
            **_summary(lag),
            "before_period_end": sum(d < 0 for d in lag),
            "on_period_end": sum(d == 0 for d in lag),
            "1_to_21": sum(1 <= d <= 21 for d in lag),
            "over_21": sum(d > 21 for d in lag),
        },
        "lines_per_application": _summary([len(v) for v in lines_by_app.values()]),
        "application_total": _money_summary([a.application_total_cents for a in apps]),
        "retention": _money_summary([a.retention_cents for a in apps]),
        "net_payable": _money_summary([a.net_payable_cents for a in apps]),
        "adjustment_nonzero": sorted(a.application_no for a in apps if a.adjustment_cents),
        "retention_released_nonzero": sorted(a.application_no for a in apps if a.retention_released_cents),
    }


def _line_profile(apps: list[Application], lines: list[ApplicationLine], terms: ContractTerms) -> dict:
    app_by_id = {a.application_no: a for a in apps}
    codes = Counter(l.item_code for l in lines)
    unknown_codes = sorted(c for c in codes if c not in terms.boq)
    unit_agree = sum(1 for l in lines if l.item_code in terms.boq and l.unit == terms.boq[l.item_code].unit)
    desc_agree = sum(1 for l in lines if l.item_code in terms.boq and l.description == terms.boq[l.item_code].description)
    ground_crosstab = Counter(
        ("schedule_3_item" if l.item_code in terms.ground_factor_items else "other_item",
         "ground_stated" if l.ground_class else "ground_blank") for l in lines)
    night_crosstab = Counter(
        ("night_uplift_item" if l.item_code in terms.night_uplift_percent else "other_item",
         "night_Y" if l.night_work else "night_N") for l in lines)
    in_period = sum(1 for l in lines if l.application_no in app_by_id
                    and app_by_id[l.application_no].period_from <= l.work_date <= app_by_id[l.application_no].period_to)
    per_item = []
    for code in sorted(codes):
        item_lines = [l for l in lines if l.item_code == code]
        rates = sorted({l.rate_applied for l in item_lines})
        per_item.append({
            "code": code, "lines": len(item_lines),
            "boq_unit": terms.boq[code].unit if code in terms.boq else None,
            "billed_units": dict(Counter(l.unit for l in item_lines)),
            "quantity_sum": str(sum(l.quantity for l in item_lines)),
            "distinct_rates": len(rates), "rate_min": str(rates[0]), "rate_max": str(rates[-1]),
            "with_record_ref": sum(1 for l in item_lines if l.record_ref),
            "night_Y": sum(1 for l in item_lines if l.night_work),
        })
    refs = Counter(l.line_ref for l in lines)
    return {
        "count": len(lines),
        "unique_line_refs": len(refs),
        "duplicate_line_refs": sorted(r for r, n in refs.items() if n > 1),
        "line_ref_matches_application_and_line_no": sum(1 for l in lines if l.line_ref == f"{l.application_no}-{l.line_no:02d}"),
        "lines_without_application": sorted(l.line_ref for l in lines if l.application_no not in app_by_id),
        "work_date_range": [min(l.work_date for l in lines).isoformat(), max(l.work_date for l in lines).isoformat()],
        "work_date_weekday": dict(Counter(WEEKDAYS[l.work_date.weekday()] for l in lines)),
        "work_date_inside_application_period": in_period,
        "work_date_outside_application_period": len(lines) - in_period,
        "line_site_equals_application_site": sum(1 for l in lines if l.application_no in app_by_id and l.site == app_by_id[l.application_no].site),
        "line_zone_equals_application_zone": sum(1 for l in lines if l.application_no in app_by_id and l.site_zone == app_by_id[l.application_no].site_zone),
        "distinct_item_codes": len(codes),
        "item_codes_not_in_schedule_1": unknown_codes,
        "unit_agrees_with_schedule_1": unit_agree,
        "description_agrees_with_schedule_1": desc_agree,
        "units": dict(Counter(l.unit for l in lines).most_common()),
        "sites": dict(Counter(l.site for l in lines).most_common()),
        "zones": dict(Counter(l.site_zone for l in lines).most_common()),
        "ground_classes": dict(Counter(l.ground_class or "(blank)" for l in lines).most_common()),
        "ground_class_by_schedule_3_membership": {f"{a}/{b}": n for (a, b), n in sorted(ground_crosstab.items())},
        "night_flag": dict(Counter("Y" if l.night_work else "N" for l in lines)),
        "night_flag_by_schedule_4_part_1_membership": {f"{a}/{b}": n for (a, b), n in sorted(night_crosstab.items())},
        "rest_day_lines": sum(1 for l in lines if l.work_date.weekday() in (4, 5)),
        "quantity": {**_summary([l.quantity for l in lines]),
                     "non_integer": sum(1 for l in lines if l.quantity != l.quantity.to_integral_value()),
                     "zero_or_negative": sum(1 for l in lines if l.quantity <= 0)},
        "per_item": per_item,
    }


def _reference_profile(lines: list[ApplicationLine], record_set: RecordSet, terms: ContractTerms) -> dict:
    records = record_set.by_ticket()
    with_ref = [l for l in lines if l.record_ref]
    missing = sorted({l.record_ref for l in with_ref if l.record_ref not in records})
    usage: dict[str, list[str]] = defaultdict(list)
    for l in with_ref:
        usage[l.record_ref].append(l.line_ref)
    reused = {ref: refs for ref, refs in sorted(usage.items()) if len(refs) > 1}
    series_vs_schedule_5 = Counter()
    series_differs = []
    for l in with_ref:
        req = terms.required_records.get(l.item_code)
        if req is None:
            series_vs_schedule_5["item_not_in_schedule_5"] += 1
        elif l.record_ref[:2] == req.reference_series:
            series_vs_schedule_5["series_agrees"] += 1
        else:
            series_vs_schedule_5["series_differs"] += 1
            series_differs.append({"line_ref": l.line_ref, "item_code": l.item_code, "record_ref": l.record_ref,
                                   "schedule_5_series": req.reference_series})
    required_without_ref = [l.line_ref for l in lines if l.item_code in terms.required_records and not l.record_ref]
    area_date = Counter()
    for l in with_ref:
        rec = records.get(l.record_ref)
        if rec is None:
            continue
        area_date["area_equal" if rec.area == l.site else "area_differs"] += 1
        if rec.date is not None:
            area_date["date_equal" if rec.date == l.work_date else "date_differs"] += 1
        elif rec.week_beginning is not None:
            in_days = l.work_date in rec.days_on
            in_week = rec.week_beginning <= l.work_date <= rec.week_beginning + timedelta(6)
            area_date["weekly_work_date_in_days_on" if in_days else
                      "weekly_work_date_in_week_not_days_on" if in_week else "weekly_work_date_outside_week"] += 1
    return {
        "lines_with_reference": len(with_ref),
        "lines_without_reference": len(lines) - len(with_ref),
        "distinct_references": len(usage),
        "references_resolving_to_a_record": sum(1 for r in usage if r in records),
        "references_without_record_file": missing,
        "lines_quoting_a_missing_record": sorted(l.line_ref for l in with_ref if l.record_ref in missing),
        "references_used_on_more_than_one_line": reused,
        "records_never_referenced": sorted(set(records) - set(usage)),
        "reference_series_vs_schedule_5": dict(series_vs_schedule_5),
        "reference_series_differs_from_schedule_5": series_differs,
        "schedule_5_items_without_reference": {"count": len(required_without_ref), "lines": required_without_ref},
        "referenced_record_vs_line": dict(area_date),
    }


def _date_profile(apps: list[Application], lines: list[ApplicationLine], terms: ContractTerms) -> dict:
    boundaries = [(terms.commencement_date, "Commencement Date")]
    for inst in terms.instruments:
        boundaries.append((inst.effective, f"{inst.id} effective"))
        for sub in inst.rate_substitutions:
            if sub.effective != inst.effective:
                boundaries.append((sub.effective, f"{inst.id} substituted rates effective"))
    boundaries.append((terms.original_completion_date + timedelta(1), "day after original completion"))
    for cy in terms.contract_years[1:]:
        boundaries.append((cy.start, f"Contract Year {cy.year} starts"))
    for inst in terms.instruments:
        if inst.new_completion_date:
            boundaries.append((inst.new_completion_date + timedelta(1), f"day after {inst.id} completion date"))
    labels_by_date: dict[date, list[str]] = defaultdict(list)
    for d, label in sorted(boundaries):
        if label not in labels_by_date[d]:
            labels_by_date[d].append(label)
    marks = sorted(labels_by_date.items())
    buckets = []
    edges = [date.min] + [d for d, _ in marks] + [date.max]
    labels = ["before " + "; ".join(marks[0][1])] + [f"from {d.isoformat()} ({'; '.join(ls)})" for d, ls in marks]
    for i, label in enumerate(labels):
        lo, hi = edges[i], edges[i + 1]
        n = sum(1 for l in lines if lo <= l.work_date < hi)
        buckets.append({"from": None if lo == date.min else lo.isoformat(),
                        "to_exclusive": None if hi == date.max else hi.isoformat(), "label": label, "lines": n})
    a3 = next((i for i in terms.instruments if i.retroactive), None)
    app_dates = {}
    if a3 is not None:
        submitted_on_or_after = sorted((a for a in apps if a.application_date >= a3.issued), key=lambda a: (a.application_date, a.application_no))
        app_dates["retroactive_instrument"] = a3.id
        app_dates["retroactive_instrument_issued"] = a3.issued.isoformat()
        app_dates["applications_submitted_before_issue"] = sum(1 for a in apps if a.application_date < a3.issued)
        app_dates["applications_submitted_on_issue_date"] = sorted(a.application_no for a in apps if a.application_date == a3.issued)
        app_dates["applications_submitted_after_issue"] = sum(1 for a in apps if a.application_date > a3.issued)
        app_dates["earliest_applications_on_or_after_issue"] = [
            {"application_no": a.application_no, "application_date": a.application_date.isoformat()} for a in submitted_on_or_after[:5]]
        affected = {sub.code for sub in a3.rate_substitutions}
        app_dates["lines_of_retroactive_items_in_retro_window_submitted_before_issue"] = sum(
            1 for l in lines if l.item_code in affected and a3.effective <= l.work_date
            and l.application_no in {a.application_no for a in apps if a.application_date < a3.issued})
    completion = terms.completion_date
    after_completion = sorted((a for a in apps if a.application_date > completion), key=lambda a: (a.application_date, a.application_no))
    app_dates["extended_completion_date"] = completion.isoformat()
    app_dates["applications_submitted_after_extended_completion"] = len(after_completion)
    app_dates["earliest_applications_after_extended_completion"] = [
        {"application_no": a.application_no, "application_date": a.application_date.isoformat()} for a in after_completion[:5]]
    per_year = Counter()
    for l in lines:
        year = next((cy.year for cy in terms.contract_years if cy.start <= l.work_date <= cy.end), None)
        per_year[f"contract_year_{year}" if year else "outside_contract_years"] += 1
    return {
        "line_work_dates_by_interval": buckets,
        "line_work_dates_by_contract_year": dict(per_year),
        "lines_before_commencement": sum(1 for l in lines if l.work_date < terms.commencement_date),
        "lines_after_original_completion": sum(1 for l in lines if l.work_date > terms.original_completion_date),
        "lines_after_extended_completion": sum(1 for l in lines if l.work_date > completion),
        "applications": app_dates,
    }


def _arithmetic_profile(apps: list[Application], lines: list[ApplicationLine], terms: ContractTerms) -> dict:
    deltas = []
    for l in lines:
        product_cents = l.quantity * l.rate_applied * 100
        if product_cents != product_cents.to_integral_value():
            # Quantity x two-decimal rate with a non-integer quantity could leave sub-halala residue.
            deltas.append((l, None))
            continue
        deltas.append((l, l.amount_cents - int(product_cents)))
    exact = sum(1 for _, d in deltas if d == 0)
    mismatched = [(l, d) for l, d in deltas if d not in (0,)]
    buckets = Counter()
    for _, d in mismatched:
        if d is None:
            buckets["sub_halala_product"] += 1
        else:
            m = abs(d)
            buckets["1 halala" if m == 1 else "2-99 halalas" if m < 100 else "1.00-99.99 SAR" if m < 10000 else ">=100.00 SAR"] += 1
    examples = sorted((x for x in mismatched if x[1] is not None), key=lambda x: -abs(x[1]))[:15]

    lines_by_app: dict[str, list[ApplicationLine]] = defaultdict(list)
    for l in lines:
        lines_by_app[l.application_no].append(l)
    total_delta, retention_delta, net_delta = [], [], []
    pct = terms.retention_percent / 100
    for a in apps:
        s = sum(l.amount_cents for l in lines_by_app.get(a.application_no, []))
        total_delta.append((a.application_no, a.application_total_cents - s))
        expected_ret = int((Decimal(a.application_total_cents) * pct).to_integral_value(rounding=ROUND_FLOOR))
        retention_delta.append((a.application_no, a.retention_cents - expected_ret))
        identity = a.application_total_cents + a.adjustment_cents - a.retention_cents + a.retention_released_cents
        net_delta.append((a.application_no, a.net_payable_cents - identity))

    def split(pairs):
        bad = [(i, d) for i, d in pairs if d]
        return {"agree": len(pairs) - len(bad), "differ": len(bad),
                "differences": [{"application_no": i, "difference": _cents_str(d)} for i, d in sorted(bad, key=lambda x: -abs(x[1]))[:25]]}

    return {
        "line_amount_vs_quantity_times_rate": {
            "lines": len(lines), "exact": exact, "mismatch": len(mismatched),
            "mismatch_magnitude": dict(buckets),
            "mismatch_sign": dict(Counter("amount_below_product" if d < 0 else "amount_above_product"
                                          for _, d in mismatched if d is not None)),
            "mismatch_by_item_code": dict(Counter(l.item_code for l, _ in mismatched).most_common()),
            "largest_mismatches": [{"line_ref": l.line_ref, "quantity": str(l.quantity), "rate_applied": str(l.rate_applied),
                                    "amount": _cents_str(l.amount_cents), "difference": _cents_str(d)} for l, d in examples],
        },
        "application_total_vs_sum_of_line_amounts": split(total_delta),
        "retention_vs_floor_5_percent_of_total": split(retention_delta),
        "net_payable_vs_total_plus_adjustment_minus_retention_plus_released": split(net_delta),
    }


def source_profile(apps: list[Application], lines: list[ApplicationLine], record_set: RecordSet, terms: ContractTerms) -> dict:
    return {
        "applications": _application_profile(apps, lines, terms),
        "lines": _line_profile(apps, lines, terms),
        "record_references": _reference_profile(lines, record_set, terms),
        "date_relationships": _date_profile(apps, lines, terms),
        "arithmetic": _arithmetic_profile(apps, lines, terms),
    }
