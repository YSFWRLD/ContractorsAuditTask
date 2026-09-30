"""Which services a switch can change: the scope a hypothetical reading is repriced over (sensitivity, audit dependencies)."""

from contractor_audit.domains.drilling.contract.models import ContractTerms, RateBasis
from contractor_audit.domains.drilling.interpretation.models import InterpretationResult


def affected_services(name: str, terms: ContractTerms, result: InterpretationResult) -> set[str]:
    s = terms.services
    rules = {
        "rig_up_hour": lambda d: d.unit == "hour",
        "pd210_class_factor": lambda d: d.rate_basis is RateBasis.SCHEDULE_2,
        "volume_tier_scope": lambda d: d.rate_basis is RateBasis.SCHEDULE_2,
        "contract_year_2": lambda d: d.rate_basis is RateBasis.SCHEDULE_2,
        "standby_section_factor": lambda d: d.section_rated,
        "rig_services_index": lambda d: d.indexed,
        "dd120_rate_from_feb_2026": lambda d: bool(d.rate_amended_by or d.monthly_republished_by),
        "monthly_rate_basis": lambda d: bool(d.monthly_republished_by),
        "lih_replacement_value": lambda d: d.rate_basis is RateBasis.CLAUSE_31,
        "lih_hours": lambda d: d.rate_basis is RateBasis.CLAUSE_31,
        "calloff_evidence": lambda d: d.class_rated or d.rate_basis is RateBasis.SCHEDULE_2,
    }
    if name in rules:
        codes = {code for code, d in s.items() if rules[name](d)}
        if name == "calloff_evidence":   # and every service whose eligibility needs a nominated section (PD-201)
            codes |= {q.service_code for q in result.quantities if any(c.code == "PERFORMANCE_SECTION_NOMINATED" for c in q.conditions)}
        return codes
    return {q.service_code for q in result.quantities if any(sw == name for sw, _ in q.readings)}   # Phase 3 quantity switches
