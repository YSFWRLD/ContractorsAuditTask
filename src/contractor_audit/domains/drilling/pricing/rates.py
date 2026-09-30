"""The Schedule 1 rate in force for a service on its service date (Schedule of Variations and each instrument).

`ContractTerms.rate_statements_on` lists every statement that speaks to the date; this module picks one under
the selected reading of the instruments' "the later governs" rule (switch dd120_rate_from_feb_2026, AMB-07):

    LATER_ISSUED_GOVERNS     the statement from the instrument issued last governs
    LATER_EFFECTIVE_GOVERNS  the statement that took effect last governs (monthly rates take effect on their month)
    MONTHLY_TABLE_SEPARATE   a monthly re-publication governs from its first month; otherwise the later-issued statement

The three agree for every service and date except DD-120 from April 2026, where Amendment No. 3 and the
Supplement No. 2 monthly table overlap.
"""

from datetime import date

from contractor_audit.domains.drilling.contract.models import ContractTerms, RateStatement, StatementKind
from contractor_audit.domains.drilling.pricing.models import RateSource


def _pick(statements: list[RateStatement], reading: str) -> RateStatement:
    issued = lambda s: s.issued or date.min  # noqa: E731  (the base contract precedes every instrument)
    if reading == "LATER_EFFECTIVE_GOVERNS":
        return max(statements, key=lambda s: (s.effective, issued(s)))
    monthly = [s for s in statements if s.kind is StatementKind.MONTHLY]
    if reading == "MONTHLY_TABLE_SEPARATE" and monthly:
        return max(monthly, key=issued)
    if reading in ("LATER_ISSUED_GOVERNS", "MONTHLY_TABLE_SEPARATE"):
        return max(statements, key=lambda s: (issued(s), s.effective))
    raise ValueError(f"unknown reading {reading!r}")


def resolve(terms: ContractTerms, code: str, service_date: date, reading: str, exclude: frozenset[str] = frozenset()) -> RateSource | None:
    """The governing statement, or None when Schedule 1 prints no rate for the service. `exclude` drops instruments by id."""
    statements = [s for s in terms.rate_statements_on(code, service_date) if s.source not in exclude]
    if not statements:
        return None
    chosen = _pick(statements, reading)
    page = terms.services[code].provenance[0].page if chosen.source == "SCHEDULE_1" else terms.instrument(chosen.source).page
    return RateSource(chosen.source, chosen.kind.value, chosen.rate_cents, chosen.effective, chosen.issued,
                      chosen.month, page, tuple(f"{s.source}:{s.kind.value}:{s.rate_cents}" + (f":{s.month}" if s.month else "") for s in statements))


def retroactive_instruments(terms: ContractTerms) -> frozenset[str]:
    return frozenset(i.id for i in terms.instruments if i.retroactive)
