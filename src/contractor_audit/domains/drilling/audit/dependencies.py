"""Which readings each conclusion depends on, measured by re-running the audit under every alternative.

For each approved pricing or quantity reading (text-resolved readings are not measured: the contract settles
them) and for each audit-phase reading, the audit is re-run with that one reading flipped. Only the services the
reading can affect are repriced. A base finding that disappears depends on the reading (`finding_absent`), unless
its line is still rejected under the alternative for another reason (`superseded`: the charge is wrong either
way). One whose amount changes depends on it for its value (`value_changes`). An unflagged invoice the alternative
would flag records `would_flag`, a flagged one it would clear `would_unflag`; a changed total `total_changes`.
AMB-13 is not flipped here: its effect is the conditional valuation itself.

The band a dependency carries: an approved pricing reading is a decision, so a conclusion resting on it is MEDIUM at
worst; an audit-phase reading keeps its own grade whether approved or not (the approval records the decision; it does
not remove the uncertainty the text leaves).
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from contractor_audit.domains.drilling.audit.categories import flags
from contractor_audit.domains.drilling.audit.models import AuditRun
from contractor_audit.domains.drilling.audit.policy import AUDIT_SWITCHES, AuditPolicy
from contractor_audit.domains.drilling.interpretation.switches import NOT_DERIVED, Switch
from contractor_audit.domains.drilling.pricing.selection import PRICING_SWITCHES, Source
from contractor_audit.shared.findings import ConfidenceBand, Dependency


@dataclass(frozen=True)
class Alternative:
    switch: str
    working: str
    value: str
    band: ConfidenceBand
    approved: bool          # the working reading is approved (a flip is then only sensitivity; it never blanks a total)

    @property
    def effective_band(self) -> ConfidenceBand:
        if self.approved and self.switch not in AUDIT_SWITCHES:
            return ConfidenceBand.strongest([self.band, ConfidenceBand.MEDIUM])
        return self.band


@dataclass
class Measured:
    finding_deps: dict[tuple, list[Dependency]] = field(default_factory=lambda: defaultdict(list))
    invoice_deps: dict[str, list[tuple[Alternative, str]]] = field(default_factory=lambda: defaultdict(list))
    rows: list[dict] = field(default_factory=list)


def alternatives(policy: AuditPolicy, switches: dict[str, Switch], grades: dict[str, ConfidenceBand]) -> list[Alternative]:
    out = []
    for name in PRICING_SWITCHES:
        choice = policy.selection.choices.get(name)
        if name == "calloff_evidence" or choice is None or choice.source is not Source.APPROVED:
            continue
        out += [Alternative(name, choice.value, v, grades[name], True) for v in switches[name].values
                if v != choice.value and (name, v) not in NOT_DERIVED]
    for name in AUDIT_SWITCHES:
        current = policy.audit[name]
        out += [Alternative(name, current.value, v, grades[name], current.approved) for v in switches[name].values if v != current.value]
    return out


def _flagged(run: AuditRun) -> set[str]:
    return {i for i, a in run.invoices.items() if any(flags(f.category) for f in a.findings)}


def measure(base: AuditRun, alts: list[Alternative], rerun: Callable[[Alternative], AuditRun]) -> Measured:
    m = Measured()
    base_flagged = _flagged(base)
    for alt in alts:
        run = rerun(alt)
        flagged = _flagged(run)
        removed = added = changed_value = 0
        totals_changed, conditional_changed = [], []
        band = alt.effective_band
        for inv, a in base.invoices.items():
            b = run.invoices[inv]
            alt_findings = {f.key: f for f in b.findings}
            rejected_lines = {f.line_ref for f in b.findings if f.line_ref and flags(f.category)}
            for f in a.findings:
                g = alt_findings.get(f.key)
                if g is None:
                    effect = "superseded" if f.line_ref in rejected_lines else "finding_absent"
                    m.finding_deps[f.key].append(Dependency(alt.switch, alt.working, alt.value, effect, band))
                    removed += 1
                elif g.impact_cents != f.impact_cents:
                    m.finding_deps[f.key].append(Dependency(alt.switch, alt.working, alt.value, "value_changes", band))
                    changed_value += 1
            added += len(set(alt_findings) - {f.key for f in a.findings})
            if inv not in base_flagged and inv in flagged:
                m.invoice_deps[inv].append((alt, "would_flag"))
            if inv in base_flagged and inv not in flagged:
                m.invoice_deps[inv].append((alt, "would_unflag"))
            if (a.valuation.status, a.valuation.total_cents) != (b.valuation.status, b.valuation.total_cents):
                m.invoice_deps[inv].append((alt, "total_changes"))
                totals_changed.append(inv)
            if a.conditional.total_cents != b.conditional.total_cents:
                m.invoice_deps[inv].append((alt, "conditional_total_changes"))
                conditional_changed.append(inv)
        m.rows.append({"switch": alt.switch, "working": alt.working, "alternative": alt.value, "grade": alt.band.value,
                       "working_approved": alt.approved, "flags_added": sorted(flagged - base_flagged), "flags_removed": sorted(base_flagged - flagged),
                       "findings_removed": removed, "findings_added": added, "finding_values_changed": changed_value,
                       "totals_changed": totals_changed, "conditional_totals_changed": conditional_changed,
                       "below_record_lines": _below_record(run)})
    return m


def _below_record(run: AuditRun) -> dict[str, int]:
    """Lines billed below the quantity the report supports under this run's readings, by service (observations, not findings)."""
    out: dict[str, int] = defaultdict(int)
    for a in run.invoices.values():
        for l in a.lines:
            if any("below the" in o for o in l.observations):
                out[l.line.service_code] += 1
    return dict(sorted(out.items()))
