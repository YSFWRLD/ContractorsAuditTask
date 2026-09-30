"""Once-per-BHA-run quantities, derived exactly once per (well, run) from the reconstructed runs.

Part B values repeat on every day of a run; they are read from one report of the run, never summed.
"""

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DailyReport
from contractor_audit.domains.drilling.ingestion.timelines import BhaRun
from contractor_audit.domains.drilling.interpretation.ambiguity import Vocabulary
from contractor_audit.domains.drilling.interpretation.common import make_quantity, record_part, signed
from contractor_audit.domains.drilling.interpretation.models import Basis, MappingStatus, Quantity, Scope
from contractor_audit.domains.drilling.interpretation.provenance import field_ref
from contractor_audit.domains.drilling.interpretation.service_mapping import READING_SWITCH

DD111, DD110, LW420, HC630, RM510, RM511 = "DD-111", "DD-110", "LW-420", "HC-630", "RM-510", "RM-511"


def run_quantities(terms: ContractTerms, run: BhaRun, reports: list[DailyReport], vocabs: dict[str, Vocabulary],
                   reading_dependent: frozenset[str]) -> list[Quantity]:
    by_date = {r.date: r for r in reports}
    first = by_date.get(run.recorded_first) or reports[0]
    last = by_date.get(run.recorded_last) or reports[-1]
    tools = set(first.bha_run.tools_in_run)
    literal = vocabs["LITERAL"]
    q: list[Quantity] = []
    common = dict(well=run.well, run=run.run)

    # DD-111: once for each run carrying a positive displacement motor, on its last day (cl. 26)
    pdm_terms = set(literal.term_for(DD110))
    if tools & pdm_terms:
        q.append(make_quantity(terms, DD111, 1, Basis.RUN, Scope.RUN, day=last.date, reports=(last,), derivation="RUN_CARRYING_PDM",
                               clauses=("26", "T5"), evidence=(field_ref(last, "B", "Run"), field_ref(last, "B", "Tools in run"), field_ref(last, "B", "Run last day")),
                               status=MappingStatus.IDENTIFIED_BY_CONTEXT, conditions=(record_part(last, "B"), signed(last)),
                               detail=(("pdm_term", ",".join(sorted(tools & pdm_terms))),), **common))
    # LW-420: once for each run carrying a radioactive source, on its first day (cl. 26); Part D is its record
    if first.bha_run.radioactive_source_carried:
        q.append(make_quantity(terms, LW420, 1, Basis.RUN, Scope.RUN, day=first.date, reports=(first,), derivation="RUN_CARRYING_SOURCE",
                               clauses=("26", "H6"), evidence=(field_ref(first, "B", "Run"), field_ref(first, "B", "Radioactive source carried"), field_ref(first, "B", "Run first day")),
                               status=MappingStatus.IDENTIFIED, conditions=(record_part(first, "D"), signed(first)), **common))
    # HC-630 under hc630_basis = PER_BHA_RUN: once for a run whose reports record a clean-out run
    cleanout_days = [r for r in reports if r.operations and r.operations.clean_out_runs]
    if cleanout_days:
        q.append(make_quantity(terms, HC630, 1, Basis.RUN, Scope.RUN, day=cleanout_days[0].date, reports=tuple(cleanout_days), derivation="RUN_WITH_CLEAN_OUT",
                               clauses=("Schedule 8",), evidence=tuple(field_ref(r, "A", "Clean-out runs") for r in cleanout_days),
                               status=MappingStatus.IDENTIFIED, readings=(("hc630_basis", "PER_BHA_RUN"),), ambiguity_ids=("AMB-19",), **common))
    # metres under metre_source = PART_B_RUN_METRES: the Part B figure once per run, never summed over days
    logged, reamed = first.bha_run.metres_logged or 0, first.bha_run.metres_reamed or 0
    readings = tuple(vocabs)
    for reading in readings:
        vocab = vocabs[reading]
        for term in sorted(tools):
            dependent = term in reading_dependent
            if not dependent and reading != readings[0]:
                continue
            tag = (("metre_source", "PART_B_RUN_METRES"),) + (((READING_SWITCH, reading),) if dependent else ())
            for code in vocab.rental_codes(terms, term):
                if terms.services[code].unit == "metre" and logged:
                    q.append(make_quantity(terms, code, logged, Basis.METRE, Scope.RUN, day=first.date, reports=(first,), derivation="PART_B_METRES_LOGGED",
                                           clauses=("24", "Schedule 5 Part B"), evidence=(field_ref(first, "B", "Metres logged"), field_ref(first, "B", "Tools in run")),
                                           status=MappingStatus.UNRESOLVED_INTERPRETATION if dependent else MappingStatus.IDENTIFIED,
                                           conditions=(record_part(first, "B"),), readings=tag, ambiguity_ids=("AMB-24",) + (("AMB-17",) if dependent else ()),
                                           detail=(("term", term),), **common))
                if code == RM511 and reamed:
                    q.append(make_quantity(terms, RM510, reamed, Basis.METRE, Scope.RUN, day=first.date, reports=(first,), derivation="PART_B_METRES_REAMED",
                                           clauses=("25", "Schedule 5 Part B"), evidence=(field_ref(first, "B", "Metres reamed"), field_ref(first, "B", "Tools in run")),
                                           status=MappingStatus.IDENTIFIED, conditions=(record_part(first, "B"),), readings=tag,
                                           ambiguity_ids=("AMB-24",), detail=(("underreamer_term", term),), **common))
    return q
