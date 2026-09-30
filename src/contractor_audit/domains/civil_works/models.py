"""Canonical civil works billing data: one payment application and its lines.

Money that the task scores (totals, retention, amounts) is held in integer halalas.
Rates and quantities stay Decimal because a built-up rate is compared, not summed.
Every object keeps the raw CSV strings so nothing a later check needs is lost.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class Application:
    application_no: str
    contract_ref: str
    subcontractor: str
    site: str
    site_zone: str
    period_from: date
    period_to: date
    application_date: date
    application_total_cents: int
    retention_cents: int
    net_payable_cents: int
    adjustment_cents: int
    retention_released_cents: int
    source_row: int
    raw: Mapping[str, str] = field(repr=False, compare=False)


@dataclass(frozen=True)
class ApplicationLine:
    line_ref: str
    application_no: str
    line_no: int
    work_date: date
    site: str
    item_code: str
    description: str
    unit: str
    site_zone: str
    ground_class: str | None
    quantity: Decimal
    rate_applied: Decimal
    amount_cents: int
    night_work: bool
    record_ref: str | None
    source_row: int
    raw: Mapping[str, str] = field(repr=False, compare=False)

    @property
    def series(self) -> str:
        return self.item_code[:1]

    @property
    def work_area(self) -> str:
        """The contract's 'work area' (Schedule 2) is what the CSV calls `site`."""
        return self.site
