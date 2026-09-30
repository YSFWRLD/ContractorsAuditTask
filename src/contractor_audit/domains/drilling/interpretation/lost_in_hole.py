"""Part E: one lost-in-hole unit per lost tool, with every candidate figure for its depreciation hours (AMB-22).

The quantity is one unit on the day of the loss (cl. 31). The hours that later drive depreciation are
carried as detail under both readings of `lih_hours`; nothing here depreciates or values the tool.
"""

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.ingestion.models import DailyReport
from contractor_audit.domains.drilling.interpretation.common import make_quantity, record_part, signed
from contractor_audit.domains.drilling.interpretation.models import Basis, MappingResult, Quantity, Scope
from contractor_audit.domains.drilling.interpretation.provenance import field_ref
from contractor_audit.domains.drilling.interpretation.service_mapping import LOST_TOOL, READING_SWITCH, codes_under


def lost_in_hole_quantities(terms: ContractTerms, report: DailyReport, mappings: tuple[MappingResult, ...],
                            well_reports: list[DailyReport], readings: tuple[str, ...]) -> list[Quantity]:
    lost = report.lost_in_hole
    if lost is None:
        return []
    mapping = next((m for m in mappings if m.source_field.label == LOST_TOOL[1]), None)
    if mapping is None:
        return []
    before = [r for r in well_reports if r.date and r.operations and r.date <= report.date]
    tool_hours = sum(r.operations.circulating_hours or 0 for r in before if lost.tool in r.operations.in_the_hole)
    well_hours = sum(r.operations.circulating_hours or 0 for r in before)
    stated = lost.circulating_hours_accumulated_on_well
    detail = (("tool", lost.tool), ("lih_hours.PART_E_STATED", str(stated)), ("lih_hours.TOOL_ACCUMULATED", str(tool_hours)),
              ("whole_well_hours_context", str(well_hours)), ("readings_agree", str(stated == tool_hours)))
    evidence = (field_ref(report, "E", "Lost in hole tool"), field_ref(report, "E", "Lost in hole run"),
                field_ref(report, "E", "Circulating hours accumulated on the well"))
    q = []
    dependent = mapping.status.value == "UNRESOLVED_INTERPRETATION"
    for reading in (readings if dependent else readings[:1]):
        for code in codes_under(mapping, reading):
            q.append(make_quantity(terms, code, 1, Basis.LOST_IN_HOLE, Scope.DAY, well=report.well, day=report.date, reports=(report,),
                                   run=lost.run, derivation="PART_E_LOST_TOOL", clauses=("31", "31A", "P12"), evidence=evidence,
                                   status=mapping.status, conditions=(record_part(report, "E"), signed(report)),
                                   readings=((READING_SWITCH, reading),) if dependent else (),
                                   ambiguity_ids=("AMB-16", "AMB-22") + (("AMB-17",) if dependent else ()), detail=detail))
    return q
