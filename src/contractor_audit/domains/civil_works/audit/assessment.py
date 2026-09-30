"""Dependencies, confidence and the expected-total policy, from runs under every alternative reading.

Dependencies are measured, not declared: the audit is re-run with one reading flipped at a time
(every Phase 2 pricing switch and every audit switch), and a finding or total that changes records
that reading as a dependency.

Application conclusions:
* flagged: at least one finding. One finding suffices, so the flag's confidence is that of its
  best-supported finding; when a corrected total is published, the row confidence is further
  capped by the weakest reading that total depends on. An application therefore does not simply
  inherit its most confident finding.
* unflagged: HIGH unless some unresolved reading would flag it; then that reading's grade.
* a finding in NO_CONSEQUENCE_CATEGORIES (timing / period statement) is capped at MEDIUM: the
  breach is certain, but the contract attaches no consequence to it.
* corrected total (flagged only): published only when every component is determined. Under the
  STRICT policy (production) any non-HIGH reading that changes the total blanks it; GRADED, kept
  only for analysis, blanks only on LOW.
"""

import dataclasses
from dataclasses import dataclass, fields

from contractor_audit.domains.civil_works.audit.categories import CATEGORIES, NO_CONSEQUENCE_CATEGORIES, primary_key
from contractor_audit.domains.civil_works.audit.confidence import grade
from contractor_audit.domains.civil_works.audit.context import AuditData
from contractor_audit.domains.civil_works.audit.engine import run_audit
from contractor_audit.domains.civil_works.audit.models import ApplicationAssessment, AuditRun
from contractor_audit.domains.civil_works.audit.options import (AUDIT_SWITCHES, WORKING_AUDIT_INTERPRETATION,
                                                                AuditInterpretation, TotalPolicy)
from contractor_audit.domains.civil_works.interpretation import (SWITCHES, WORKING_INTERPRETATION, CivilWorksInterpretation,
                                                                 alternatives)
from contractor_audit.shared.findings import ConfidenceBand, Dependency

_CATEGORY_ORDER = {c.value: i for i, c in enumerate(CATEGORIES)}
NO_CONSEQUENCE = {c.value for c in NO_CONSEQUENCE_CATEGORIES}


@dataclass(frozen=True)
class AlternativeRun:
    field: str
    working: str
    alternative: str
    band: ConfidenceBand
    run: AuditRun


@dataclass(frozen=True)
class AuditResult:
    base: AuditRun
    alternatives: tuple[AlternativeRun, ...]
    applications: tuple[ApplicationAssessment, ...]
    policy: TotalPolicy
    data: AuditData | None = None

    @property
    def findings(self):
        return tuple(f for a in self.applications for f in a.findings)


def run_alternatives(data: AuditData, interp: CivilWorksInterpretation = WORKING_INTERPRETATION,
                     audit_interp: AuditInterpretation = WORKING_AUDIT_INTERPRETATION) -> tuple[AlternativeRun, ...]:
    runs = []
    for f in fields(interp):
        for alt in alternatives(f.name):
            runs.append(AlternativeRun(f.name, getattr(interp, f.name).value, alt.value, grade(f.name),
                                       run_audit(data, interp.with_(**{f.name: alt}), audit_interp)))
    for f in fields(audit_interp):
        current = getattr(audit_interp, f.name)
        for alt in (v for v in type(current) if v != current):
            runs.append(AlternativeRun(f.name, current.value, alt.value, grade(f.name),
                                       run_audit(data, interp, audit_interp.with_(**{f.name: alt}))))
    return tuple(runs)


def _primary(findings) -> str:
    """The row's error_category: lowest (tier, fixed category precedence, line, rule); see categories.primary_key."""
    return min(findings, key=primary_key).category


# Mutually exclusive blank reason: data gaps first, then the least certain reading, then fixed switch order.
DATA_REASONS = ("rate_not_established", "payable_quantity_unresolved", "limit_allocation_unresolved")
_SWITCH_ORDER = {s.field: i for i, s in enumerate(SWITCHES + AUDIT_SWITCHES)}


