"""One audit pass: every line of every invoice in submission order, then each invoice's own checks and valuation.

Lines are taken in the order the invoices were submitted (the invoice date stands for the submission date,
AMB-25; ties by invoice number, then line number), so that "already charged" means charged on this invoice
or an earlier one (guideline check 10, cl. 29). Report evidence is consumed as it is charged.
"""

from collections import defaultdict
from datetime import date

from contractor_audit.domains.drilling.audit.bundle import PricingBundle
from contractor_audit.domains.drilling.audit.categories import Category
from contractor_audit.domains.drilling.audit.invoices import _finding, invoice_checks, timing_observations, valuation
from contractor_audit.domains.drilling.audit.lines import Ledger, LineContext, assess_line, resolve_deferred
from contractor_audit.domains.drilling.audit.models import AuditRun, InvoiceAudit, LineAssessment, LineStatus, TotalStatus
from contractor_audit.domains.drilling.audit.policy import AuditPolicy
from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset, DrillingInvoice
from contractor_audit.shared.findings import Outcome


def submission_key(invoice: DrillingInvoice) -> tuple:
    return (invoice.invoice_date or date.max, invoice.invoice_no)


def audit(dataset: DrillingDataset, terms: ContractTerms, bundle: PricingBundle, policy: AuditPolicy) -> AuditRun:
    reports = {r.report_id: r for r in dataset.reports if r.report_id}
    retro = [i for i in terms.instruments if i.retroactive]
    retro_issue = max(i.issued for i in retro) if retro else None
    ctx = LineContext(terms, bundle, policy, reports, retro_issue)
    lines = defaultdict(list)
    for line in dataset.lines:
        lines[line.invoice_no].append(line)
    order = sorted(dataset.invoices, key=submission_key)
    ledger = Ledger()
    assessed: dict[str, list[LineAssessment]] = {}
    for invoice in order:
        assessed[invoice.invoice_no] = [assess_line(ctx, l, invoice, ledger) for l in sorted(lines[invoice.invoice_no], key=lambda l: (l.line_no or 0, l.line_ref))]
    resolve_deferred(ledger)
    adjustments = backdated_adjustments(order, assessed, policy.value("backdated_adjustment"), retro_issue)
    out = {}
    for invoice in dataset.invoices:
        la = assessed[invoice.invoice_no]
        findings = invoice_checks(terms, invoice, la, policy.value) + [f for l in la for f in l.findings]
        findings += _adjustment_findings(terms, invoice, adjustments.get(invoice.invoice_no))
        adj = adjustments.get(invoice.invoice_no)
        observations = timing_observations(invoice) if policy.value("submission_date") != "INVOICE_DATE_IS_SUBMISSION" else []
        out[invoice.invoice_no] = InvoiceAudit(invoice, la, findings, valuation(terms, la, adj, conditional=False),
                                               valuation(terms, la, adj, conditional=True), observations)
    return AuditRun(out, tuple(policy.readings()), tuple(adjustments))


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
                             clause_ids=("BR-36A",))]
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
                     f"first invoice on or after Amendment No. 3 was issued: Clause 36A puts the single adjustment for the back-dated "
                     f"rates here, {amount / 100:.2f}{basis}; the invoice shows {billed / 100:.2f}. No invoice carries any adjustment; "
                     f"this invoice is the first by invoice date, and the submission dates are not in the data (AMB-25)",
                     outcome=Outcome.PART_REJECT if determined else Outcome.QUERY, observed=f"{billed / 100:.2f}", expected=f"{amount / 100:.2f}",
                     impact=billed - amount if determined else None, affects=determined, blocks=not determined, clause_ids=("BR-36A",))]
