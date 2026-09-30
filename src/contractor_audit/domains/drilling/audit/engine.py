"""One audit pass: every line of every invoice in processing order, then each invoice's own checks and valuation.

Lines are processed in invoice-date order (ties by invoice number, then line number). The invoice date is a
deterministic processing proxy only, not the submission date, which is not in the data (AMB-25; see
`policy.SUBMISSION_PROXY`). Report evidence is consumed as it is charged, so a second charge of the same evidence is
a duplicate whichever came first (cl. 29). Conclusions that depend on the actual submission order carry AMB-25.
"""

from collections import defaultdict
from datetime import date

from contractor_audit.domains.drilling.audit.bundle import PricingBundle
from contractor_audit.domains.drilling.audit.categories import Category
from contractor_audit.domains.drilling.audit.invoices import _finding, invoice_checks, timing_observations, valuation
from contractor_audit.domains.drilling.audit.lines import Ledger, LineContext, assess_line, resolve_deferred
from contractor_audit.domains.drilling.audit.models import AuditRun, InvoiceAudit, LineAssessment, LineStatus, TotalStatus
from contractor_audit.domains.drilling.audit.policy import AuditPolicy, processing_key, submission_order_dependency
from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset, DrillingInvoice
from contractor_audit.shared.findings import ConfidenceBand, Evidence, Outcome


def audit(dataset: DrillingDataset, terms: ContractTerms, bundle: PricingBundle, policy: AuditPolicy) -> AuditRun:
    reports = {r.report_id: r for r in dataset.reports if r.report_id}
    retro = [i for i in terms.instruments if i.retroactive]
    retro_issue = max(i.issued for i in retro) if retro else None
    ctx = LineContext(terms, bundle, policy, reports, retro_issue)
    lines = defaultdict(list)
    for line in dataset.lines:
        lines[line.invoice_no].append(line)
    order = sorted(dataset.invoices, key=processing_key)
    ledger = Ledger()
    assessed: dict[str, list[LineAssessment]] = {}
    for invoice in order:
        assessed[invoice.invoice_no] = [assess_line(ctx, l, invoice, ledger) for l in sorted(lines[invoice.invoice_no], key=lambda l: (l.line_no or 0, l.line_ref))]
    resolve_deferred(ledger)
    adjustments = backdated_adjustments(order, assessed, policy.value("backdated_adjustment"), retro_issue)
    class_findings = well_class_consistency(terms, dataset.invoices, assessed)
    out = {}
    for invoice in dataset.invoices:
        la = assessed[invoice.invoice_no]
        findings = invoice_checks(terms, invoice, la, policy.value) + [f for l in la for f in l.findings]
        findings += class_findings.get(invoice.invoice_no, [])
        findings += _adjustment_findings(terms, invoice, adjustments.get(invoice.invoice_no))
        adj = adjustments.get(invoice.invoice_no)
        observations = timing_observations(invoice) if policy.value("submission_date") != "INVOICE_DATE_IS_SUBMISSION" else []
        out[invoice.invoice_no] = InvoiceAudit(invoice, la, findings, valuation(terms, la, adj, conditional=False),
                                               valuation(terms, la, adj, conditional=True), observations)
    return AuditRun(out, tuple(policy.readings()), tuple(adjustments))


def _class_sets(lines: list[LineAssessment]) -> list[LineAssessment]:
    """Class-rated lines whose billed rate some contract class produces and that the class actually constrains."""
    return [l for l in lines if l.permissible_classes and l.class_constrains]


def well_class_consistency(terms, invoices: list[DrillingInvoice], assessed: dict[str, list[LineAssessment]]) -> dict[str, list]:
    """The call-off fixes one class for the whole well (cl. 4, P2, P3): every class-rated rate billed on a well must come
    from one common class. The invoice's descriptive class is not used. An empty intersection proves an error without
    saying which class is right; the call-off is still missing, so the total stays blank.

    within one invoice   the invoice's own lines admit no common class: the invoice is wrong (HIGH)
    across invoices      each invoice is consistent, but they admit no common class together: at least one is wrong,
                         and which one is unknown, so each disagreeing invoice is flagged at MEDIUM
    """
    out: dict[str, list] = defaultdict(list)
    by_well = defaultdict(list)
    for invoice in invoices:
        by_well[invoice.well_name].append(invoice)
    for well, invs in sorted(by_well.items()):
        own = {}
        for invoice in invs:
            lines = _class_sets(assessed[invoice.invoice_no])
            if lines:
                own[invoice.invoice_no] = (invoice, lines, frozenset.intersection(*(l.permissible_classes for l in lines)))
        for no, (invoice, lines, common) in own.items():
            if not common:
                out[no].append(_class_finding(terms, invoice, lines, "class.inconsistent_within_invoice", ConfidenceBand.HIGH,
                                              "the class-rated rates billed on this invoice cannot all come from one well class"))
        consistent = {no: v for no, v in own.items() if v[2]}
        if len(consistent) > 1 and not frozenset.intersection(*(v[2] for v in consistent.values())):
            for no, (invoice, lines, common) in consistent.items():
                others = [v[2] for o, v in consistent.items() if o != no]
                if any(not (common & c) for c in others):
                    out[no].append(_class_finding(terms, invoice, lines, "class.inconsistent_across_invoices", ConfidenceBand.MEDIUM,
                                                  f"this invoice's class-rated rates admit only {', '.join(sorted(common))}; other invoices on "
                                                  f"well {well} admit only classes this one excludes, so at least one of them is wrong"))
    return out


