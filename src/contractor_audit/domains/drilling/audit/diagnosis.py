"""Why a billed rate differs from the contract rate: the build-up component that, changed, reproduces it.

Only after the contract rate is established from the contract and the report evidence does this compare it
with the billed rate. Each change touches ONE component of the contract's own build-up (cl. 17A, 18, the
instruments, Schedule 2): another rate statement for the service, a factor dropped, added or taken at another
value, another depth band or tier. Single changes are tried first, then pairs; the first that reproduces the
billed rate names the category (changes are generated in category precedence order). A billed rate nothing
explains is `rate_mismatch`. Diagnosis never changes the contract rate, only the label and the explanation.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations

from contractor_audit.domains.drilling.audit.categories import Category
from contractor_audit.domains.drilling.contract.models import ContractTerms, RateBasis, StandbyTreatment
from contractor_audit.domains.drilling.pricing.models import PricedPart
from contractor_audit.domains.drilling.pricing.rounding import half_even_cents

ORDER = ("volume tier", "index", "section factor", "class factor", "standby percentage", "principal discount")
Chain = tuple[int, dict[str, Decimal]]


@dataclass(frozen=True)
class Diagnosis:
    category: Category
    rule: str
    explanation: str


@dataclass(frozen=True)
class Change:
    category: Category
    rule: str
    explanation: str
    component: str                       # two changes to the same component are never combined
    apply: Callable[[Chain], Chain]


def _evaluate(chain: Chain) -> int:
    value, factors = chain
    for name in ORDER:
        if name in factors:
            value = half_even_cents(Decimal(value) * factors[name])
    return value


def _chain(part: PricedPart) -> Chain:
    return part.steps[0].output_cents, {s.name: Decimal(s.factor) for s in part.steps[1:] if s.name in ORDER}


def _set(name: str, value: Decimal | None) -> Callable[[Chain], Chain]:
    def f(chain: Chain) -> Chain:
        base, factors = chain
        factors = {k: v for k, v in factors.items() if k != name}
        if value is not None:
            factors[name] = value
        return base, factors
    return f


def _base(cents: int) -> Callable[[Chain], Chain]:
    return lambda chain: (cents, chain[1])


def _changes(terms: ContractTerms, code: str, chain: Chain, alt_rates: tuple[int, ...] = ()) -> Iterator[Change]:
    service = terms.services[code]
    base, factors = chain
    statements = {s.rate_cents: s for s in terms.rate_statements(code)}
    for cents in sorted(set(statements) | set(alt_rates)):
        if cents != base:
            s = statements.get(cents)
            what = f"the {s.source} {s.kind.value.lower()} rate {cents / 100:.2f}" if s else f"the rate {cents / 100:.2f}"
            yield Change(Category.SUPERSEDED_RATE, "rates.superseded_statement", f"{what} instead of the rate in force", "base", _base(cents))
    percents = sorted({d.percent for i in terms.instruments for d in i.discounts if code in d.codes})
    if percents:
        if "principal discount" in factors:
            yield Change(Category.DISCOUNT_MISAPPLIED, "adjustments.discount_omitted", "leaving out the principal-services discount",
                         "principal discount", _set("principal discount", None))
        for pct in percents:
            if factors.get("principal discount") != 1 - pct / 100:
                yield Change(Category.DISCOUNT_MISAPPLIED, "adjustments.discount_wrong", f"a {pct}% discount not in force on the work date",
                             "principal discount", _set("principal discount", 1 - pct / 100))
    if service.standby.treatment is StandbyTreatment.PERCENT:
        if "standby percentage" in factors:
            yield Change(Category.STANDBY_RATE_MISAPPLIED, "adjustments.standby_not_applied", "charging a Standby day at the full rate",
                         "standby percentage", _set("standby percentage", None))
        else:
            yield Change(Category.STANDBY_RATE_MISAPPLIED, "adjustments.standby_on_operating_day", "the standby percentage on an Operating day",
                         "standby percentage", _set("standby percentage", service.standby.percent / 100))
    for name, table in (("section factor", terms.section_factors), ("class factor", terms.class_factors)):
        if name in factors:
            yield Change(Category.FACTOR_MISAPPLIED, "adjustments.factor_omitted", f"leaving out the {name}", name, _set(name, None))
        for label, f in table.items():
            if factors.get(name) != f:
                yield Change(Category.FACTOR_MISAPPLIED, "adjustments.factor_wrong", f"a {name} of {f} ({label})", name, _set(name, f))
    if service.indexed:
        if "index" in factors:
            yield Change(Category.INDEX_MISAPPLIED, "adjustments.index_omitted", "leaving out the Rig Services Index", "index", _set("index", None))
        for month, index in sorted(terms.price_index.monthly.items()):
            f = index / terms.price_index.base_index
            if factors.get("index") != f:
                yield Change(Category.INDEX_MISAPPLIED, "adjustments.index_month", f"the index for {month} ({index})", "index", _set("index", f))
    if service.rate_basis is RateBasis.SCHEDULE_2:
        for band in terms.depth_bands:
            if band.rate_cents != base:
                yield Change(Category.DEPTH_BAND_MISAPPLIED, "rates.depth_band", f"the band {band.band} rate {band.rate_cents / 100:.2f}", "base", _base(band.rate_cents))
        for tier in terms.volume_tiers:
            if factors.get("volume tier") != tier.percent_of_rate / 100:
                yield Change(Category.DEPTH_BAND_MISAPPLIED, "rates.volume_tier", f"the tier {tier.band} percentage ({tier.percent_of_rate}%)",
                             "volume tier", _set("volume tier", tier.percent_of_rate / 100))
    if factors:
        yield Change(Category.RATE_MISMATCH, "rates.unadjusted_base", "the rate with none of the build-up applied", "all", lambda chain: (chain[0], {}))


def diagnose(terms: ContractTerms, code: str, part: PricedPart, billed_rate_cents: int, expected_rate_cents: int | None = None,
             alt_rates: tuple[int, ...] = ()) -> Diagnosis:
    """`part` is the priced build-up; `expected_rate_cents` the rate in force for this charge (it differs from the part's own rate
    when Clause 36A puts an invoice before the back-dated instrument's issue); `alt_rates` the rate on the other side of 36A."""
    if terms.services[code].rate_basis is RateBasis.CLAUSE_31:
        return Diagnosis(Category.LOST_IN_HOLE_VALUATION, "adjustments.lost_in_hole_value",
                         "the value charged is not the Schedule 2D value converted at the month of loss and depreciated (cl. 31, 31A)")
    if billed_rate_cents in alt_rates:
        return Diagnosis(Category.SUPERSEDED_RATE, "rates.backdated_timing",
                         "reproduced by the rate on the other side of Amendment No. 3's date of issue (cl. 36A: the invoice date decides)")
    chain = _chain(part)
    expected = _evaluate(chain) if expected_rate_cents is None else expected_rate_cents
    if _evaluate(chain) != expected:            # rebuild on the rate statement that gives the rate in force
        base = next((s.rate_cents for s in terms.rate_statements(code) if _evaluate((s.rate_cents, chain[1])) == expected), None)
        if base is not None:
            chain = (base, chain[1])
    changes = [c for c in _changes(terms, code, chain, ()) if _evaluate(c.apply(chain)) != expected]   # a change must change something
    for c in changes:
        if _evaluate(c.apply(chain)) == billed_rate_cents:
            return Diagnosis(c.category, c.rule, f"reproduced by {c.explanation}")
    for a, b in combinations(changes, 2):
        if a.component != b.component and "all" not in (a.component, b.component) and _evaluate(b.apply(a.apply(chain))) == billed_rate_cents:
            return Diagnosis(a.category, a.rule + "+" + b.rule.split(".")[-1], f"reproduced by {a.explanation} and {b.explanation}")
    return Diagnosis(Category.RATE_MISMATCH, "rates.rate_mismatch", "no single or paired build-up change explains the billed rate")
