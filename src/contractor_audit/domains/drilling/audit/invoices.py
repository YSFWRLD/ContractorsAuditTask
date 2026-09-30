"""Invoice-level checks (1, 3, 8, 11) and the valuation of the total the contract supports.

    1   contract reference and issuer (Form of Agreement); every charge on the invoice's own well (cl. 32)
    3   dated no earlier than the last day of its period and within 30 days after it (cl. 33; AMB-25)
    8   the Clause 36A adjustment for the back-dated Amendment No. 3 rates, where the reading used puts it (AMB-12)
    11  net = sum of the charges including DS-900 (cl. 36); VAT 15 per cent of net rounded (cl. 39);
        total = net + VAT (cl. 40); DS-900 = 4 per cent of the services' sum above 250,000.00 (cl. 38; AMB-26)

The valuation rebuilds the invoice from the contract-side line amounts: services, DS-900 on them, the 36A
adjustment, VAT. It is `determined` only when every component is; a CONDITIONAL line (AMB-13) makes it
`conditional` and an unvalued line makes it `undetermined`. The conditional valuation takes each conditional line
at the contractor's claimed entitlement: an analysis figure, never a payable one.
"""

from datetime import timedelta
from decimal import Decimal

from contractor_audit.domains.drilling.audit.categories import Category, info
from contractor_audit.domains.drilling.audit.models import InvoiceValuation, LineAssessment, LineStatus, TotalStatus
from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DrillingInvoice
from contractor_audit.domains.drilling.pricing.rounding import half_even_cents
from contractor_audit.shared.findings import Citation, ConfidenceBand, Evidence, Finding, Outcome

WINDOW_DAYS = 30   # cl. 33 / Form of Agreement


def _finding(terms, invoice, category: Category, rule: str, message: str, *, outcome=Outcome.QUERY, observed=None, expected=None,
             impact=None, affects=False, blocks=False, band=ConfidenceBand.HIGH, evidence=(), clause_ids=()) -> Finding:
    meta = info(category.value)
    citations = tuple(Citation(cid, *terms.clauses[cid]) for cid in clause_ids if cid in terms.clauses)
    head = Evidence("invoice", invoice.invoice_no, f"{invoice.contract_ref}; {invoice.contractor}; {invoice.well_name}; period {invoice.period_start}.."
                    f"{invoice.period_end}; dated {invoice.invoice_date}; net {_m(invoice.net_cents)} VAT {_m(invoice.vat_cents)} "
                    f"total {_m(invoice.total_cents)} adjustment {_m(invoice.adjustment_cents)}", source=invoice.source.file)
    return Finding(check=meta.check, outcome=outcome, message=message, clause=", ".join(meta.clauses), invoice_id=invoice.invoice_no,
                   evidence=(head,) + tuple(evidence), category=category.value, rule=rule, observed=observed, expected=expected,
                   impact_cents=impact, citations=citations, affects_total=affects, blocks_total=blocks, confidence=band)


def _m(c: int | None) -> str:
    return "blank" if c is None else f"{c / 100:.2f}"


def discount(terms: ContractTerms, services_cents: int) -> int:
    """Clause 38: 4 per cent of the excess over 250,000.00 ('exceeds': strictly greater), as a negative charge."""
    d = terms.invoice_discount
    if services_cents <= d.threshold_cents:
        return 0
    return -half_even_cents(Decimal(services_cents - d.threshold_cents) * d.percent / 100)


def vat(terms: ContractTerms, net_cents: int) -> int:
    return half_even_cents(Decimal(net_cents) * terms.vat_percent / 100)


