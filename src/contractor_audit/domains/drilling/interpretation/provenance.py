"""Field references from a parsed report back to the exact line it was read from."""

from contractor_audit.domains.drilling.ingestion.models import DailyReport
from contractor_audit.domains.drilling.interpretation.models import FieldRef


class MissingEvidence(KeyError):
    pass


def field_ref(report: DailyReport, section: str, label: str) -> FieldRef:
    for f in report.fields:
        if f.section == section and f.label == label:
            return FieldRef(report.report_id, report.source.file, section, label, f.value, f.line)
    raise MissingEvidence(f"{report.report_id}: no {section}/{label}")


def refs(report: DailyReport, *pairs: tuple[str, str]) -> tuple[FieldRef, ...]:
    return tuple(field_ref(report, s, l) for s, l in pairs)
