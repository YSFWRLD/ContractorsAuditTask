"""Once-per-well quantities (Clause 27), derived exactly once per well from its reports.

Which services are charged once per well, and on which day, is read from the contract model
(Schedule 3 Part 6 and each service's Clause 27 timing), not restated here.
"""

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DailyReport
from contractor_audit.domains.drilling.interpretation.ambiguity import Vocabulary
from contractor_audit.domains.drilling.interpretation.common import make_quantity
from contractor_audit.domains.drilling.interpretation.models import Basis, MappingStatus, Quantity, Scope
from contractor_audit.domains.drilling.interpretation.provenance import field_ref
from contractor_audit.domains.drilling.interpretation.service_mapping import READING_SWITCH

LWD_CONDITION = "only where logging while drilling was run"


def lwd_reports(reports: list[DailyReport], terms: ContractTerms, vocab: Vocabulary) -> list[DailyReport]:
    """Reports on which a word the vocabulary maps to an LWD logging service (a metre-rated LW code) is in the hole."""
    lwd_words = {t for t, codes in vocab.codes.items() for c in codes
                 if c.startswith("LW-") and terms.services[c].unit == "metre"}
    return [r for r in reports if r.operations and set(r.operations.in_the_hole) & lwd_words]


def well_quantities(terms: ContractTerms, well: str, reports: list[DailyReport], vocabs: dict[str, Vocabulary]) -> list[Quantity]:
    reports = sorted((r for r in reports if r.date), key=lambda r: r.date)
    if not reports:
        return []
    first, last = reports[0], reports[-1]
    q: list[Quantity] = []
    for code, service in sorted(terms.services.items()):
        if not service.once_per_well or not service.charge_timing:
            continue
        on_first = "first day on the well" in service.charge_timing
        day_report = first if on_first else last
        derivation = "FIRST_DAY_ON_WELL" if on_first else "LAST_DAY_ON_WELL"
        evidence = (field_ref(day_report, "HEADER", "Date"), field_ref(day_report, "HEADER", "Well"))
        if LWD_CONDITION not in service.charge_timing:
            q.append(make_quantity(terms, code, 1, Basis.WELL, Scope.WELL, well=well, day=day_report.date, reports=(day_report,),
                                   derivation=derivation, clauses=("27", "Schedule 3 Part 6"), evidence=evidence, status=MappingStatus.IDENTIFIED))
            continue
        by_reading = {reading: lwd_reports(reports, terms, vocab) for reading, vocab in vocabs.items()}
        same = len({bool(v) for v in by_reading.values()}) == 1   # the readings agree on whether LWD was run
        for reading, runs_lwd in by_reading.items():
            if not runs_lwd or (same and reading != next(iter(vocabs))):
                continue
            tag = () if same else ((READING_SWITCH, reading),)
            q.append(make_quantity(terms, code, 1, Basis.WELL, Scope.WELL, well=well, day=day_report.date, reports=(day_report,),
                                   derivation=derivation + "_WITH_LWD", clauses=("27", "Schedule 3 Part 6"),
                                   evidence=evidence + (field_ref(runs_lwd[0], "A", "In the hole"),),
                                   status=MappingStatus.IDENTIFIED if same else MappingStatus.UNRESOLVED_INTERPRETATION,
                                   readings=tag, ambiguity_ids=() if same else ("AMB-17",),
                                   detail=(("lwd_reports", str(len(runs_lwd))), ("first_lwd_report", runs_lwd[0].report_id))))
    return q
