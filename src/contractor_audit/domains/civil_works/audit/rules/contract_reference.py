"""Check 1: the application belongs to this contract (reference and issuer)."""

from contractor_audit.domains.civil_works.audit.categories import Category
from contractor_audit.domains.civil_works.audit.models import RuleOutput
from contractor_audit.domains.civil_works.audit.rules.common import finding
from contractor_audit.shared.findings import Evidence


def check(ctx, payable) -> list:
    t = ctx.terms
    ag = ctx.data.raw_extraction["agreement"]
    ref_cite = ctx.cite_text("Agreement", ag["contract_ref"]["source_page"], ag["contract_ref"]["source_text"])
    sub_cite = ctx.cite_text("Agreement", ag["subcontractor"]["source_page"], ag["subcontractor"]["source_text"])
    out = []
    for app in ctx.data.applications:
        ev = (Evidence("application", app.application_no, f"contract_ref {app.contract_ref!r}; subcontractor {app.subcontractor!r}"),)
        if app.contract_ref != t.contract_ref:
            # The amendments are read into this Subcontract and carry its own reference (CW-2025-0417-CIV/S1 ...);
            # an instrument never changes the contract reference.
            out.append(RuleOutput(finding(Category.CONTRACT_REFERENCE_MISMATCH, app.application_no, "contract_reference.reference",
                                          f"Application quotes {app.contract_ref}; the Subcontract is {t.contract_ref} (instruments are {t.contract_ref}/S1 ... /A3).",
                                          observed=app.contract_ref, expected=t.contract_ref, citations=(ref_cite,), evidence=ev)))
        if app.subcontractor.casefold() != ag["subcontractor"]["value"].casefold():
            out.append(RuleOutput(finding(Category.CONTRACT_REFERENCE_MISMATCH, app.application_no, "contract_reference.issuer",
                                          f"Issued by {app.subcontractor!r}, not the Subcontractor named in the Agreement.",
                                          observed=app.subcontractor, expected=ag["subcontractor"]["value"], citations=(sub_cite,), evidence=ev)))
    return out
