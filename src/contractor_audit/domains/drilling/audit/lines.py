"""Checks 2-11 on one invoice line: evidence first, then the invoice's figures compared with it.

Order inside a line (guideline order; every failure is recorded, none stops the others unless the line has no
evidence to compare with):

    service code, unit, description, required details          check 6 (and 34-35)
    term, invoice period                                        checks 2-3
    the quoted report: exists, same well and day, signed,      check 4 (cl. 15, 19A, 37); consequence AMB-23
      the Schedule 5 part the service needs
    report evidence for the service                             check 6 (unsupported, once-only)
    chargeability on the day                                    check 9 (Standby, hole size, term)
    quantity against the evidence not yet charged               checks 5, 9, 10 (record, daily limit, duplicates)
    rate against the contract rate in force (36A-aware)         checks 7-8, diagnosed
    amount = quantity x rate                                    check 11

The invoice's own well class, service code, quantity and rate are read only to COMPARE with the contract-side
figure already established from the reports. A charge whose entitlement needs the missing call-off (AMB-13) is
CONDITIONAL: its billed figures are still compared with the price each possible class would give, and a billed
figure no possible entitlement produces is a finding in its own right.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from contractor_audit.domains.drilling.audit.bundle import PD210, PricingBundle
from contractor_audit.domains.drilling.audit.categories import Category, info
from contractor_audit.domains.drilling.audit.diagnosis import diagnose
from contractor_audit.domains.drilling.audit.models import LineAssessment, LineStatus
from contractor_audit.domains.drilling.audit.policy import AuditPolicy
from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DailyReport, DrillingInvoice, InvoiceLine
from contractor_audit.domains.drilling.pricing.models import PricedQuantity, PricingStatus
from contractor_audit.domains.drilling.pricing.rounding import half_even_cents
from contractor_audit.shared.findings import Citation, ConfidenceBand, Evidence, Finding, Outcome

METRE_TOLERANCE = Decimal("1.01")        # 25A: metres not exceeding the record by more than 1 per cent are payable as charged
RUN_ONCE = ("DD-111", "LW-420")          # cl. 26: once for each BHA run
PART_SERVICES = ("B", "C", "D", "E")     # Schedule 5 parts whose illustrative forms name their own signatories (AMB-14)


def cents(value: Decimal) -> int:
    return half_even_cents(value * 100)


@dataclass
class Ledger:
    """Report evidence already charged, in submission order: qid -> quantity consumed, and by which lines."""
    consumed: dict[str, Decimal] = field(default_factory=dict)
    consumers: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    pd210: dict[str, list[tuple[int, int, str, str]]] = field(default_factory=dict)   # well -> (from, to, invoice, line)
    deferred: list = field(default_factory=list)   # lines already denied: checked for re-used evidence once every line is in

    def take(self, qid: str, quantity: Decimal, invoice_no: str, line_ref: str) -> None:
        self.consumed[qid] = self.consumed.get(qid, Decimal(0)) + quantity
        self.consumers.setdefault(qid, []).append((invoice_no, line_ref))


@dataclass(frozen=True)
class LineContext:
    terms: ContractTerms
    bundle: PricingBundle
    policy: AuditPolicy
    reports: dict[str, DailyReport]
    retro_issue: date | None          # issue date of the back-dated instrument (A3); services priced before it: 36A


class _Line:
    """Builds the findings of one line."""

    def __init__(self, ctx: LineContext, line: InvoiceLine, invoice: DrillingInvoice):
        self.ctx, self.line, self.invoice = ctx, line, invoice
        self.a = LineAssessment(line, LineStatus.DETERMINED)

    def finding(self, category: Category, rule: str, message: str, *, outcome=Outcome.PART_REJECT, observed=None, expected=None,
                impact=None, affects=True, blocks=False, band=ConfidenceBand.HIGH, evidence=(), clause_ids=()) -> Finding:
        meta = info(category.value)
        citations = tuple(Citation(cid, *self.ctx.terms.clauses[cid]) for cid in clause_ids if cid in self.ctx.terms.clauses)
        f = Finding(check=meta.check, outcome=outcome, message=message, clause=", ".join(meta.clauses), line_ref=self.line.line_ref,
                    evidence=(self.billed(),) + tuple(evidence), invoice_id=self.invoice.invoice_no, category=category.value, rule=rule,
                    observed=observed, expected=expected, impact_cents=impact, citations=citations, affects_total=affects,
                    blocks_total=blocks, confidence=band)
        self.a.findings.append(f)
        return f

    def billed(self) -> Evidence:
        l = self.line
        return Evidence("billed_line", l.line_ref, f"{l.service_code} {l.service_date} qty {l.quantity} {l.unit} x {l.unit_rate} = "
                        f"{(l.amount_cents or 0) / 100:.2f}; report {l.report_ref}; {l.day_status}; {l.hole_section}"
                        + (f"; depths {l.depth_from_m}-{l.depth_to_m}" if l.depth_from_m is not None else ""))

    def not_payable(self):
        self.a.status, self.a.payable_quantity, self.a.amount_cents = LineStatus.DETERMINED, Decimal(0), 0


def report_evidence(report: DailyReport) -> Evidence:
    ops = report.operations
    return Evidence("daily_report", report.report_id or "", f"{report.well} {report.date}: {ops.status if ops else '?'}, {ops.hole_section if ops else '?'}; "
                    f"parts {report.variant}; signatures " + ", ".join(f"{s.role}={'blank' if s.blank else 'signed'}" for s in report.signatures),
                    source=report.source.file)


def priced_evidence(p: PricedQuantity, rate_cents: int | None = None) -> Evidence:
    steps = "; ".join(f"{s.name} {s.output_cents / 100:.2f}" for part in p.parts for s in part.steps)
    readings = ", ".join(f"{s}={v}" for s, v, _ in p.readings_used)
    return Evidence("pricing_trace", p.qid, f"{p.status.value}: chargeable {p.chargeable_quantity} {p.unit}; {steps or p.reason}",
                    result=None if rate_cents is None else f"{rate_cents / 100:.2f}", interpretation=readings or None)


def assess_line(ctx: LineContext, line: InvoiceLine, invoice: DrillingInvoice, ledger: Ledger) -> LineAssessment:
    L = _Line(ctx, line, invoice)
    if line.service_code == ctx.terms.invoice_discount.code:
        L.a.status = LineStatus.INVOICE_LEVEL
        return L.a
    _assess(L, ledger)
    if None not in (line.quantity, line.unit_rate, line.amount_cents):
        _arithmetic(L)
    return L.a


def _assess(L: _Line, ledger: Ledger) -> None:
    ctx, line, invoice = L.ctx, L.line, L.invoice
    terms = ctx.terms
    code = line.service_code
    billed_amount = line.amount_cents or 0
    service = terms.services.get(code)
    if service is None:
        L.finding(Category.SERVICE_NOT_IN_CONTRACT, "identification.unknown_code", f"{code} is not a Schedule 1 item",
                  observed=code, impact=billed_amount, clause_ids=("BR-34",))
        L.not_payable()
        return
    missing = [n for n, v in (("service_date", line.service_date), ("quantity", line.quantity), ("unit_rate", line.unit_rate),
                              ("amount", line.amount_cents)) if v is None]
    if code == PD210 and (line.depth_from_m is None or line.depth_to_m is None):
        missing.append("depths")
    if missing:
        L.finding(Category.LINE_DETAILS_MISSING, "identification.details_missing", f"charge lacks {', '.join(missing)} (cl. 34)",
                  outcome=Outcome.QUERY, affects=False, blocks=True, clause_ids=("BR-34",))
        L.a.status = LineStatus.UNDETERMINED
        return
    if line.unit != service.unit:
        L.finding(Category.UNIT_MISMATCH, "identification.unit", f"charged per {line.unit}; Schedule 1 unit is {service.unit} (cl. 35: in no other)",
                  observed=line.unit, expected=service.unit, impact=billed_amount, clause_ids=("BR-35",))
        L.not_payable()
        return
    if line.description != service.description:
        L.finding(Category.DESCRIPTION_MISMATCH, "identification.description", "description does not match the Schedule 1 item the code names",
                  outcome=Outcome.QUERY, observed=line.description, expected=service.description, affects=False, blocks=True,
                  band=ConfidenceBand.MEDIUM, clause_ids=("BR-34",))
        L.a.status = LineStatus.UNDETERMINED
    if line.well_name != invoice.well_name:
        L.finding(Category.INVOICE_WELL_MISMATCH, "identity.line_well", f"charge for well {line.well_name} on the invoice for {invoice.well_name}",
                  observed=line.well_name, expected=invoice.well_name, impact=billed_amount, clause_ids=("BR-32",))
        L.not_payable()
    day = line.service_date
    if not (terms.commencement <= day <= terms.final_expiry):
        L.finding(Category.WORK_OUTSIDE_CONTRACT_TERM, "term.outside", f"service date {day} outside the term {terms.commencement}..{terms.final_expiry}",
                  observed=str(day), expected=f"{terms.commencement}..{terms.final_expiry}", impact=billed_amount, clause_ids=("BR-TERM",))
        L.not_payable()
    if invoice.period_start and invoice.period_end and not (invoice.period_start <= day <= invoice.period_end):
        L.finding(Category.LINE_OUTSIDE_INVOICE_PERIOD, "timing.line_outside_period",
                  f"charge dated {day}, outside the invoice period {invoice.period_start}..{invoice.period_end}",
                  observed=str(day), expected=f"{invoice.period_start}..{invoice.period_end}", impact=billed_amount, clause_ids=("BR-32",))
        L.not_payable()

    report = ctx.reports.get(line.report_ref) if line.report_ref else None
    record_failure = _record_checks(L, service, report)
    usable = report is not None and report.well == line.well_name
    if not usable:
        if L.a.status is not LineStatus.UNDETERMINED:
            _record_consequence(L, billed_amount)
        return
    if record_failure:
        _record_consequence(L, billed_amount)
    if (L.a.status is LineStatus.DETERMINED and L.a.amount_cents == 0) or L.a.status is LineStatus.UNDETERMINED:
        ledger.deferred.append((L, service, report))     # not payable anyway; only its re-use of evidence is still in question
    else:
        _match(L, service, report, ledger, dry=False)


def resolve_deferred(ledger: Ledger) -> None:
    """Lines denied for another reason: is the report evidence they quote charged on another line? (cl. 29)"""
    for L, service, report in ledger.deferred:
        _match(L, service, report, ledger, dry=True)
    ledger.deferred.clear()
    return


def _record_checks(L: _Line, service, report: DailyReport | None) -> Category | None:
    line, policy = L.line, L.ctx.policy
    ev = (report_evidence(report),) if report else ()
    if report is None:
        what = "no report is quoted" if not line.report_ref else f"report {line.report_ref} does not exist"
        L.finding(Category.MISSING_RECORD, "records.missing", f"{what} (cl. 19A, 37)", clause_ids=("BR-19A", "BR-37"))
        return Category.MISSING_RECORD
    if report.well != line.well_name or report.date != line.service_date:
        L.finding(Category.RECORD_LINE_MISMATCH, "records.other_day_or_well",
                  f"report {report.report_id} is for {report.well} on {report.date}; the charge is for {line.well_name} on {line.service_date}",
                  observed=f"{line.well_name} {line.service_date}", expected=f"{report.well} {report.date}", evidence=ev, clause_ids=("BR-19A", "CL-19"))
        return Category.RECORD_LINE_MISMATCH
    blank = [s.role for s in report.signatures if s.blank]
    if blank or len(report.signatures) < 2:
        L.finding(Category.UNSIGNED_RECORD, "records.unsigned", f"report {report.report_id} is not signed by: {', '.join(blank) or 'a required signatory'} (cl. 15)",
                  evidence=ev)
        return Category.UNSIGNED_RECORD
    part = service.record_part_required
    if part and part not in report.parts:
        L.finding(Category.RECORD_PART_MISSING, "records.part_missing", f"{service.code} needs Part {part} of the report; report {report.report_id} has parts {report.variant}",
                  evidence=ev, clause_ids=("BR-37",))
        return Category.RECORD_PART_MISSING
    if part in PART_SERVICES and policy.value("record_signatories") == "FORM_SIGNATORIES_REQUIRED":
        L.finding(Category.UNSIGNED_RECORD, "records.part_form_signatories",
                  f"Part {part} carries no signatures of its own; the Appendix E-F form names its own signatories (AMB-14 reading B)", evidence=ev)
        return Category.UNSIGNED_RECORD
    if policy.value("report_vocabulary") == "CODES_REQUIRED":
        L.finding(Category.RECORD_NOT_COMPLIANT, "records.codes_required", "the report lists rig words, not service codes (AMB-15 reading B: R5/R6)",
                  evidence=ev)
        return Category.RECORD_NOT_COMPLIANT
    return None


def _record_consequence(L: _Line, billed_amount: int) -> None:
    """AMB-23: a charge without its record is not payable on this invoice (PART_REJECT) or held as a query (QUERY)."""
    record = [f for f in L.a.findings if info(f.category).check.value == 4]
    if not record:
        return
    if L.ctx.policy.value("missing_record_consequence") == "PART_REJECT":
        for i, f in enumerate(L.a.findings):
            if f in record:
                L.a.findings[i] = _replace(f, impact_cents=billed_amount, affects_total=True, outcome=Outcome.PART_REJECT)
        L.not_payable()
    else:
        for i, f in enumerate(L.a.findings):
            if f in record:
                L.a.findings[i] = _replace(f, affects_total=False, blocks_total=True, outcome=Outcome.QUERY)
        L.a.status = LineStatus.UNDETERMINED


def _replace(f: Finding, **kw) -> Finding:
    from dataclasses import replace
    return replace(f, **kw)


def _match(L: _Line, service, report: DailyReport, ledger: Ledger, dry: bool) -> None:
    """Compare the charge with the report evidence for it; `dry` only looks for earlier charges of the same evidence."""
    ctx, line = L.ctx, L.line
    code = line.service_code
    ev = report_evidence(report)
    if code == PD210:
        return _match_pd210(L, report, ledger, dry)
    candidates = ctx.bundle.at_report(report.report_id, code)
    if not candidates:
        elsewhere = ctx.bundle.on_well(line.well_name, code) if (service.once_per_well or code in RUN_ONCE) else []
        if dry:
            return
        if elsewhere:
            L.finding(Category.ONCE_ONLY_EXCEEDED, "limits.once_only",
                      f"{code} is charged once for the {'run' if code in RUN_ONCE else 'well'} (cl. 26-27); report {report.report_id} is not the day it is due",
                      impact=line.amount_cents, evidence=(ev,) + tuple(priced_evidence(p) for p in elsewhere[:2]), clause_ids=("CL-26", "CL-27", "CL-29"))
        else:
            L.finding(Category.UNSUPPORTED_SERVICE, "identification.no_report_evidence",
                      f"report {report.report_id} records no tool, person or event {code} is charged for",
                      impact=line.amount_cents, evidence=(ev,), clause_ids=("CL-28", "CL-22", "BR-19A"))
        L.not_payable()
        return
    p = candidates[0]
    if len(candidates) > 1:
        L.a.observations.append(f"{len(candidates)} report quantities for {code}; compared with the first ({p.qid})")
    L.a.matched = (p.qid,)
    available = p.chargeable_quantity - ledger.consumed.get(p.qid, Decimal(0))
    if dry:
        if ledger.consumed.get(p.qid) and available <= 0:
            _duplicate(L, p, ledger, line.amount_cents, ev)
        return
    if p.status is PricingStatus.NOT_CHARGEABLE:
        category = (Category.SECTION_NOT_ELIGIBLE if "Appendix A" in p.reason else
                    Category.WORK_OUTSIDE_CONTRACT_TERM if "outside the term" in p.reason else Category.NOT_CHARGEABLE_ON_STANDBY)
        L.finding(category, "limits.not_chargeable", f"not chargeable: {p.reason}", impact=line.amount_cents, evidence=(ev, priced_evidence(p)),
                  clause_ids=("CL-20", "CL-21") if category is Category.NOT_CHARGEABLE_ON_STANDBY else ("CL-23",))
        L.not_payable()
        return
    if p.status is PricingStatus.UNPRICEABLE:
        L.a.status = LineStatus.UNDETERMINED
        L.a.observations.append(f"contract price not determinable: {p.reason}")
        return
    payable = _quantity(L, p, available, ledger, ev)
    if payable is None:
        return
    ledger.take(p.qid, min(payable, available), L.invoice.invoice_no, line.line_ref)
    _price(L, p, payable, ev)


def _duplicate(L: _Line, p: PricedQuantity, ledger: Ledger, impact: int, ev: Evidence) -> None:
    earlier = ledger.consumers.get(p.qid, [])
    same = any(inv == L.invoice.invoice_no for inv, _ in earlier)
    L.finding(Category.DUPLICATE_CHARGE, "duplicates.within_invoice" if same else "duplicates.across_invoices",
              f"{p.service_code} for {p.well} on {p.date} (report {p.report_ids[0]}) already charged on "
              + ", ".join(ref for _, ref in earlier), observed=str(L.line.quantity), expected="0 (already charged)", impact=impact,
              evidence=(ev, priced_evidence(p)), clause_ids=("CL-29",))
    L.not_payable()


def _quantity(L: _Line, p: PricedQuantity, available: Decimal, ledger: Ledger, ev: Evidence) -> Decimal | None:
    """The payable quantity; None when nothing is payable (the line is settled)."""
    line = L.line
    billed = line.quantity
    if ledger.consumed.get(p.qid) and available <= 0:
        _duplicate(L, p, ledger, line.amount_cents, ev)
        return None
    if billed <= available:
        if billed < p.chargeable_quantity and not ledger.consumed.get(p.qid):
            L.a.observations.append(f"billed {billed} below the {p.chargeable_quantity} the report supports (a claim below the record is not a finding)")
        return billed
    if ledger.consumed.get(p.qid):
        excess = billed - available
        L.finding(Category.DUPLICATE_CHARGE, "duplicates.partial", f"{excess} of the {billed} {p.unit} already charged on "
                  + ", ".join(r for _, r in ledger.consumers[p.qid]), observed=str(billed), expected=str(available),
                  evidence=(ev, priced_evidence(p)), clause_ids=("CL-29",))
        return available
    unit_is_metre = p.unit == "metre"
    if unit_is_metre and billed <= p.chargeable_quantity * METRE_TOLERANCE:
        L.a.observations.append(f"{billed} m billed against {p.chargeable_quantity} m recorded: within the 1 per cent of 25A, payable as charged")
        return billed
    limit = next((s for s in p.quantity_steps if s.name == "daily limit"), None)
    if limit is not None and billed > limit.output_cents:
        L.finding(Category.DAILY_LIMIT_EXCEEDED, "limits.daily_limit", f"{billed} {p.unit} charged; the daily limit is {limit.output_cents} (Schedule 3 Part 5)",
                  observed=str(billed), expected=str(available), evidence=(ev, priced_evidence(p)), clause_ids=("CL-22",))
    else:
        steps = ", ".join(s.name for s in p.quantity_steps)
        L.finding(Category.QUANTITY_EXCEEDS_RECORD, "quantity.exceeds_record",
                  f"{billed} {p.unit} charged; the report supports {p.chargeable_quantity}" + (f" ({steps})" if steps else "")
                  + ("; beyond the 1 per cent 25A allows" if unit_is_metre else ""),
                  observed=str(billed), expected=str(available), evidence=(ev, priced_evidence(p)),
                  clause_ids=("CL-25A",) if unit_is_metre else ("CL-21", "CL-21A", "CL-22", "CL-30"))
    return available


def _expected_rate(L: _Line, p: PricedQuantity) -> tuple[int, tuple[int, ...]]:
    """The rate in force for this charge and the other side of Clause 36A (for diagnosis)."""
    rate = p.parts[0].rate_cents
    if p.rate_without_retroactive_cents is None:
        return rate, ()
    before_issue = L.ctx.retro_issue is not None and L.invoice.invoice_date is not None and L.invoice.invoice_date < L.ctx.retro_issue
    return (p.rate_without_retroactive_cents, (rate,)) if before_issue else (rate, (p.rate_without_retroactive_cents,))


def _price(L: _Line, p: PricedQuantity, payable: Decimal, ev: Evidence) -> None:
    ctx, line = L.ctx, L.line
    billed_rate = cents(line.unit_rate)
    conditional = p.status is PricingStatus.EVIDENCE_NOT_PROVIDED
    reference = p
    if conditional and p.service_code in ctx.bundle.class_services:
        by_class = ctx.bundle.conditional(p.qid)
        claimed = L.invoice.well_class_stated
        rates = {c: _expected_rate(L, q)[0] for c, q in by_class.items() if q.parts}
        by_rate = ", ".join(f"{c} {r / 100:.2f}" for c, r in sorted(rates.items()))
        if claimed not in rates:
            # the invoice's well class is a descriptive field (not in cl. 34 or the Appendix B form); the class is the call-off's
            L.finding(Category.ENTITLEMENT_UNVERIFIED, "entitlement.descriptive_class_not_a_contract_class",
                      f"the invoice describes the well as {claimed!r}, which is not a contract class; the class is the call-off's (P2, P3), which is "
                      f"not provided. Billed rate {billed_rate / 100:.2f}; rates by class: {by_rate}",
                      outcome=Outcome.QUERY, observed=f"{billed_rate / 100:.2f}", expected=by_rate, affects=False, blocks=True)
            if billed_rate not in rates.values():
                _rate_finding(L, next(iter(by_class.values())), payable, billed_rate, ev, conditional=True)
            L.a.status = LineStatus.UNDETERMINED
            return
        reference = by_class[claimed]
        if billed_rate != rates[claimed] and billed_rate in rates.values():
            # not a finding: the descriptive class proves nothing either way (cl. 34, Appendix B, P2, P3); kept for reviewers
            other = sorted(c for c, r in rates.items() if r == billed_rate)
            L.finding(Category.ENTITLEMENT_UNVERIFIED, "entitlement.descriptive_class_differs",
                      f"the invoice describes the well as {claimed}; the billed rate {billed_rate / 100:.2f} is the {', '.join(other)} rate. The "
                      "invoice's well class is descriptive, not part of the contractual billing basis, and the class is the call-off's (P2, P3), "
                      f"which is not provided: neither the described nor the billed class is shown correct. Rates by class: {by_rate}",
                      outcome=Outcome.QUERY, observed=f"{billed_rate / 100:.2f} ({', '.join(other)})", expected=by_rate,
                      affects=False, blocks=True, evidence=(ev, priced_evidence(reference, rates[claimed])))
            L.a.observations.append(f"conditional amount taken at the described class {claimed} ({rates[claimed] / 100:.2f}), as for every "
                                    "conditional line; the billed rate is another class's, so this line's conditional amount differs from its billed amount")
            billed_rate_consistent = True
        else:
            billed_rate_consistent = billed_rate == rates[claimed]
        _entitlement(L, p, f"well class {claimed} as claimed (unverified); the call-off is not provided")
        if not billed_rate_consistent:
            _rate_finding(L, reference, payable, billed_rate, ev, conditional=True)
    elif conditional:
        if not p.parts:
            L.a.status = LineStatus.UNDETERMINED
            L.a.observations.append(f"no conditional price: {p.reason}")
            return
        _entitlement(L, p, "performance-drilled section nominated in the call-off (not provided)")
        if billed_rate != _expected_rate(L, p)[0]:
            _rate_finding(L, p, payable, billed_rate, ev, conditional=True)
    else:
        if billed_rate != _expected_rate(L, p)[0]:
            _rate_finding(L, p, payable, billed_rate, ev, conditional=False)
    rate, _ = _expected_rate(L, reference)
    amount = half_even_cents(payable * rate)
    L.a.payable_quantity, L.a.contract_rate_cents, L.a.amount_cents = payable, rate, amount
    if L.a.status is not LineStatus.UNDETERMINED:
        L.a.status = LineStatus.CONDITIONAL if conditional else LineStatus.DETERMINED
    if reference.rate_without_retroactive_cents is not None and rate == reference.rate_without_retroactive_cents != reference.parts[0].rate_cents:
        L.a.retro_difference_cents = half_even_cents(payable * reference.parts[0].rate_cents) - amount


def _entitlement(L: _Line, p: PricedQuantity, what: str) -> None:
    L.finding(Category.ENTITLEMENT_UNVERIFIED, "entitlement.calloff_not_provided",
              f"{p.service_code}: payable only if the call-off establishes the {what}; the billed figures are consistent with that claim",
              outcome=Outcome.QUERY, affects=False, blocks=True, evidence=(priced_evidence(p),))


def _rate_finding(L: _Line, p: PricedQuantity, payable: Decimal, billed_rate: int, ev: Evidence, conditional: bool) -> None:
    expected, alt = _expected_rate(L, p)
    d = diagnose(L.ctx.terms, p.service_code, p.parts[0], billed_rate, expected, alt)
    impact = half_even_cents(payable * billed_rate) - half_even_cents(payable * expected)
    retro = " (Clause 36A: invoiced before Amendment No. 3 was issued, so the rate then in force applies)" if alt and expected == p.rate_without_retroactive_cents else ""
    L.finding(d.category, d.rule, f"billed rate {billed_rate / 100:.2f}; the contract rate in force is {expected / 100:.2f}{retro}: {d.explanation}"
              + ("; conditional on the claimed entitlement, but no entitlement produces the billed rate" if conditional else ""),
              observed=f"{billed_rate / 100:.2f}", expected=f"{expected / 100:.2f}", impact=impact,
              affects=not conditional, blocks=conditional, evidence=(ev, priced_evidence(p, expected)),
              clause_ids=("BR-SOV", "BR-36A") if alt else ("BR-SOV",))


def _arithmetic(L: _Line) -> None:
    line = L.line
    stated = half_even_cents(line.quantity * line.unit_rate * 100)
    if stated != line.amount_cents:
        L.finding(Category.LINE_ARITHMETIC, "arithmetic.line", f"{line.quantity} x {line.unit_rate} = {stated / 100:.2f}, charged {line.amount_cents / 100:.2f}",
                  observed=f"{line.amount_cents / 100:.2f}", expected=f"{stated / 100:.2f}", impact=line.amount_cents - stated)


def _match_pd210(L: _Line, report: DailyReport, ledger: Ledger, dry: bool) -> None:
    """PD-210: the billed depth interval against the metres the report records in each Schedule 2 band (cl. 23)."""
    ctx, line = L.ctx, L.line
    ev = report_evidence(report)
    lo, hi = line.depth_from_m, line.depth_to_m
    earlier = [(f, t, inv, ref) for f, t, inv, ref in ledger.pd210.get(line.well_name, []) if f < hi and lo < t]
    candidates = []
    for p in ctx.bundle.at_report(report.report_id, PD210):
        d = dict(ctx.bundle.quantities[p.qid].detail)
        a, b = int(d["from_m"]), int(d["to_m"])
        overlap = min(hi, b) - max(lo, a)
        if overlap > 0:
            candidates.append((p, a, b, overlap))
    if earlier:
        same = any(inv == L.invoice.invoice_no for *_, inv, _ in earlier)
        L.finding(Category.DUPLICATE_CHARGE, "duplicates.within_invoice" if same else "duplicates.across_invoices",
                  f"metres {lo}-{hi} on {line.well_name} overlap metres already charged on " + ", ".join(r for *_, r in earlier),
                  impact=line.amount_cents, evidence=(ev,), clause_ids=("CL-29",))
        L.not_payable()
        return
    if dry:
        return
    ledger.pd210.setdefault(line.well_name, []).append((lo, hi, L.invoice.invoice_no, line.line_ref))
    if not candidates:
        L.finding(Category.UNSUPPORTED_SERVICE, "identification.no_report_evidence",
                  f"report {report.report_id} records no drilling between {lo} m and {hi} m", impact=line.amount_cents, evidence=(ev,), clause_ids=("CL-23",))
        L.not_payable()
        return
    statuses = {p.status for p, *_ in candidates}
    if statuses == {PricingStatus.NOT_CHARGEABLE}:
        p = candidates[0][0]
        L.finding(Category.SECTION_NOT_ELIGIBLE, "limits.not_chargeable", f"not chargeable: {p.reason}", impact=line.amount_cents,
                  evidence=(ev, priced_evidence(p)), clause_ids=("CL-23",))
        L.not_payable()
        return
    L.a.matched = tuple(p.qid for p, *_ in candidates)
    supported = Decimal(sum(o for *_, o in candidates))
    billed = line.quantity
    payable = billed
    if billed > supported:
        if billed <= supported * METRE_TOLERANCE:
            L.a.observations.append(f"{billed} m billed against {supported} m recorded: within the 1 per cent of 25A, payable as charged")
        else:
            L.finding(Category.QUANTITY_EXCEEDS_RECORD, "quantity.exceeds_record", f"{billed} m charged for {lo}-{hi} m; the report records {supported} m in that interval",
                      observed=str(billed), expected=str(supported), evidence=(ev,), clause_ids=("CL-23", "CL-25A"))
            payable = supported
    # conditional price: each band's rate under the eligibility the call-off would establish (class-independent unless AMB-02 = APPLY)
    claimed = L.invoice.well_class_stated
    priced = []
    for p, a, b, overlap in candidates:
        q = ctx.bundle.conditional(p.qid).get(claimed) or next(iter(ctx.bundle.conditional(p.qid).values()), None)
        if p.status is PricingStatus.NOT_CHARGEABLE or q is None or not q.parts:
            continue
        priced.append((q, overlap))
    if not priced:
        L.a.status = LineStatus.UNDETERMINED
        return
    _entitlement(L, candidates[0][0], "performance-drilled section nominated in the call-off (not provided)")
    remaining, amount = payable, 0
    for q, overlap in priced:
        take = min(Decimal(overlap), remaining)
        for part in q.parts:                      # volume tiers split a quantity; allocate metres in order
            use = min(part.quantity, take)
            amount += half_even_cents(use * part.rate_cents)
            take -= use
            remaining -= use
    billed_rate = cents(line.unit_rate)
    rates = {part.rate_cents for q, _ in priced for part in q.parts}
    if len(rates) == 1 and billed_rate != next(iter(rates)):
        q = priced[0][0]
        d = diagnose(ctx.terms, PD210, q.parts[0], billed_rate, next(iter(rates)))
        L.finding(d.category, d.rule, f"billed rate {billed_rate / 100:.2f}; the Schedule 2 rate for these metres is {next(iter(rates)) / 100:.2f}: {d.explanation}"
                  "; conditional on the nomination, but no nomination produces the billed rate",
                  observed=f"{billed_rate / 100:.2f}", expected=f"{next(iter(rates)) / 100:.2f}", impact=half_even_cents(payable * billed_rate) - amount,
                  affects=False, blocks=True, evidence=(ev, priced_evidence(q, next(iter(rates)))), clause_ids=("CL-23",))
    elif len(rates) > 1 and half_even_cents(billed * line.unit_rate) != amount:
        L.a.observations.append(f"interval spans {len(rates)} rates; compared by amount only")
    L.a.payable_quantity, L.a.amount_cents = payable, amount
    L.a.contract_rate_cents = next(iter(rates)) if len(rates) == 1 else None
    L.a.status = LineStatus.CONDITIONAL if any(p.status is PricingStatus.EVIDENCE_NOT_PROVIDED for p, *_ in candidates) else LineStatus.DETERMINED
