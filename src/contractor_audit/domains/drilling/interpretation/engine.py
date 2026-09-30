"""One interpretation pass over the Daily Drilling Reports. Takes reports and the contract, nothing billed."""

from collections.abc import Sequence

from contractor_audit.domains.drilling.contract.models import Ambiguity, ContractTerms
from contractor_audit.domains.drilling.ingestion.indexes import build_indexes
from contractor_audit.domains.drilling.ingestion.models import DailyReport, DrillingDataset
from contractor_audit.domains.drilling.ingestion.timelines import bha_runs
from contractor_audit.domains.drilling.interpretation.ambiguity import reading_dependent_terms, surprising_pairings, vocabularies
from contractor_audit.domains.drilling.interpretation.lost_in_hole import lost_in_hole_quantities
from contractor_audit.domains.drilling.interpretation.models import InterpretationResult
from contractor_audit.domains.drilling.interpretation.quantities import daily_quantities
from contractor_audit.domains.drilling.interpretation.run_quantities import run_quantities
from contractor_audit.domains.drilling.interpretation.service_mapping import MappingContext, map_report
from contractor_audit.domains.drilling.interpretation.well_quantities import well_quantities


def interpret(reports: Sequence[DailyReport], terms: ContractTerms, ambiguities: dict[str, Ambiguity]) -> InterpretationResult:
    """Map every report's words to contract candidates and derive every evidence-backed quantity, under all readings."""
    vocabs = vocabularies(terms)
    readings = tuple(vocabs)
    ctx = MappingContext(terms, vocabs, frozenset(reading_dependent_terms(vocabs)), frozenset(surprising_pairings(ambiguities["AMB-17"].issue, terms)))
    parsed = [r for r in reports if r.report_id and r.operations and r.date and r.well]
    ix = build_indexes(DrillingDataset((), (), tuple(parsed), ()))
    mappings = {r.report_id: map_report(ctx, r) for r in parsed}
    quantities = []
    for r in parsed:
        quantities += daily_quantities(terms, r, mappings[r.report_id], readings)
        quantities += lost_in_hole_quantities(terms, r, mappings[r.report_id], list(ix.reports_by_well.get(r.well)), readings)
    for key, run in bha_runs(ix).items():
        quantities += run_quantities(terms, run, [ix.reports_by_id.one(i) for i in run.report_ids], vocabs, ctx.reading_dependent)
    for well in ix.reports_by_well.keys():
        quantities += well_quantities(terms, well, list(ix.reports_by_well.get(well)), vocabs)
    quantities.sort(key=lambda q: q.qid)
    all_mappings = tuple(m for r in parsed for m in mappings[r.report_id])
    return InterpretationResult(all_mappings, tuple(quantities), len(parsed))