def blank_reason_key(reason: str) -> tuple:
    if reason in DATA_REASONS:
        return (0, DATA_REASONS.index(reason), 0)
    switch = reason.split(":", 1)[1]
    return (1, grade(switch).rank, _SWITCH_ORDER.get(switch, 99))


def assess(data: AuditData, base: AuditRun, alt_runs: tuple[AlternativeRun, ...], policy: TotalPolicy = TotalPolicy.STRICT) -> AuditResult:
    alt_index = [(a, {f.key: f for f in a.run.findings}) for a in alt_runs]

    enriched = []
    for f in base.findings:
        deps = []
        for a, keyed in alt_index:
            other = keyed.get(f.key)
            if other is None:
                deps.append(Dependency(a.field, a.working, a.alternative, "finding_absent", a.band))
            elif other.impact_cents != f.impact_cents:
                deps.append(Dependency(a.field, a.working, a.alternative, "value_changes", a.band))
        confidence = ConfidenceBand.weakest(d.band for d in deps if d.effect == "finding_absent")
        if f.category in NO_CONSEQUENCE:
            confidence = ConfidenceBand.weakest([confidence, ConfidenceBand.MEDIUM])
        enriched.append(dataclasses.replace(f, dependencies=tuple(deps), confidence=confidence))

    by_app: dict[str, list] = {}
    for f in enriched:
        by_app.setdefault(f.invoice_id, []).append(f)
    alt_apps = [(a, {f.invoice_id for f in a.run.findings}) for a in alt_runs]
    unresolved_by_app: dict[str, list] = {}
    for u in base.unresolved:
        unresolved_by_app.setdefault(u.application_no, []).append(u.reason)

    assessments = []
    for app in data.applications:
        no = app.application_no
        findings = tuple(by_app.get(no, ()))
        total = base.contract_totals[no]
        total_deps = tuple(Dependency(a.field, a.working, a.alternative, "total_changes", a.band)
                           for a in alt_runs if a.run.contract_totals[no] != total)
        unresolved = sorted(set(unresolved_by_app.get(no, [])))
        if findings:
            strict_blank = [f"unresolved_interpretation:{d.switch}" for d in total_deps if d.band is not ConfidenceBand.HIGH]
            graded_blank = [f"unresolved_interpretation:{d.switch}" for d in total_deps if d.band is ConfidenceBand.LOW]
            if total is None:
                unresolved = unresolved or ["rate_not_established"]
            blank = sorted(set(unresolved + (strict_blank if policy is TotalPolicy.STRICT else graded_blank)), key=blank_reason_key)
            graded_total = None if (unresolved or graded_blank) else total
            expected = None if blank else total
            flag_band = ConfidenceBand.strongest(f.confidence for f in findings)
            band = flag_band if expected is None else ConfidenceBand.weakest([flag_band] + [d.band for d in total_deps])
            would_flag = ()
            outcome = "part-reject" if any(f.affects_total for f in findings) else "query"
            status = "undetermined" if expected is None else ("unchanged" if expected == app.application_total_cents else "corrected")
        else:
            would_flag = tuple(Dependency(a.field, a.working, a.alternative, "would_flag", a.band)
                               for a, apps in alt_apps if no in apps)
            band = ConfidenceBand.weakest(d.band for d in would_flag)
            expected = graded_total = app.application_total_cents
            blank = []
            outcome, status = "pass", "correct"
        assessments.append(ApplicationAssessment(
            application_no=no, billed_total_cents=app.application_total_cents, flagged=bool(findings),
            categories=tuple(sorted({f.category for f in findings}, key=lambda c: _CATEGORY_ORDER.get(c, 99))),
            primary_category=_primary(findings) if findings else "",
            expected_total_cents=expected, contract_total_cents=total, graded_total_cents=graded_total,
            blank_reasons=tuple(blank), confidence=band, findings=findings, total_dependencies=total_deps,
            would_flag_under=would_flag, outside_total=base.outside_total.get(no, ()),
            primary_blank_reason=blank[0] if blank else "", outcome=outcome, total_status=status))
    return AuditResult(base, alt_runs, tuple(assessments), policy, data)


def audit(data: AuditData, policy: TotalPolicy = TotalPolicy.STRICT) -> AuditResult:
    base = run_audit(data)
    return assess(data, base, run_alternatives(data), policy)
