"""From an audit run and its measured dependencies to graded findings and one InvoiceResult per invoice.

Confidence is evidence quality (shared bands):
    a finding              its rule's own band, lowered to the band of every reading without which it disappears
                           (an approved reading counts as MEDIUM at worst, a working one at its own grade);
                           timing findings are capped at MEDIUM (the contract prices nothing off them)
    a flagged invoice      the strongest band among its flagging findings (any one of them makes it wrong), and no
                           stronger than any reading under which it would not be flagged at all
    an unflagged invoice   HIGH, lowered to the band of every reading that would flag it; MEDIUM when a charge's
                           entitlement rests on the missing call-off (AMB-13: its absence is certain, the class is not)

Corrected total (STRICT): published only when every component is determined from the contract and the reports,
and no unapproved (working) reading changes it. Otherwise blank, with the reasons. The conditional total (each
conditional charge at the contractor's claimed entitlement) is kept for analysis and never published as payable.
"""

from dataclasses import dataclass, replace

from contractor_audit.domains.drilling.audit.categories import NO_CONSEQUENCE_CAP, NO_CONSEQUENCE_CATEGORIES, Category, flags, primary_key
from contractor_audit.domains.drilling.audit.dependencies import Measured
from contractor_audit.domains.drilling.audit.models import AuditRun, InvoiceAudit, TotalStatus
from contractor_audit.shared.findings import ConfidenceBand, Finding, InvoiceResult, Outcome

ENTITLEMENT = Category.ENTITLEMENT_UNVERIFIED.value


@dataclass(frozen=True)
class InvoiceOutcome:
    result: InvoiceResult
    audit: InvoiceAudit
    outcome: Outcome
    band: ConfidenceBand
    primary: Finding | None
    findings: tuple[Finding, ...]              # graded
    total_status: str
    blank_reasons: tuple[str, ...]
    contract_total_cents: int | None           # the determined total, whether published or not
    conditional_total_cents: int | None        # claimed entitlement confirmed (analysis only)
    total_depends_on: tuple[str, ...]
    would_flag_under: tuple[str, ...]
    would_unflag_under: tuple[str, ...]


def grade(f: Finding, measured: Measured) -> Finding:
    deps = tuple(measured.finding_deps.get(f.key, ()))
    band = ConfidenceBand.weakest([f.confidence] + [d.band for d in deps if d.effect == "finding_absent"])
    if Category(f.category) in NO_CONSEQUENCE_CATEGORIES:
        band = ConfidenceBand.weakest([band, NO_CONSEQUENCE_CAP])
    return replace(f, dependencies=deps, confidence=band)


def finalize(run: AuditRun, measured: Measured) -> list[InvoiceOutcome]:
    out = []
    for inv, a in run.invoices.items():
        findings = tuple(sorted((grade(f, measured) for f in a.findings), key=primary_key))
        flagging = [f for f in findings if flags(f.category)]
        flagged = bool(flagging)
        deps = measured.invoice_deps.get(inv, [])
        would_flag = tuple(dict.fromkeys(f"{alt.switch}={alt.value}" for alt, effect in deps if effect == "would_flag"))
        would_unflag = tuple(dict.fromkeys(f"{alt.switch}={alt.value}" for alt, effect in deps if effect == "would_unflag"))
        unresolved_total = tuple(dict.fromkeys(alt.switch for alt, effect in deps if effect == "total_changes" and not alt.approved))
        if flagged:
            band = ConfidenceBand.weakest([ConfidenceBand.strongest(f.confidence for f in flagging)]
                                          + [alt.effective_band for alt, effect in deps if effect == "would_unflag"])
        else:
            bands = [alt.effective_band for alt, effect in deps if effect == "would_flag"]
            if any(f.category == ENTITLEMENT for f in findings):
                bands.append(ConfidenceBand.MEDIUM)
            band = ConfidenceBand.weakest(bands)
        v = a.valuation
        reasons = list(dict.fromkeys(_reason(r) for r in v.reasons))
        reasons += [f"unresolved_interpretation:{s}" for s in unresolved_total]
        expected = v.total_cents if v.status is TotalStatus.DETERMINED and not unresolved_total else None
        if not reasons and expected is None:
            reasons.append("undetermined")
        if expected is not None and not flagged and expected != a.invoice.total_cents:
            expected, reasons = None, ["unflagged_total_differs:review"]      # guard: never publish a silent correction
        outcome = (Outcome.PART_REJECT if any(f.outcome is Outcome.PART_REJECT for f in flagging) else
                   Outcome.QUERY if flagged or any(f.outcome is Outcome.QUERY for f in findings) else Outcome.PASS)
        primary = flagging[0] if flagging else None
        result = InvoiceResult(inv, flagged, a.invoice.total_cents or 0, expected, band.score, primary.category if primary else "", findings)
        out.append(InvoiceOutcome(result, a, outcome, band, primary, findings, v.status.value, tuple(reasons) if expected is None else (),
                                  v.total_cents, a.conditional.total_cents, tuple(dict.fromkeys(alt.switch for alt, e in deps if e == "total_changes")),
                                  would_flag, would_unflag))
    return out


def _reason(r: str) -> str:
    if r.startswith("entitlement_unverified"):
        return "entitlement_unverified:AMB-13"
    if r.startswith("undetermined_line"):
        return "undetermined_line"
    return r
