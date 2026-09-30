"""The drilling audit end to end: contract-side prices, one audit pass, the dependency re-runs, graded results."""

from dataclasses import dataclass

from contractor_audit.domains.drilling.audit.bundle import PricingBundle, build_bundle, rebundle
from contractor_audit.domains.drilling.audit.dependencies import Alternative, Measured, alternatives, measure
from contractor_audit.domains.drilling.audit.engine import audit
from contractor_audit.domains.drilling.audit.models import AuditRun
from contractor_audit.domains.drilling.audit.policy import AUDIT_SWITCHES, AuditPolicy, build_policy, reading_grades
from contractor_audit.domains.drilling.audit.results import InvoiceOutcome, finalize
from contractor_audit.domains.drilling.contract.models import Ambiguity, ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset
from contractor_audit.domains.drilling.interpretation.models import InterpretationResult
from contractor_audit.domains.drilling.interpretation.switches import Switch
from contractor_audit.domains.drilling.pricing.affected import affected_services
from contractor_audit.domains.drilling.pricing.selection import Choice, Source, build_selection
from contractor_audit.shared.findings import ConfidenceBand


@dataclass(frozen=True)
class AuditReport:
    policy: AuditPolicy
    grades: dict[str, ConfidenceBand]
    bundle: PricingBundle
    run: AuditRun
    measured: Measured
    outcomes: list[InvoiceOutcome]


def run_audit(dataset: DrillingDataset, terms: ContractTerms, result: InterpretationResult, switches: dict[str, Switch],
              ambiguities: dict[str, Ambiguity], approved: dict[str, Choice], approved_raw: dict, recommendations: dict,
              measure_dependencies: bool = True) -> AuditReport:
    selection = build_selection(switches, {k: v for k, v in approved.items() if k not in AUDIT_SWITCHES})
    policy = build_policy(selection, approved_raw, switches)
    grades = reading_grades(policy, switches, ambiguities, recommendations)
    bundle = build_bundle(result, terms, switches, selection)
    base = audit(dataset, terms, bundle, policy)

    def rerun(alt: Alternative) -> AuditRun:
        if alt.switch in AUDIT_SWITCHES:
            return audit(dataset, terms, bundle, policy.with_audit(alt.switch, alt.value))
        alt_selection = selection.with_choice(alt.switch, alt.value, Source.HYPOTHETICAL)
        alt_bundle = rebundle(bundle, result, terms, switches, alt_selection, affected_services(alt.switch, terms, result))
        return audit(dataset, terms, alt_bundle, policy.with_selection(alt_selection))

    measured = measure(base, alternatives(policy, switches, grades) if measure_dependencies else [], rerun)
    return AuditReport(policy, grades, bundle, base, measured, finalize(base, measured))
