"""Report words -> contract service candidates (Appendix G), with an explicit status for every mapping.

Three report fields carry rig words: Part A "In the hole" (tools), Part A "Crew on tour" (crew roles) and
Part E "Lost in hole tool". Each occurrence becomes a MappingResult tied to the exact field it came from.
"""

from dataclasses import dataclass

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DailyReport
from contractor_audit.domains.drilling.interpretation.ambiguity import Vocabulary
from contractor_audit.domains.drilling.interpretation.models import FieldRef, MappingResult, MappingStatus, ServiceCandidate
from contractor_audit.domains.drilling.interpretation.provenance import field_ref

IN_THE_HOLE = ("A", "In the hole")
CREW = ("A", "Crew on tour")
LOST_TOOL = ("E", "Lost in hole tool")
READING_SWITCH = "appendix_g_reading"


@dataclass(frozen=True)
class MappingContext:
    terms: ContractTerms
    vocabs: dict[str, Vocabulary]         # Appendix G reading -> vocabulary
    reading_dependent: frozenset[str]     # terms whose codes differ between readings
    surprising: frozenset[str]            # terms AMB-17 lists as surprising pairings


def _codes(ctx: MappingContext, term: str, lost: bool, reading: str) -> tuple[str, ...]:
    vocab = ctx.vocabs[reading]
    return vocab.lost_codes(ctx.terms, term) if lost else vocab.rental_codes(ctx.terms, term)


def map_term(ctx: MappingContext, report: DailyReport, field: FieldRef, term: str, lost: bool) -> MappingResult:
    """Map one term in one field. `lost` is the Part E context (AMB-16): it selects the lost-in-hole rows."""
    literal = ctx.vocabs["LITERAL"]
    all_codes = literal.codes.get(term, ())
    note = ""
    if term in ctx.surprising and term not in ctx.reading_dependent:
        note = "AMB-17 lists this pairing as surprising; the contract offers no alternative, so it is read as printed"
    if term in ctx.reading_dependent:
        candidates = tuple(
            ServiceCandidate(code, term, report.report_id, field, MappingStatus.UNRESOLVED_INTERPRETATION, ("AMB-17",), ((READING_SWITCH, reading),))
            for reading in ctx.vocabs for code in _codes(ctx, term, lost, reading))
        missing = [r for r in ctx.vocabs if not _codes(ctx, term, lost, r)]
        reason = "depends on appendix_g_reading (AMB-17)" + (f"; no candidate under {', '.join(missing)}" if missing else "")
        return MappingResult(term, report.report_id, field, MappingStatus.UNRESOLVED_INTERPRETATION, candidates, reason)
    chosen = _codes(ctx, term, lost, "LITERAL")
    others = tuple(c for c in all_codes if c not in chosen)
    if not chosen:
        return MappingResult(term, report.report_id, field, MappingStatus.UNSUPPORTED, (),
                             "no Appendix G row for this term in this context" if all_codes else "term not in Appendix G")
    if len(chosen) > 1:
        cands = tuple(ServiceCandidate(c, term, report.report_id, field, MappingStatus.AMBIGUOUS, ("AMB-16",)) for c in chosen)
        return MappingResult(term, report.report_id, field, MappingStatus.AMBIGUOUS, cands, "several codes remain after the context rule")
    if others:
        context = "Part E records the tool as lost" if lost else "the tool is recorded in the hole, not lost"
        cand = ServiceCandidate(chosen[0], term, report.report_id, field, MappingStatus.IDENTIFIED_BY_CONTEXT, ("AMB-16",),
                                note=f"Appendix G lists {', '.join(all_codes)}; {context}, and the Appendix G footnote selects {chosen[0]}")
        return MappingResult(term, report.report_id, field, MappingStatus.IDENTIFIED_BY_CONTEXT, (cand,))
    cand = ServiceCandidate(chosen[0], term, report.report_id, field, MappingStatus.IDENTIFIED, ("AMB-17",) if note else (), note=note)
    return MappingResult(term, report.report_id, field, MappingStatus.IDENTIFIED, (cand,))


def map_report(ctx: MappingContext, report: DailyReport) -> tuple[MappingResult, ...]:
    out = []
    if report.operations:
        field = field_ref(report, *IN_THE_HOLE)
        out += [map_term(ctx, report, field, word, lost=False) for word in report.operations.in_the_hole]
        field = field_ref(report, *CREW)
        out += [map_term(ctx, report, field, entry.role, lost=False) for entry in report.operations.crew]
    if report.lost_in_hole and report.lost_in_hole.tool:
        out.append(map_term(ctx, report, field_ref(report, *LOST_TOOL), report.lost_in_hole.tool, lost=True))
    return tuple(out)


def codes_under(result: MappingResult, reading: str) -> tuple[str, ...]:
    """The candidate codes of a mapping under one Appendix G reading (reading-independent candidates always count)."""
    return tuple(c.service_code for c in result.candidates
                 if not c.readings or (READING_SWITCH, reading) in c.readings)
