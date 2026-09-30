"""Contract-driven ambiguity handling: Appendix G under each reading, the Part E context rule, later dependencies.

The vocabulary is always read from the contract model (ContractTerms.appendix_g). The only structure
added here is the row shift that AMB-17 reading B describes, expressed over contract codes.
"""

from dataclasses import dataclass

from contractor_audit.domains.drilling.contract.models import ContractTerms, RateBasis, ServiceDefinition

# AMB-17 reading B: the LWD "logged" rows are shifted by one line. Codes in printed row order; LH-714
# (LWD resistivity tool, lost) follows LW-410 (LWD resistivity).
LWD_LOGGED_ROWS = ("LW-410", "LW-411", "LW-412")
LWD_LOST_COMPANION = {"LW-410": "LH-714"}


@dataclass(frozen=True)
class Vocabulary:
    """Report term -> contract codes, for one Appendix G reading."""
    reading: str
    codes: dict[str, tuple[str, ...]]

    def rental_codes(self, terms: ContractTerms, term: str) -> tuple[str, ...]:
        return tuple(c for c in self.codes.get(term, ()) if terms.services[c].rate_basis is not RateBasis.CLAUSE_31)

    def lost_codes(self, terms: ContractTerms, term: str) -> tuple[str, ...]:
        return tuple(c for c in self.codes.get(term, ()) if terms.services[c].rate_basis is RateBasis.CLAUSE_31)

    def term_for(self, code: str) -> tuple[str, ...]:
        return tuple(t for t, codes in self.codes.items() if code in codes)


def literal_vocabulary(terms: ContractTerms) -> Vocabulary:
    words = dict.fromkeys(m.report_term for m in terms.appendix_g)
    return Vocabulary("LITERAL", {w: terms.codes_for_report_term(w) for w in words})


def shifted_vocabulary(terms: ContractTerms) -> Vocabulary:
    """Reading B of AMB-17: each LWD logged row's printed term belongs to the row above; the first has none."""
    literal = literal_vocabulary(terms)
    printed = {code: literal.term_for(code) for code in LWD_LOGGED_ROWS}
    shifted_codes = set(LWD_LOGGED_ROWS) | set(LWD_LOST_COMPANION.values())
    codes = {t: tuple(c for c in cs if c not in shifted_codes) for t, cs in literal.codes.items()}
    for upper, lower in zip(LWD_LOGGED_ROWS, LWD_LOGGED_ROWS[1:]):
        for term in printed[lower]:
            codes[term] = tuple(sorted(codes[term] + (upper,) + ((LWD_LOST_COMPANION[upper],) if upper in LWD_LOST_COMPANION else ())))
    return Vocabulary("LWD_ROWS_SHIFTED", codes)


def vocabularies(terms: ContractTerms) -> dict[str, Vocabulary]:
    return {"LITERAL": literal_vocabulary(terms), "LWD_ROWS_SHIFTED": shifted_vocabulary(terms)}


def reading_dependent_terms(vocabs: dict[str, Vocabulary]) -> set[str]:
    """Terms whose codes differ between the Appendix G readings."""
    literal, shifted = vocabs["LITERAL"], vocabs["LWD_ROWS_SHIFTED"]
    return {t for t in literal.codes if set(literal.codes[t]) != set(shifted.codes.get(t, ()))}


def surprising_pairings(ambiguity_issue: str, terms: ContractTerms) -> set[str]:
    """Terms the AMB-17 issue text itself lists as surprising (read from the register, not restated)."""
    return {m.report_term for m in terms.appendix_g if f"'{m.report_term}'" in ambiguity_issue}


def later_dependencies(service: ServiceDefinition, day_status: str | None) -> tuple[str, ...]:
    """Later-phase switches that will affect how a quantity of this service is used (never its value here)."""
    deps = []
    if service.rate_basis is RateBasis.SCHEDULE_2:
        deps += ["pd210_class_factor", "volume_tier_scope", "contract_year_2", "calloff_evidence"]
    if service.rate_basis is RateBasis.CLAUSE_31:
        deps += ["lih_hours", "lih_replacement_value"]
    if service.unit == "hour":
        deps.append("rig_up_hour")
    if service.indexed:
        deps.append("rig_services_index")
    if service.monthly_republished_by:
        deps.append("monthly_rate_basis")
    if service.code in ("DD-120", "DD-101"):
        deps.append("dd120_rate_from_feb_2026")
    if service.rate_discounted_by:
        deps.append("principal_discount_combination")
    if service.section_rated and day_status == "Standby":
        deps.append("standby_section_factor")
    return tuple(dict.fromkeys(deps))