def invoice_checks(terms: ContractTerms, invoice: DrillingInvoice, lines: list[LineAssessment], policy_value) -> list[Finding]:
    out: list[Finding] = []
    F = lambda *a, **k: out.append(_finding(terms, invoice, *a, **k))  # noqa: E731
    # check 1
    if invoice.contract_ref != terms.contract_ref:
        F(Category.CONTRACT_REFERENCE_MISMATCH, "identity.contract_ref", f"invoice quotes contract {invoice.contract_ref!r}, not {terms.contract_ref}",
          observed=invoice.contract_ref, expected=terms.contract_ref, clause_ids=("BR-REF",))
    if terms.contractor and invoice.contractor != terms.contractor:
        F(Category.CONTRACT_REFERENCE_MISMATCH, "identity.issuer", f"issued by {invoice.contractor!r}, not the Contractor {terms.contractor!r}",
          observed=invoice.contractor, expected=terms.contractor, clause_ids=("BR-REF",))
    missing = [n for n, v in (("period_start", invoice.period_start), ("period_end", invoice.period_end), ("invoice_date", invoice.invoice_date),
                              ("net_amount", invoice.net_cents), ("vat_amount", invoice.vat_cents), ("invoice_total", invoice.total_cents)) if v is None]
    if missing:
        F(Category.INVOICE_DETAILS_MISSING, "identity.details_missing", f"invoice lacks {', '.join(missing)}", blocks=True)
    elif invoice.period_start > invoice.period_end:
        F(Category.INVOICE_DETAILS_MISSING, "identity.period_reversed", f"period starts {invoice.period_start}, after it ends {invoice.period_end}", blocks=True,
          clause_ids=("BR-32",))
    # check 3: Clause 33 is about submission. Only under AMB-25 reading A (the invoice date taken as the submission date)
    # is timing judged from the invoice date; as decided (EVIDENCE_NOT_PROVIDED) the facts are observations only.
    if invoice.invoice_date and invoice.period_end and policy_value("submission_date") == "INVOICE_DATE_IS_SUBMISSION":
        if invoice.invoice_date < invoice.period_end:
            F(Category.INVOICE_TIMING, "timing.before_period_end", f"dated {invoice.invoice_date}, before its period ended on {invoice.period_end}",
              observed=str(invoice.invoice_date), expected=f"on or after {invoice.period_end}", band=ConfidenceBand.MEDIUM, clause_ids=("BR-33",))
        elif invoice.invoice_date > invoice.period_end + timedelta(days=WINDOW_DAYS):
            F(Category.INVOICE_TIMING, "timing.late", f"dated {invoice.invoice_date}, {(invoice.invoice_date - invoice.period_end).days} days after its period ended",
              observed=str(invoice.invoice_date), expected=f"by {invoice.period_end + timedelta(days=WINDOW_DAYS)}", band=ConfidenceBand.MEDIUM,
              clause_ids=("BR-33",))
    # check 11
    charges = [l.line.amount_cents for l in lines]
    if None not in charges and invoice.net_cents is not None:
        if sum(charges) != invoice.net_cents:
            F(Category.INVOICE_ARITHMETIC, "arithmetic.net", f"charges sum to {_m(sum(charges))}; net amount stated {_m(invoice.net_cents)}",
              outcome=Outcome.PART_REJECT, observed=_m(invoice.net_cents), expected=_m(sum(charges)), impact=invoice.net_cents - sum(charges),
              affects=True, clause_ids=("BR-36",))
    if invoice.net_cents is not None and invoice.vat_cents is not None and vat(terms, invoice.net_cents) != invoice.vat_cents:
        F(Category.VAT_ERROR, "arithmetic.vat", f"VAT stated {_m(invoice.vat_cents)}; 15 per cent of the stated net is {_m(vat(terms, invoice.net_cents))}",
          outcome=Outcome.PART_REJECT, observed=_m(invoice.vat_cents), expected=_m(vat(terms, invoice.net_cents)),
          impact=invoice.vat_cents - vat(terms, invoice.net_cents), affects=True, clause_ids=("BR-39",))
    if None not in (invoice.net_cents, invoice.vat_cents, invoice.total_cents) and invoice.net_cents + invoice.vat_cents != invoice.total_cents:
        F(Category.INVOICE_ARITHMETIC, "arithmetic.total", f"total stated {_m(invoice.total_cents)}; net + VAT is {_m(invoice.net_cents + invoice.vat_cents)}",
          outcome=Outcome.PART_REJECT, observed=_m(invoice.total_cents), expected=_m(invoice.net_cents + invoice.vat_cents),
          impact=invoice.total_cents - invoice.net_cents - invoice.vat_cents, affects=True, clause_ids=("BR-40",))
    ds = [l.line for l in lines if l.status is LineStatus.INVOICE_LEVEL]
    services = [l.line.amount_cents for l in lines if l.status is not LineStatus.INVOICE_LEVEL]
    if None not in services and None not in [d.amount_cents for d in ds]:
        expected = discount(terms, sum(services))
        billed = sum(d.amount_cents for d in ds)
        if len(ds) > 1 or billed != expected:
            what = "omitted" if not ds and expected else "charged although the services do not exceed 250,000.00" if not expected else "miscalculated"
            F(Category.INVOICE_DISCOUNT_ERROR, "adjustments.ds900", f"Clause 38 discount {what}: the charged services sum to {_m(sum(services))}, "
              f"so DS-900 is {_m(expected)}; the invoice shows {_m(billed)}" + (f" on {len(ds)} lines" if len(ds) > 1 else ""),
              outcome=Outcome.PART_REJECT, observed=_m(billed), expected=_m(expected), impact=billed - expected,
              affects=True, clause_ids=("BR-38",))
    return out


