"""Whether the Subcontract was live on a work date, and which Contract Year a date falls in.

Agreement p.1: commencement 2025-01-05, completion 2025-09-27. Amendment No. 1 (p.40) and
Amendment No. 2 (p.42) extend completion; each states that work executed after the extended
Date for Completion 'is not' measurable and payable. Clause 3A (p.32) defines Contract Years.
"""

from dataclasses import dataclass
from datetime import date

from contractor_audit.domains.civil_works.contract import ContractTerms, ContractYear


@dataclass(frozen=True)
class CompletionChange:
    instrument_id: str
    issued: date
    effective: date
    new_completion: date


@dataclass(frozen=True)
class ContractPeriodStatus:
    work_date: date
    measurable: bool
    reason: str
    completion_date: date
    contract_year: int | None


class ContractPeriod:
    def __init__(self, terms: ContractTerms):
        self.commencement = terms.commencement_date
        self.original_completion = terms.original_completion_date
        self.changes = tuple(CompletionChange(i.id, i.issued, i.effective, i.new_completion_date)
                             for i in terms.instruments if i.new_completion_date)
        self.years: tuple[ContractYear, ...] = terms.contract_years

    @property
    def final_completion(self) -> date:
        return max((c.new_completion for c in self.changes), default=self.original_completion)

    def completion_as_at(self, as_at: date) -> date:
        """Date for Completion as extended by the instruments issued on or before `as_at`."""
        issued = [c.new_completion for c in self.changes if c.issued <= as_at]
        return max(issued, default=self.original_completion)

    def contract_year(self, work_date: date) -> ContractYear | None:
        return next((y for y in self.years if y.start <= work_date <= y.end), None)

    def status(self, work_date: date) -> ContractPeriodStatus:
        completion = self.final_completion
        year = self.contract_year(work_date)
        if work_date < self.commencement:
            return ContractPeriodStatus(work_date, False, f"before the Commencement Date {self.commencement} (Agreement p.1)", completion, None)
        if work_date > completion:
            return ContractPeriodStatus(work_date, False, f"after the Date for Completion as extended ({completion}; Amendment No. 2 2.1 p.42: 'work executed after it is not' measurable)", completion, None)
        if work_date > self.original_completion:
            extended_by = min((c for c in self.changes if c.new_completion >= work_date), key=lambda c: c.new_completion)
            return ContractPeriodStatus(work_date, True, f"within the extension granted by {extended_by.instrument_id} (to {extended_by.new_completion})", completion, year.year if year else None)
        return ContractPeriodStatus(work_date, True, "within the Term as let (Agreement p.1)", completion, year.year if year else None)
