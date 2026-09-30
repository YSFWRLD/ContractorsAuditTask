"""Facts in the drilling data that bear on the open Phase 1 ambiguities.

Recorded for later phases; never used to choose a reading. The only contract fact read here is the issue
date of the back-dated instrument, taken from the reviewed contract model rather than restated.
"""

from collections import Counter

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.indexes import DrillingIndexes
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset
from contractor_audit.domains.drilling.ingestion.timelines import bha_runs, well_timelines


def collect(ds: DrillingDataset, ix: DrillingIndexes, terms: ContractTerms) -> tuple[dict, ...]:
    reports = [r for r in ds.reports if r.operations]
    standby = [r for r in reports if r.operations.status == "Standby"]
    timelines = well_timelines(ix)
    backdated = [i for i in terms.instruments if i.retroactive]
    issue_dates = sorted(i.issued for i in backdated)
    first_after_issue = sorted((i.invoice_date, i.invoice_no) for i in ds.invoices
                               if issue_dates and i.invoice_date and i.invoice_date >= issue_dates[0])[:3]
    lost = [r for r in ds.reports if r.lost_in_hole]
    well_sum = tool_sum = 0
    for r in lost:
        before = [x for x in ix.reports_by_well.get(r.well) if x.date and x.operations and x.date <= r.date]
        stated = r.lost_in_hole.circulating_hours_accumulated_on_well
        well_sum += stated == sum(x.operations.circulating_hours for x in before)
        tool_sum += stated == sum(x.operations.circulating_hours for x in before if r.lost_in_hole.tool in x.operations.in_the_hole)
    runs = bha_runs(ix)
    logged = [(_run_value(ix, run, "metres_logged"), _depth_advance(ix, run)) for run in runs.values()]
    reamed = [(_run_value(ix, run, "metres_reamed"), _depth_advance(ix, run)) for run in runs.values()]
    return (
        {"ambiguities": ["AMB-13"], "fact": "Well class appears only on invoice headers (the contractor's statement); no call-off is in the data.",
         "wells": len(timelines), "wells_with_more_than_one_stated_class": sum(len(t.well_classes_stated) > 1 for t in timelines.values()),
         "stated_classes": dict(sorted(Counter(i.well_class_stated for i in ds.invoices).items()))},
        {"ambiguities": ["AMB-12", "AMB-25"], "fact": "The adjustment column is 0.00 on every invoice; invoices carry an invoice date but no submission date.",
         "nonzero_adjustments": sum(1 for i in ds.invoices if i.adjustment_cents),
         "backdated_instruments": [f"{i.id} issued {i.issued}" for i in backdated],
         "earliest_invoices_dated_on_or_after_that_issue_date": [f"{n} {d}" for d, n in first_after_issue]},
        {"ambiguities": ["AMB-05", "AMB-06", "AMB-20"], "fact": "Reports state whole circulating and back-reaming hours per day; some Standby days record circulating hours.",
         "standby_reports": len(standby), "standby_reports_with_circulating_hours": sum(1 for r in standby if r.operations.circulating_hours),
         "reports_with_back_reaming_hours": sum(1 for r in reports if r.operations.back_reaming_hours)},
        {"ambiguities": ["AMB-14", "AMB-23"], "fact": "Each report has one signature block (Company Representative, lead directional driller) after its last part; Parts B-E carry no signatures of their own.",
         "reports_with_blank_signatures": sum(1 for r in ds.reports if any(s.blank for s in r.signatures))},
        {"ambiguities": ["AMB-15", "AMB-17"], "fact": "Reports list tools and crew in rig words; no report field carries a service code.",
         "distinct_tool_words": sorted({w for r in reports for w in r.operations.in_the_hole}),
         "distinct_crew_roles": sorted({c.role for r in reports for c in r.operations.crew})},
        {"ambiguities": ["AMB-22"], "fact": "Part E states circulating hours accumulated on the well at the loss. Compared with sums of daily circulating hours up to and including the day of loss.",
         "part_e_reports": len(lost), "equal_to_whole_well_sum": well_sum, "equal_to_sum_on_days_the_lost_tool_is_in_the_hole": tool_sum},
        {"ambiguities": ["AMB-24"], "fact": "Part B states metres logged and reamed per run. Compared with the sum of daily depth advances over the run's reports.",
         "runs": len(runs), "runs_with_metres_logged": sum(1 for m, _ in logged if m), "logged_equal_to_depth_advance": sum(1 for m, d in logged if m and m == d),
         "runs_with_metres_reamed": sum(1 for m, _ in reamed if m), "reamed_equal_to_depth_advance": sum(1 for m, d in reamed if m and m == d)},
    )


def _run_value(ix: DrillingIndexes, run, attr: str):
    values = {getattr(ix.reports_by_id.one(rid).bha_run, attr) for rid in run.report_ids}
    return values.pop() if len(values) == 1 else None


def _depth_advance(ix: DrillingIndexes, run):
    reports = [ix.reports_by_id.one(rid) for rid in run.report_ids]
    if any(r.operations is None or r.operations.depth_end_m is None or r.operations.depth_start_m is None for r in reports):
        return None
    return sum(r.operations.depth_end_m - r.operations.depth_start_m for r in reports)
