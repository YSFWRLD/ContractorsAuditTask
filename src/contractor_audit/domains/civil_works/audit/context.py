"""Everything an audit run reads, loaded once, plus lookups and contract citations.

Citations come from the reviewed `contract_extraction.json` (the Phase 1 provenance), so a
finding cites exactly the page and wording the rest of the project relies on.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from contractor_audit.domains.civil_works.contract import ContractTerms
from contractor_audit.domains.civil_works.contract_period import ContractPeriod
from contractor_audit.domains.civil_works.interpretation import WORKING_INTERPRETATION, CivilWorksInterpretation
from contractor_audit.domains.civil_works.models import Application, ApplicationLine
from contractor_audit.domains.civil_works.record_quantities import RecordQuantity
from contractor_audit.domains.civil_works.records import SiteRecord
from contractor_audit.domains.civil_works.audit.options import (WORKING_AUDIT_INTERPRETATION, AuditInterpretation,
                                                                MeasurementOrder)
from contractor_audit.shared.findings import Citation

_TEXT_LIMIT = 220


@dataclass(frozen=True)
class AuditData:
    """Inputs that do not change between interpretation runs."""
    terms: ContractTerms
    raw_extraction: dict
    applications: tuple[Application, ...]
    lines: tuple[ApplicationLine, ...]
    records: dict[str, SiteRecord]              # by ticket
    quantities: dict[str, RecordQuantity]       # by record id


@dataclass
class AuditContext:
    data: AuditData
    interp: CivilWorksInterpretation = WORKING_INTERPRETATION
    audit_interp: AuditInterpretation = WORKING_AUDIT_INTERPRETATION
    period: ContractPeriod = field(init=False)
    apps: dict[str, Application] = field(init=False)
    lines_by_app: dict[str, list[ApplicationLine]] = field(init=False)
    _clauses: dict[str, dict] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.period = ContractPeriod(self.data.terms)
        self.apps = {a.application_no: a for a in self.data.applications}
        self.lines_by_app = defaultdict(list)
        for line in self.data.lines:
            self.lines_by_app[line.application_no].append(line)
        self._clauses = {c["id"]: c for c in self.data.raw_extraction["clauses"]}

    @property
    def terms(self) -> ContractTerms:
        return self.data.terms

    @property
    def lines(self) -> tuple[ApplicationLine, ...]:
        return self.data.lines

    def measurement_key(self, line: ApplicationLine) -> tuple:
        """Order in which measurements were made, for 'later measurement' questions (Clause 44)."""
        app = self.apps[line.application_no]
        if self.audit_interp.measurement_order is MeasurementOrder.SUBMISSION_DATE:
            return (app.application_date, app.application_no, line.line_no)
        return (app.application_no, line.line_no)

    def work_area_of(self, line: ApplicationLine) -> str:
        return line.site

    def cite(self, clause_id: str) -> Citation:
        c = self._clauses.get(clause_id)
        if c is None:
            raise KeyError(f"clause {clause_id!r} is not in the reviewed extraction")
        text = c["text"]
        return Citation(f"Clause {clause_id}", c["source_page"], text if len(text) <= _TEXT_LIMIT else text[:_TEXT_LIMIT - 1] + "…")

    @staticmethod
    def cite_text(reference: str, page: int | None, text: str) -> Citation:
        return Citation(reference, page, text)


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def load_audit_data(data_root, artifacts_dir) -> AuditData:
    """Load the untouched task data and the reviewed contract extraction for an audit."""
    from contractor_audit.domains.civil_works.contract import EXTRACTION_FILENAME, load_raw_extraction, terms_from_raw
    from contractor_audit.domains.civil_works.loaders import load_application_lines, load_applications
    from contractor_audit.domains.civil_works.record_quantities import extract_all
    from contractor_audit.domains.civil_works.records import load_records
    from contractor_audit.domains.civil_works.sources import CivilWorksSources

    sources = CivilWorksSources.from_data_root(data_root)
    raw = load_raw_extraction(artifacts_dir / EXTRACTION_FILENAME)
    record_set = load_records(sources.records_dir)
    return AuditData(terms_from_raw(raw), raw, tuple(load_applications(sources.applications_csv)),
                     tuple(load_application_lines(sources.application_lines_csv)), record_set.by_ticket(),
                     {q.record_id: q for q in extract_all(record_set.records)})