def timing_observations(invoice: DrillingInvoice) -> list[str]:
    """Invoice-date facts bearing on Clause 33, recorded without a finding: the submission date is not in the data (AMB-25)."""
    if not (invoice.invoice_date and invoice.period_end):
        return []
    lag = (invoice.invoice_date - invoice.period_end).days
    if lag < 0:
        return [f"invoice dated {invoice.invoice_date}, {-lag} day(s) before its period ended on {invoice.period_end}; the submission "
                "date is not in the data (AMB-25), so Clause 33 is not judged"]
    if lag > WINDOW_DAYS:
        return [f"invoice dated {invoice.invoice_date}, {lag} days after its period ended on {invoice.period_end}; the submission date "
                "is not in the data (AMB-25), so Clause 33 is not judged"]
    return []


def valuation(terms: ContractTerms, lines: list[LineAssessment], adjustment: tuple[int, TotalStatus] | None, conditional: bool) -> InvoiceValuation:
    """The total the contract supports; `conditional` takes CONDITIONAL lines at the claimed entitlement."""
    reasons, status = [], TotalStatus.DETERMINED
    services = 0
    for l in lines:
        if l.status is LineStatus.INVOICE_LEVEL:
            continue
        if l.status is LineStatus.UNDETERMINED or l.amount_cents is None:
            status = TotalStatus.UNDETERMINED
            reasons.append(f"undetermined_line:{l.line.line_ref}")
            continue
        if l.status is LineStatus.CONDITIONAL:
            if not conditional:
                if status is TotalStatus.DETERMINED:
                    status = TotalStatus.CONDITIONAL
                reasons.append(f"entitlement_unverified:{l.line.service_code}")
        services += l.amount_cents
    adj = 0
    if adjustment is not None:
        adj, adj_status = adjustment
        if adj_status is TotalStatus.UNDETERMINED or (adj_status is TotalStatus.CONDITIONAL and not conditional):
            status = TotalStatus.UNDETERMINED if adj_status is TotalStatus.UNDETERMINED else (TotalStatus.CONDITIONAL if status is TotalStatus.DETERMINED else status)
            reasons.append(f"backdated_adjustment_{adj_status.value}")
    if status is TotalStatus.UNDETERMINED:
        return InvoiceValuation(status, None, None, None, None, None, None, tuple(dict.fromkeys(reasons)))
    ds = discount(terms, services)
    net = services + ds + adj
    v = vat(terms, net)
    return InvoiceValuation(status, services, ds, adj, net, v, net + v, tuple(dict.fromkeys(reasons)))