def _class_finding(terms, invoice, lines, rule, band, what):
    groups = defaultdict(list)
    for l in lines:
        groups[tuple(sorted(l.permissible_classes))].append(f"{l.line.line_ref} ({l.line.service_code} at {l.line.unit_rate})")
    detail = "; ".join(f"{' or '.join(c)}: {', '.join(refs[:6])}{' ...' if len(refs) > 6 else ''} ({len(refs)} lines)"
                       for c, refs in sorted(groups.items()))
    evidence = tuple(Evidence("class_rated_lines", " or ".join(c), ", ".join(refs)) for c, refs in sorted(groups.items()))
    f = _finding(terms, invoice, Category.WELL_CLASS_INCONSISTENT, rule,
                 f"{what}. The call-off states one class for the whole well (cl. 4, P2, P3) and is not in the data, so which class is right "
                 f"is not known; the invoice's descriptive class ({invoice.well_class_stated}) is not evidence. Classes each billed rate "
                 f"admits: {detail}", outcome=Outcome.QUERY, observed=detail, expected="one common class for the well", affects=False,
                 blocks=True, band=band, evidence=evidence)
    return f


def backdated_adjustments(order: list[DrillingInvoice], assessed: dict[str, list[LineAssessment]], reading: str,
                          issue: date | None) -> dict[str, tuple[int, TotalStatus]]:
    """Clause 36A: the difference on services invoiced before the back-dated instrument was issued, and where it goes."""
    if issue is None or reading == "NO_REPRICING":
        return {}
    dated = [i for i in order if i.invoice_date]
    before = [i for i in dated if i.invoice_date < issue]
    after = [i for i in dated if (i.invoice_date > issue if reading == "CONTRACT_WIDE_AFTER" else i.invoice_date >= issue)]

    def difference(invoices) -> tuple[int, TotalStatus] | None:
        total, status, any_line = 0, TotalStatus.DETERMINED, False
        for inv in invoices:
            for l in assessed[inv.invoice_no]:
                if l.retro_difference_cents is None:
                    continue
                any_line = True
                total += l.retro_difference_cents
                if l.status is LineStatus.CONDITIONAL and status is TotalStatus.DETERMINED:
                    status = TotalStatus.CONDITIONAL
                elif l.status is LineStatus.UNDETERMINED:
                    status = TotalStatus.UNDETERMINED
        return (total, status) if any_line else None

    out = {}
    if reading in ("CONTRACT_WIDE_ON_OR_AFTER", "CONTRACT_WIDE_AFTER"):
        diff = difference(before)
        if after and diff:
            out[after[0].invoice_no] = diff
    elif reading == "PER_WELL":
        for well in sorted({i.well_name for i in before}):
            diff = difference([i for i in before if i.well_name == well])
            first = next((i for i in after if i.well_name == well), None)
            if diff and first:
                out[first.invoice_no] = diff
    return out


def _adjustment_findings(terms, invoice: DrillingInvoice, expected: tuple[int, TotalStatus] | None) -> list:
    billed = invoice.adjustment_cents or 0
    if expected is None:
        if billed:
            return [_finding(terms, invoice, Category.BACKDATED_ADJUSTMENT_INCORRECT, "adjustments.backdated_not_due",
                             f"an adjustment of {billed / 100:.2f} is shown; Clause 36A puts the single adjustment on another invoice",
                             outcome=Outcome.PART_REJECT, observed=f"{billed / 100:.2f}", expected="0.00", impact=billed, affects=True,
                             clause_ids=("BR-36A",), deps=(submission_order_dependency(),))]
        return []
    amount, status = expected
    determined = status is TotalStatus.DETERMINED
    if determined and billed == amount:
        return []
    if not determined and billed == 0 and amount == 0:
        return []
    category = Category.BACKDATED_ADJUSTMENT_MISSING if billed == 0 else Category.BACKDATED_ADJUSTMENT_INCORRECT
    basis = "" if determined else " (the difference includes class-rated services, so it is conditional on the call-off: AMB-13)"
    return [_finding(terms, invoice, category, "adjustments.backdated",
                     f"Clause 36A puts the single adjustment for the back-dated rates on the first invoice submitted on or after "
                     f"Amendment No. 3 was issued: {amount / 100:.2f}{basis}; this invoice shows {billed / 100:.2f}. No invoice carries any "
                     f"adjustment, so it is missing wherever it belongs; it is placed here because this is the first invoice in invoice-date "
                     f"order, a proxy (the submission dates are not in the data, AMB-25)",
                     outcome=Outcome.PART_REJECT if determined else Outcome.QUERY, observed=f"{billed / 100:.2f}", expected=f"{amount / 100:.2f}",
                     impact=billed - amount if determined else None, affects=determined, blocks=not determined, clause_ids=("BR-36A",),
                     deps=(submission_order_dependency(),))]
