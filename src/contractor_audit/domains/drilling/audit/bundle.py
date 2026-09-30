"""The contract-side prices the audit compares invoices with, built before any invoice is read.

    canonical   every quantity priced under the audit's selection (approved and text-resolved readings).
                Class-rated services, PD-210 and PD-201 are EVIDENCE_NOT_PROVIDED there (AMB-13).
    by_class    the services whose price needs the call-off, priced once per possible well class with the
                eligibility the call-off would establish (every allowed-size PD-210 day nominated). These are
                CONDITIONAL figures: what the charge is worth if the call-off states that class. Nothing
                chooses a class; an invoice's claimed class only selects which conditional figure to compare with.

A bundle for an alternative reading is the base bundle with only the services that reading can affect repriced.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from contractor_audit.domains.drilling.contract.models import ContractTerms, RateBasis
from contractor_audit.domains.drilling.interpretation.models import InterpretationResult, Quantity
from contractor_audit.domains.drilling.interpretation.switches import Switch
from contractor_audit.domains.drilling.pricing.engine import price, selected
from contractor_audit.domains.drilling.pricing.models import PricedQuantity, PricingResult
from contractor_audit.domains.drilling.pricing.selection import Selection, Source

PD210 = "PD-210"


def calloff_services(terms: ContractTerms, selection: Selection) -> set[str]:
    """Services whose price or eligibility needs the call-off under this selection (AMB-13)."""
    apply_pd210 = selection.value("pd210_class_factor") == "APPLY"
    return {c for c, d in terms.services.items()
            if (d.class_rated and (d.rate_basis is not RateBasis.SCHEDULE_2 or apply_pd210)) or d.rate_basis is RateBasis.SCHEDULE_2}


@dataclass(frozen=True)
class PricingBundle:
    selection: Selection
    canonical: tuple[PricedQuantity, ...]
    by_class: dict[str, tuple[PricedQuantity, ...]]
    quantities: dict[str, Quantity]                  # qid -> quantity, for the quantities the selection keeps
    class_services: frozenset[str]
    _index: dict = field(default_factory=dict, compare=False, repr=False)

    def _build(self):
        if self._index:
            return self._index
        by_report, by_well = defaultdict(list), defaultdict(list)
        for p in self.canonical:
            for r in p.report_ids:
                by_report[(r, p.service_code)].append(p)
            by_well[(p.well, p.service_code)].append(p)
        self._index.update(by_report=by_report, by_well=by_well,
                           by_class={c: {p.qid: p for p in ps} for c, ps in self.by_class.items()})
        return self._index

    def at_report(self, report_id: str, code: str) -> list[PricedQuantity]:
        return self._build()["by_report"].get((report_id, code), [])

    def on_well(self, well: str, code: str) -> list[PricedQuantity]:
        return self._build()["by_well"].get((well, code), [])

    def conditional(self, qid: str) -> dict[str, PricedQuantity]:
        """class -> the conditional price of this quantity if the call-off states that class (empty if not call-off dependent)."""
        return {c: ix[qid] for c, ix in self._build()["by_class"].items() if qid in ix}


def _class_runs(result, terms, switches, selection, wells, services) -> dict[str, tuple[PricedQuantity, ...]]:
    hypothetical = selection.with_choice("calloff_evidence", "INVOICE_STATEMENT_UNVERIFIED", Source.HYPOTHETICAL)
    return {cls: price(result, terms, switches, hypothetical, {w: cls for w in wells}, services).priced for cls in terms.class_factors}


def build_bundle(result: InterpretationResult, terms: ContractTerms, switches: dict[str, Switch], selection: Selection) -> PricingBundle:
    canonical: PricingResult = price(result, terms, switches, selection)
    services = calloff_services(terms, selection)
    wells = sorted({q.well for q in result.quantities})
    quantities = {q.qid: q for q in result.quantities if selected(q, selection)}
    return PricingBundle(selection, canonical.priced, _class_runs(result, terms, switches, selection, wells, services), quantities, frozenset(services))


def rebundle(base: PricingBundle, result: InterpretationResult, terms: ContractTerms, switches: dict[str, Switch],
             selection: Selection, services: set[str]) -> PricingBundle:
    """The base bundle with `services` repriced under another selection (for a dependency run)."""
    canonical = [p for p in base.canonical if p.service_code not in services]
    canonical += price(result, terms, switches, selection, None, services).priced
    class_services = calloff_services(terms, selection)
    wells = sorted({q.well for q in result.quantities})
    reprice = (services & class_services) | (class_services - base.class_services)
    by_class = {c: tuple(p for p in ps if p.service_code not in reprice) for c, ps in base.by_class.items()}
    if reprice:
        for cls, ps in _class_runs(result, terms, switches, selection, wells, reprice).items():
            by_class[cls] += ps
    quantities = {q.qid: q for q in result.quantities if selected(q, selection)}
    return PricingBundle(selection, tuple(canonical), by_class, quantities, frozenset(class_services))
