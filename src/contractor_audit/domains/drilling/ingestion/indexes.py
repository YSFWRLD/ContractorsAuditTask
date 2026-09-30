"""Deterministic lookup indexes. A key never silently overwrites another: every index keeps all members per key."""

from dataclasses import dataclass
from datetime import date
from typing import Callable, Generic, Hashable, Iterable, TypeVar

from contractor_audit.domains.drilling.ingestion.models import DailyReport, DrillingDataset, DrillingInvoice, InvoiceLine

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)


class DuplicateKeyError(KeyError):
    pass


class KeyIndex(Generic[K, T]):
    """Key -> every member with that key, in source order. Keys iterate in sorted order."""

    def __init__(self, name: str, items: Iterable[T], key: Callable[[T], K | None]):
        self.name = name
        groups: dict = {}
        self.unkeyed: tuple[T, ...] = ()
        unkeyed = []
        for item in items:
            k = key(item)
            if k is None:
                unkeyed.append(item)
            else:
                groups.setdefault(k, []).append(item)
        self.unkeyed = tuple(unkeyed)
        self._groups: dict[K, tuple[T, ...]] = {k: tuple(groups[k]) for k in sorted(groups, key=_sort_key)}

    def __contains__(self, key: K) -> bool:
        return key in self._groups

    def __len__(self) -> int:
        return len(self._groups)

    def keys(self):
        return self._groups.keys()

    def get(self, key: K) -> tuple[T, ...]:
        return self._groups.get(key, ())

    def one(self, key: K) -> T:
        """The single member for `key`; raises KeyError when absent and DuplicateKeyError when shared."""
        members = self._groups[key]
        if len(members) > 1:
            raise DuplicateKeyError(f"{self.name}: {key!r} has {len(members)} members")
        return members[0]

    def duplicates(self) -> dict[K, tuple[T, ...]]:
        return {k: v for k, v in self._groups.items() if len(v) > 1}


def _sort_key(key):
    return tuple(str(part) for part in key) if isinstance(key, tuple) else (str(key),)


@dataclass(frozen=True)
class DrillingIndexes:
    invoices_by_id: KeyIndex[str, DrillingInvoice]
    invoices_by_well: KeyIndex[str, DrillingInvoice]
    lines_by_id: KeyIndex[str, InvoiceLine]
    lines_by_invoice: KeyIndex[str, InvoiceLine]
    lines_by_report_ref: KeyIndex[str, InvoiceLine]
    lines_by_report_and_code: KeyIndex[tuple[str, str], InvoiceLine]
    reports_by_id: KeyIndex[str, DailyReport]
    reports_by_well_and_date: KeyIndex[tuple[str, date], DailyReport]
    reports_by_well: KeyIndex[str, DailyReport]


def build_indexes(ds: DrillingDataset) -> DrillingIndexes:
    return DrillingIndexes(
        invoices_by_id=KeyIndex("invoices_by_id", ds.invoices, lambda i: i.invoice_no or None),
        invoices_by_well=KeyIndex("invoices_by_well", ds.invoices, lambda i: i.well_name or None),
        lines_by_id=KeyIndex("lines_by_id", ds.lines, lambda l: l.line_ref or None),
        lines_by_invoice=KeyIndex("lines_by_invoice", ds.lines, lambda l: l.invoice_no or None),
        lines_by_report_ref=KeyIndex("lines_by_report_ref", ds.lines, lambda l: l.report_ref),
        lines_by_report_and_code=KeyIndex("lines_by_report_and_code", ds.lines,
                                          lambda l: (l.report_ref, l.service_code) if l.report_ref else None),
        reports_by_id=KeyIndex("reports_by_id", ds.reports, lambda r: r.report_id),
        reports_by_well_and_date=KeyIndex("reports_by_well_and_date", ds.reports,
                                          lambda r: (r.well, r.date) if r.well and r.date else None),
        reports_by_well=KeyIndex("reports_by_well", ds.reports, lambda r: r.well),
    )
