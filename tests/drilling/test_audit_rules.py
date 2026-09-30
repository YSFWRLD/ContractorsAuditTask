"""Targeted drilling audit rules on a small synthetic world: one correct invoice, then one change at a time."""

from datetime import timedelta
from decimal import Decimal

import pytest
from .audit_world import World, categories, d, find, invoice, line, report, with_line

from contractor_audit.domains.drilling.audit.categories import Category, primary_key
from contractor_audit.domains.drilling.audit.dependencies import Alternative, Measured
from contractor_audit.domains.drilling.audit.engine import _adjustment_findings, backdated_adjustments
from contractor_audit.domains.drilling.audit.invoices import discount, invoice_checks, vat
from contractor_audit.domains.drilling.audit.models import LineAssessment, LineStatus, TotalStatus
from contractor_audit.domains.drilling.audit.results import grade
from contractor_audit.domains.drilling.pricing.selection import APPROVED_FILENAME, load_approved
from contractor_audit.shared import paths
from contractor_audit.shared.findings import ConfidenceBand, Dependency, Finding, Outcome

W1, W2, W3, W4 = "NGP-TS-901", "NGP-TS-902", "NGP-TS-903", "NGP-TS-904"
D1, D2, D3 = d("2025-03-10"), d("2025-03-11"), d("2025-03-12")
DATED = d("2025-03-20")


@pytest.fixture(scope="module")
def approved(switches):
    return load_approved(paths.artifacts_dir("drilling") / APPROVED_FILENAME, switches)


@pytest.fixture(scope="module")
def world(terms, ambiguities, switches, approved):
    """Three days on one well: Operating (run 1 starts), Standby, Operating (run 1 ends). 12-1/4" section."""
    run = dict(first=D1, last=D3)
    reports = [report(W1, D1, **run), report(W1, D2, status="Standby", start=1200, end=1200, circ=4, **run),
               report(W1, D3, start=1200, end=1350, circ=12, **run)]
    return World(terms, ambiguities, switches, approved, reports)


@pytest.fixture(scope="module")
def plain(terms, ambiguities, switches, approved):
    """A 17-1/2" day with no class-rated or performance service: its total can be fully determined."""
    return World(terms, ambiguities, switches, approved,
                 [report(W3, d("2025-04-01"), section='17-1/2"', tools=("drilling jars", "mud motor", "real-time link"), crew="2 directional hands, 1 night man")])


@pytest.fixture(scope="module")
def odd(terms, ambiguities, switches, approved):
    """Unusual days: unsigned; a gyro survey without its Part C; three directional hands; 3 circulating hours; a 17-1/2" section."""
    run = dict(first=d("2025-05-01"), last=d("2025-05-04"))
    return World(terms, ambiguities, switches, approved, [
        report(W4, d("2025-05-01"), signed=False, **run),
        report(W4, d("2025-05-02"), gyro=1, start=1200, end=1300, **run),
        report(W4, d("2025-05-03"), crew="3 directional hands, 1 night man, 2 MWD engineers", start=1300, end=1400, **run),
        report(W4, d("2025-05-04"), section='17-1/2"', circ=3, start=1400, end=1500, **run)])


@pytest.fixture(scope="module")
def a3(terms, ambiguities, switches, approved):
    """A day after Amendment No. 3's effective date (2026-02-01) and a week before its issue (2026-08-17); personnel only."""
    return World(terms, ambiguities, switches, approved,
                 [report(W2, d("2026-08-10"), section='17-1/2"', tools=("drilling jars",), crew="2 directional hands")])


def ids(w):
    return [r.report_id for r in w.reports]


def build(w, terms, lines=None, no="MDS-90001", start=D1, end=D3, dated=DATED, **kw):
    lines = w.correct_lines(no, ids(w), dated) if lines is None else lines
    return invoice(no, w.reports[0].well, start, end, dated, lines, terms=terms, **kw)


def one(w, inv, policy=None):
    return w.audit(inv, policy=policy)[inv[0].invoice_no]


def line_of(outcome, ref):
    return next(l for l in outcome.audit.lines if l.line.line_ref == ref)


# ---------------------------------------------------------------- the correct invoice
def test_correct_invoice_passes(world, terms):
    o = one(world, build(world, terms))
    assert not o.result.flagged and categories(o) == set()
    assert o.outcome is Outcome.QUERY          # the entitlement queries stand (AMB-13), they do not flag
    assert o.result.expected_total_cents is None and o.total_status == "conditional"
    assert o.conditional_total_cents == o.result.billed_total_cents
    assert o.result.confidence == ConfidenceBand.MEDIUM.score


def test_correct_invoice_without_call_off_services_has_a_determined_total(plain, terms):
    inv = build(plain, terms, start=d("2025-04-01"), end=d("2025-04-01"), dated=d("2025-04-10"))
    o = one(plain, inv)
    assert not o.result.flagged and o.total_status == "determined"
    assert o.result.expected_total_cents == o.result.billed_total_cents and o.result.confidence == ConfidenceBand.HIGH.score


# ---------------------------------------------------------------- check 1
def test_contract_reference_and_issuer(world, terms):
    o = one(world, build(world, terms, ref="DSS-2025-118"))
    f = next(f for f in o.findings if f.category == Category.CONTRACT_REFERENCE_MISMATCH.value)
    assert o.result.flagged and f.rule == "identity.contract_ref" and not f.affects_total and f.check.value == 1
    o = one(world, build(world, terms, contractor="Another Drilling Co"))
    assert {f.rule for f in o.findings if f.category == "contract_reference_mismatch"} == {"identity.issuer"}


# ---------------------------------------------------------------- check 2
def test_work_after_the_extended_term(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "DD-102")
    lines = with_line(lines, target.line_ref, service_date=d("2027-01-05"))
    o = one(world, build(world, terms, lines, end=d("2027-01-05")))
    assert "work_outside_contract_term" in categories(o)
    a = line_of(o, target.line_ref)
    assert a.status is LineStatus.DETERMINED and a.amount_cents == 0


# ---------------------------------------------------------------- check 3
@pytest.mark.parametrize("days_after,rule", [(-1, "timing.before_period_end"), (31, "timing.late"), (30, None), (0, None)])
def test_invoice_timing(world, terms, days_after, rule):
    """Clause 33 is judged from the invoice date only under AMB-25 reading A (a sensitivity alternative, not the decision)."""
    policy = world.policy.with_audit("submission_date", "INVOICE_DATE_IS_SUBMISSION")
    o = one(world, build(world, terms, dated=D3 + timedelta(days=days_after)), policy)
    found = {f.rule for f in o.findings if f.category == "invoice_timing"}
    assert found == ({rule} if rule else set())
    if rule:
        f = next(f for f in o.findings if f.category == "invoice_timing")
        assert f.confidence is ConfidenceBand.MEDIUM and not f.affects_total and o.result.flagged


@pytest.mark.parametrize("days_after,observed", [(-1, True), (45, True), (30, False)])
def test_timing_is_not_judged_without_a_submission_date(world, terms, days_after, observed):
    """AMB-25 as decided: the submission date is not in the data; the invoice date proves nothing about Clause 33."""
    assert world.policy.value("submission_date") == "UNKNOWN_QUERY"
    o = one(world, build(world, terms, dated=D3 + timedelta(days=days_after)))
    assert "invoice_timing" not in categories(o) and not o.result.flagged
    assert bool(o.audit.observations) is observed
    assert all("AMB-25" in x for x in o.audit.observations)


def test_line_outside_period(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "MW-330")
    o = one(world, build(world, terms, with_line(lines, target.line_ref, service_date=d("2025-03-13"))))
    assert {"line_outside_invoice_period", "record_line_mismatch"} <= categories(o)
    assert line_of(o, target.line_ref).amount_cents == 0


# ---------------------------------------------------------------- check 4
def test_missing_report(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    a, b = find(lines, "DD-102"), find(lines, "DD-102", 1)
    lines = with_line(with_line(lines, a.line_ref, report_ref=None), b.line_ref, report_ref="DDR-901-20250399")
    o = one(world, build(world, terms, lines))
    missing = [f for f in o.findings if f.category == "missing_record"]
    assert {f.line_ref for f in missing} == {a.line_ref, b.line_ref} and all(f.affects_total for f in missing)
    assert line_of(o, a.line_ref).amount_cents == 0
    # AMB-23 reading B: a query that holds the charge back without rejecting it
    o = one(world, build(world, terms, lines), world.policy.with_audit("missing_record_consequence", "QUERY"))
    held = [f for f in o.findings if f.category == "missing_record"]
    assert all(f.blocks_total and not f.affects_total and f.outcome is Outcome.QUERY for f in held)
    assert line_of(o, a.line_ref).status is LineStatus.UNDETERMINED


def test_unsigned_report(odd, terms):
    rid = odd.reports[0].report_id
    inv = invoice("MDS-90004", W4, d("2025-05-01"), d("2025-05-01"), d("2025-05-10"), odd.correct_lines("MDS-90004", [rid], d("2025-05-10")), terms=terms)
    o = one(odd, inv)
    unsigned = [f for f in o.findings if f.category == "unsigned_record"]
    assert len(unsigned) == len([l for l in inv[1] if l.service_code != "DS-900"]) and o.result.flagged


def test_record_part_missing(odd, terms):
    rid = odd.reports[1].report_id
    lines = odd.correct_lines("MDS-90004", [rid], d("2025-05-10"))
    assert any(l.service_code == "DD-130" for l in lines)       # the gyro survey Part A records, without its Part C
    o = one(odd, invoice("MDS-90004", W4, d("2025-05-02"), d("2025-05-02"), d("2025-05-10"), lines, terms=terms))
    f = next(f for f in o.findings if f.category == "record_part_missing")
    assert line_of(o, f.line_ref).line.service_code == "DD-130" and f.affects_total


def test_record_for_another_day(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "DD-102")
    o = one(world, build(world, terms, with_line(lines, target.line_ref, report_ref=world.reports[2].report_id)))
    assert "record_line_mismatch" in categories(o)


# ---------------------------------------------------------------- checks 5 and 9
def test_quantity_above_record(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "MW-301")
    o = one(world, build(world, terms, with_line(lines, target.line_ref, quantity=Decimal(3))))
    f = next(f for f in o.findings if f.category == "quantity_exceeds_record")
    assert f.observed == "3" and f.expected == "2" and line_of(o, target.line_ref).payable_quantity == 2


def test_daily_limit(odd, terms):
    rid = odd.reports[2].report_id
    lines = odd.correct_lines("MDS-90004", [rid], d("2025-05-10"))
    target = find(lines, "DD-101")
    assert target.quantity == 2                                   # three recorded, the daily limit is two
    o = one(odd, invoice("MDS-90004", W4, d("2025-05-03"), d("2025-05-03"), d("2025-05-10"),
                         with_line(lines, target.line_ref, quantity=Decimal(3)), terms=terms))
    assert "daily_limit_exceeded" in categories(o)


@pytest.mark.parametrize("billed_to,finding", [(1202, False), (1203, True)])
def test_metre_tolerance_25a(world, terms, billed_to, finding):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "PD-210")
    assert (target.depth_from_m, target.depth_to_m) == (1000, 1200)
    changed = with_line(lines, target.line_ref, depth_to_m=billed_to, quantity=Decimal(billed_to - 1000))
    o = one(world, build(world, terms, changed))
    assert ("quantity_exceeds_record" in categories(o)) is finding
    if not finding:
        assert any("25A" in x for x in line_of(o, target.line_ref).observations)


def test_standby_exclusion(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    standby = world.reports[1].report_id
    extra = [line("MDS-90001", 90, D2, W1, "HC-640", 1, "719.55", standby, terms=terms, status="Standby"),
             line("MDS-90001", 91, D2, W1, "DD-120", 1, "384.15", standby, terms=terms, status="Standby")]
    o = one(world, build(world, terms, lines + extra))
    flagged = [f for f in o.findings if f.category == "not_chargeable_on_standby"]
    assert {f.line_ref for f in flagged} == {l.line_ref for l in extra}


def test_standby_rate(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = next(l for l in lines if l.service_code == "DD-101" and l.day_status == "Standby")
    o = one(world, build(world, terms, with_line(lines, target.line_ref, unit_rate=Decimal("1847.35"))))
    f = next(f for f in o.findings if f.line_ref == target.line_ref)
    assert f.category == "standby_rate_misapplied" and f.affects_total and f.impact_cents == 2 * (184735 - 147788)   # two persons


def test_minimum_hours(odd, terms):
    rid = odd.reports[3].report_id
    lines = odd.correct_lines("MDS-90004", [rid], d("2025-05-10"))
    dd120 = find(lines, "DD-120")
    assert dd120.quantity == 6                                    # 3 recorded; the 6-hour minimum on an Operating day (cl. 21)
    inv = lambda ls: invoice("MDS-90004", W4, d("2025-05-04"), d("2025-05-04"), d("2025-05-10"), ls, terms=terms)  # noqa: E731
    assert "quantity_exceeds_record" not in categories(one(odd, inv(lines)))
    assert "quantity_exceeds_record" in categories(one(odd, inv(with_line(lines, dd120.line_ref, quantity=Decimal(7)))))


def test_once_only(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    extra = [line("MDS-90001", 90, D3, W1, "MB-701", 1, "18497.50", world.reports[2].report_id, terms=terms),
             line("MDS-90001", 91, D1, W1, "DD-111", 1, "3589.45", world.reports[0].report_id, terms=terms)]
    o = one(world, build(world, terms, lines + extra))
    assert {f.line_ref for f in o.findings if f.category == "once_only_exceeded"} == {l.line_ref for l in extra}


def test_unsupported_service(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    extra = [line("MDS-90001", 90, D1, W1, "HC-601", 1, "689.35", world.reports[0].report_id, terms=terms),
             line("MDS-90001", 91, D2, W1, "DD-121", 1, "2893.65", world.reports[0].report_id, terms=terms)]
    o = one(world, build(world, terms, lines + extra))
    unsupported = {f.line_ref for f in o.findings if f.category == "unsupported_service"}
    assert extra[0].line_ref in unsupported and line_of(o, extra[0].line_ref).amount_cents == 0


def test_unit_mismatch(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "DD-110")
    o = one(world, build(world, terms, with_line(lines, target.line_ref, unit="hour")))
    assert "unit_mismatch" in categories(o) and line_of(o, target.line_ref).amount_cents == 0


# ---------------------------------------------------------------- checks 7 and 8
def test_amendment_3_rate_before_and_after_issue(a3, terms):
    rid = a3.reports[0].report_id
    p = a3.priced(rid, "DD-101")[0]
    before, after = p.rate_without_retroactive_cents, p.parts[0].rate_cents          # 1916.50 x 0.93 and 1954.00 x 0.93
    assert (before, after) == (178234, 181722)
    for dated, rate, other in ((d("2026-08-14"), before, after), (d("2026-08-20"), after, before)):
        lines = a3.correct_lines("MDS-90002", [rid], dated)
        dd101 = find(lines, "DD-101")
        assert dd101.unit_rate * 100 == rate                                          # 36A: the rate then in force
        inv = lambda ls: invoice("MDS-90002", W2, d("2026-08-10"), d("2026-08-10"), dated, ls, terms=terms)  # noqa: E731
        o = one(a3, inv(lines))
        assert not o.result.flagged and o.result.expected_total_cents == o.result.billed_total_cents
        o = one(a3, inv(with_line(lines, dd101.line_ref, unit_rate=Decimal(other) / 100)))
        f = next(f for f in o.findings if f.line_ref == dd101.line_ref)
        assert f.category == "superseded_rate" and "36A" in f.message
        assert f.rule == "rates.backdated_timing" and [d.switch for d in f.dependencies] == ["submission_date"]


def test_discount_and_factor_diagnosis(a3, world, terms):
    rid = a3.reports[0].report_id
    lines = a3.correct_lines("MDS-90002", [rid], d("2026-08-14"))
    dd101 = find(lines, "DD-101")
    o = one(a3, invoice("MDS-90002", W2, d("2026-08-10"), d("2026-08-10"), d("2026-08-14"),
                        with_line(lines, dd101.line_ref, unit_rate=Decimal("1916.50")), terms=terms))
    assert next(f for f in o.findings if f.line_ref == dd101.line_ref).category == "discount_misapplied"
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    dd110 = find(lines, "DD-110")                                     # 12-1/4" factor 1.00; billed at the 17-1/2" factor
    hc620 = find(lines, "HC-620")                                     # indexed at March 2025; billed at June's index
    changed = with_line(with_line(lines, dd110.line_ref, unit_rate=Decimal("1623.32")), hc620.line_ref, unit_rate=Decimal("559.08"))
    o = one(world, build(world, terms, changed))
    by_line = {f.line_ref: f.category for f in o.findings}
    assert by_line[dd110.line_ref] == "factor_misapplied" and by_line[hc620.line_ref] == "index_misapplied"


def _assessed(inv, retro=None, status=LineStatus.DETERMINED):
    a = LineAssessment(line=None, status=status, retro_difference_cents=retro)
    return a


def test_backdated_adjustment(terms):
    from dataclasses import replace
    from .audit_world import invoice as mk
    base = mk("MDS-1", "W-A", d("2026-03-01"), d("2026-03-05"), d("2026-03-20"), [], terms=terms)[0]
    invs = [replace(base, invoice_no="MDS-1", well_name="W-A", invoice_date=d("2026-03-20")),
            replace(base, invoice_no="MDS-2", well_name="W-B", invoice_date=d("2026-08-17")),
            replace(base, invoice_no="MDS-3", well_name="W-A", invoice_date=d("2026-08-18"))]
    assessed = {"MDS-1": [_assessed(None, 1000)], "MDS-2": [], "MDS-3": []}
    issue = d("2026-08-17")
    assert backdated_adjustments(invs, assessed, "CONTRACT_WIDE_ON_OR_AFTER", issue) == {"MDS-2": (1000, TotalStatus.DETERMINED)}
    assert backdated_adjustments(invs, assessed, "CONTRACT_WIDE_AFTER", issue) == {"MDS-3": (1000, TotalStatus.DETERMINED)}
    assert backdated_adjustments(invs, assessed, "PER_WELL", issue) == {"MDS-3": (1000, TotalStatus.DETERMINED)}
    assert backdated_adjustments(invs, assessed, "NO_REPRICING", issue) == {}
    missing = _adjustment_findings(terms, invs[1], (1000, TotalStatus.DETERMINED))
    assert [f.category for f in missing] == ["backdated_adjustment_missing"] and missing[0].impact_cents == -1000
    assert [d.switch for d in missing[0].dependencies] == ["submission_date"] and "proxy" in missing[0].message
    assert _adjustment_findings(terms, replace(invs[1], adjustment_cents=1000), (1000, TotalStatus.DETERMINED)) == []
    wrong = _adjustment_findings(terms, replace(invs[0], adjustment_cents=500), None)
    assert [f.category for f in wrong] == ["backdated_adjustment_incorrect"]
    conditional = _adjustment_findings(terms, invs[1], (1000, TotalStatus.CONDITIONAL))
    assert conditional[0].blocks_total and not conditional[0].affects_total


# ---------------------------------------------------------------- checks 10 and 11
def test_duplicate_within_invoice(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    copy = line("MDS-90001", 90, D1, W1, "DD-102", 1, "948.60", world.reports[0].report_id, terms=terms)
    o = one(world, build(world, terms, lines + [copy]))
    f = next(f for f in o.findings if f.category == "duplicate_charge")
    assert f.line_ref == copy.line_ref and f.rule == "duplicates.within_invoice" and line_of(o, copy.line_ref).amount_cents == 0
    assert f.dependencies == () and f.confidence is ConfidenceBand.HIGH    # one invoice: no submission order in question


def test_duplicate_across_invoices(world, terms):
    first = build(world, terms)
    copy = line("MDS-90002", 1, D1, W1, "DD-102", 1, "948.60", world.reports[0].report_id, terms=terms)
    second = invoice("MDS-90002", W1, D1, D1, DATED + timedelta(days=5), [copy], terms=terms)
    out = world.audit(first, second)
    assert not out["MDS-90001"].result.flagged
    f = next(f for f in out["MDS-90002"].findings if f.category == "duplicate_charge")
    assert f.rule == "duplicates.across_invoices" and first[1][1].line_ref in f.message
    # which of the two invoices carries the repeat rests on the invoice-date proxy, not on a known submission order
    assert [d.switch for d in f.dependencies] == ["submission_date"] and f.confidence is ConfidenceBand.MEDIUM


def test_line_and_invoice_arithmetic(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "MW-330")
    changed = with_line(lines, target.line_ref, amount_cents=target.amount_cents + 1000)
    o = one(world, build(world, terms, changed))
    assert "line_arithmetic" in categories(o) and "invoice_arithmetic" not in categories(o)   # net is the sum of the (wrong) line
    inv, ls = build(world, terms)
    o = one(world, (inv.__class__(**{**inv.__dict__, "net_cents": inv.net_cents + 1}), ls))
    assert "arithmetic.net" in {f.rule for f in o.findings if f.category == "invoice_arithmetic"}
    o = one(world, (inv.__class__(**{**inv.__dict__, "total_cents": inv.total_cents + 1}), ls))
    assert {f.rule for f in o.findings if f.category == "invoice_arithmetic"} == {"arithmetic.total"}


def test_vat(world, terms):
    inv, ls = build(world, terms)
    o = one(world, (inv.__class__(**{**inv.__dict__, "vat_cents": inv.vat_cents + 1, "total_cents": inv.total_cents + 1}), ls))
    assert categories(o) == {"vat_error"}


def test_ds900(terms):
    assert discount(terms, 25000000) == 0                          # 'exceeds': exactly 250,000.00 attracts none
    assert discount(terms, 31240000) == -249600                    # the Appendix B worked example
    from .audit_world import invoice as mk
    from .audit_world import line as ln

    def assessed(amounts, ds=None):
        ls = [ln("MDS-9", i + 1, D1, W1, "MW-330", 1, Decimal(a) / 100, "R", terms=terms) for i, a in enumerate(amounts)]
        out = [LineAssessment(l, LineStatus.DETERMINED) for l in ls]
        if ds is not None:
            out.append(LineAssessment(ln("MDS-9", 99, None, W1, "DS-900", 1, Decimal(ds) / 100, None, terms=terms), LineStatus.INVOICE_LEVEL))
        return out
    inv = mk("MDS-9", W1, D1, D1, DATED, [], terms=terms, with_discount=False)[0]
    rules = lambda la: {f.category for f in invoice_checks(terms, inv, la, lambda s: "INVOICE_DATE_IS_SUBMISSION")}  # noqa: E731
    assert "invoice_discount_error" in rules(assessed([20000000, 11240000]))                 # omitted
    assert "invoice_discount_error" in rules(assessed([20000000, 11240000], -249500))        # miscalculated
    assert "invoice_discount_error" not in rules(assessed([20000000, 11240000], -249600))    # right
    assert "invoice_discount_error" not in rules(assessed([20000000, 5000000]))              # exactly at the threshold
    assert "invoice_discount_error" in rules(assessed([20000000, 5000000], -1))              # charged although not exceeded


# ---------------------------------------------------------------- AMB-13: call-off dependent charges
def test_class_rated_charge_stays_unresolved(world, terms):
    o = one(world, build(world, terms))
    mw310 = [l for l in o.audit.lines if l.line.service_code == "MW-310"]
    assert mw310 and all(l.status is LineStatus.CONDITIONAL for l in mw310)
    assert all(any(f.category == "entitlement_unverified" for f in l.findings) for l in mw310)
    assert "entitlement_unverified:AMB-13" in o.blank_reasons


@pytest.mark.parametrize("claimed", ["Standard", "Extended Reach", "HPHT"])
def test_invoice_claims_cannot_establish_the_entitlement(world, terms, claimed):
    lines = world.correct_lines("MDS-90001", ids(world), DATED, claimed=claimed)
    o = one(world, build(world, terms, lines, cls=claimed))
    assert not o.result.flagged and o.result.expected_total_cents is None and o.total_status == "conditional"
    assert o.conditional_total_cents == o.result.billed_total_cents


def test_described_class_differing_from_the_billed_class_is_only_a_query(world, terms):
    """The invoice's well class is descriptive (cl. 34, Appendix B); the class is the call-off's (P2, P3): no finding either way."""
    lines = world.correct_lines("MDS-90001", ids(world), DATED, claimed="HPHT")
    o = one(world, build(world, terms, lines, cls="Standard"))
    assert not o.result.flagged and o.result.expected_total_cents is None and o.total_status == "conditional"
    queries = [f for f in o.findings if f.rule == "entitlement.descriptive_class_differs"]
    assert queries and all(f.category == "entitlement_unverified" and f.outcome is Outcome.QUERY and f.blocks_total for f in queries)
    f = queries[0]
    assert "HPHT" in f.observed and all(c in f.expected for c in ("Standard", "Extended Reach", "HPHT"))   # billed rate and every class's rate
    mw310 = next(l for l in o.audit.lines if l.line.service_code == "MW-310")
    assert mw310.status is LineStatus.CONDITIONAL                                  # entitlement still EVIDENCE_NOT_PROVIDED


def test_class_rated_rate_no_class_produces(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "MW-310")
    o = one(world, build(world, terms, with_line(lines, target.line_ref, unit_rate=Decimal("2245.85"))))
    f = next(f for f in o.findings if f.line_ref == target.line_ref and f.category != "entitlement_unverified")
    assert f.category == "index_misapplied" and f.blocks_total and not f.affects_total and o.result.flagged


def test_pd201_unresolved(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    pd201 = find(lines, "PD-201")
    o = one(world, build(world, terms, lines))
    a = line_of(o, pd201.line_ref)
    assert a.status is LineStatus.CONDITIONAL and any(f.category == "entitlement_unverified" for f in a.findings)
    o = one(world, build(world, terms, with_line(lines, pd201.line_ref, unit_rate=Decimal("2200.00"))))
    assert any(f.line_ref == pd201.line_ref and f.category == "rate_mismatch" for f in o.findings) and o.result.flagged


def test_pd210_unresolved_and_ineligible(world, odd, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    pd210 = find(lines, "PD-210")
    o = one(world, build(world, terms, lines))
    assert line_of(o, pd210.line_ref).status is LineStatus.CONDITIONAL
    o = one(world, build(world, terms, with_line(lines, pd210.line_ref, unit_rate=Decimal("56.11"))))   # 42.35 x 1.325 (HPHT)
    assert next(f for f in o.findings if f.line_ref == pd210.line_ref and f.category != "entitlement_unverified").category == "factor_misapplied"
    rid = odd.reports[3].report_id                                   # 17-1/2": not a size Appendix A allows
    extra = line("MDS-90004", 1, d("2025-05-04"), W4, "PD-210", 100, "42.35", rid, terms=terms, section='17-1/2"', depth_from=1400, depth_to=1500)
    o = one(odd, invoice("MDS-90004", W4, d("2025-05-04"), d("2025-05-04"), d("2025-05-10"), [extra], terms=terms))
    assert "section_not_eligible" in categories(o)


# ---------------------------------------------------------------- corrected totals, confidence, precedence
def test_corrected_total_reconstructable(plain, terms):
    lines = plain.correct_lines("MDS-90003", ids(plain), d("2025-04-10"))
    target = find(lines, "MW-330")
    o = one(plain, invoice("MDS-90003", W3, d("2025-04-01"), d("2025-04-01"), d("2025-04-10"),
                           with_line(lines, target.line_ref, quantity=Decimal(2)), terms=terms))
    assert o.result.flagged and o.result.error_category == "quantity_exceeds_record"
    net = sum(l.amount_cents for l in lines)
    assert o.result.expected_total_cents == net + round(Decimal(net) * Decimal("0.15"))


def test_corrected_total_blocked(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    target = find(lines, "MW-330")
    o = one(world, build(world, terms, with_line(lines, target.line_ref, quantity=Decimal(2))))
    assert o.result.flagged and o.result.expected_total_cents is None
    assert "entitlement_unverified:AMB-13" in o.blank_reasons
    net = o.audit.invoice.net_cents - 30975                                     # one MW-330 day not payable; VAT on the new net (cl. 39)
    assert o.conditional_total_cents == net + vat(terms, net)


def _finding(category, **kw):
    return Finding(check=kw.pop("check", None) or 7, outcome=Outcome.PART_REJECT, message="", invoice_id="I", category=category,
                   line_ref=kw.pop("line_ref", "L"), rule=kw.pop("rule", "r"), **kw)


def test_confidence_grading():
    f = _finding("superseded_rate", confidence=ConfidenceBand.HIGH, affects_total=True)
    working_low = Alternative("backdated_adjustment", "A", "B", ConfidenceBand.LOW, approved=False)
    approved_low = Alternative("rig_up_hour", "B", "C", ConfidenceBand.LOW, approved=True)
    m = Measured()
    m.finding_deps[f.key].append(Dependency("x", "a", "b", "finding_absent", working_low.effective_band))
    assert grade(f, m).confidence is ConfidenceBand.LOW
    m = Measured()
    m.finding_deps[f.key].append(Dependency("x", "a", "b", "finding_absent", approved_low.effective_band))
    assert grade(f, m).confidence is ConfidenceBand.LOW             # approval is a decision, not evidence: LOW stays LOW
    m = Measured()
    m.finding_deps[f.key].append(Dependency("x", "a", "b", "superseded", ConfidenceBand.LOW))
    assert grade(f, m).confidence is ConfidenceBand.HIGH            # rejected for another reason under the alternative
    timing = _finding("invoice_timing", confidence=ConfidenceBand.HIGH, line_ref=None)
    assert grade(timing, Measured()).confidence is ConfidenceBand.MEDIUM


def test_multiple_findings_and_category_precedence(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    copy = line("MDS-90001", 90, D1, W1, "DD-102", 1, "948.60", world.reports[0].report_id, terms=terms)
    dd110 = find(lines, "DD-110")
    changed = with_line(lines, dd110.line_ref, unit_rate=Decimal("1623.32")) + [copy]
    o = one(world, build(world, terms, changed, dated=D3 + timedelta(days=40)))
    assert {"duplicate_charge", "factor_misapplied"} <= categories(o) and "invoice_timing" not in categories(o)
    assert o.result.error_category == "duplicate_charge"
    high_total = _finding("rate_mismatch", confidence=ConfidenceBand.HIGH, affects_total=True)
    medium_total = _finding("duplicate_charge", confidence=ConfidenceBand.MEDIUM, affects_total=True)
    timing = _finding("invoice_timing", confidence=ConfidenceBand.MEDIUM, line_ref=None)
    query = _finding("entitlement_unverified", confidence=ConfidenceBand.HIGH, blocks_total=True)
    assert sorted([query, timing, medium_total, high_total], key=primary_key) == [high_total, medium_total, timing, query]


def test_malformed_data(world, terms):
    lines = world.correct_lines("MDS-90001", ids(world), DATED)
    a, b, c = find(lines, "DD-102"), find(lines, "MW-330"), find(lines, "HC-620")
    changed = with_line(with_line(with_line(lines, a.line_ref, quantity=None, amount_cents=a.amount_cents), b.line_ref, service_code="XX-999"),
                        c.line_ref, description="Something else")
    o = one(world, build(world, terms, changed))
    by_line = {f.line_ref: f.category for f in o.findings if f.category != "entitlement_unverified"}
    assert by_line[a.line_ref] == "line_details_missing" and by_line[b.line_ref] == "service_not_in_contract"
    assert by_line[c.line_ref] == "description_mismatch"
    assert line_of(o, a.line_ref).status is LineStatus.UNDETERMINED
    inv, ls = build(world, terms)
    o = one(world, (inv.__class__(**{**inv.__dict__, "invoice_date": None}), ls))
    assert "invoice_details_missing" in categories(o) and "invoice_timing" not in categories(o)


def test_contract_side_prices_never_read_an_invoice(world):
    """The bundle is built from the reports and the contract before any invoice exists; auditing leaves it untouched."""
    before = [(p.qid, p.status, p.amount_cents) for p in world.bundle.canonical]
    world.audit(build(world, world.terms, cls="HPHT"))
    assert [(p.qid, p.status, p.amount_cents) for p in world.bundle.canonical] == before


# ---------------------------------------------------------------- whole-well class consistency (cl. 4, P2, P3)
def _at_class(world, lines, code, cls, n=0):
    """The lines with the n-th `code` line re-priced at the conditional rate of well class `cls`."""
    target = find(lines, code, n)
    q = world.priced(target.report_ref, code)[0]
    rate = world.bundle.conditional(q.qid)[cls].parts[0].rate_cents
    return with_line(lines, target.line_ref, unit_rate=Decimal(rate) / 100), target


@pytest.mark.parametrize("described", ["Standard", "HPHT"])
def test_mixed_class_rates_on_one_invoice_are_flagged(world, terms, described):
    lines = world.correct_lines("MDS-90001", ids(world), DATED, claimed="Standard")
    lines, target = _at_class(world, lines, "MW-310", "HPHT", 1)
    o = one(world, build(world, terms, lines, cls=described))          # the descriptive class plays no part
    f = next(f for f in o.findings if f.category == "well_class_inconsistent")
    assert f.rule == "class.inconsistent_within_invoice" and o.result.flagged and f.blocks_total and not f.affects_total
    assert target.line_ref in f.observed and "HPHT" in f.observed and "Standard" in f.observed
    assert "not known" in f.message                                    # no class is claimed to be the right one
    assert o.result.expected_total_cents is None and "entitlement_unverified:AMB-13" in o.blank_reasons


@pytest.mark.parametrize("cls", ["Standard", "Extended Reach", "HPHT"])
def test_consistent_class_rates_are_not_flagged(world, terms, cls):
    lines = world.correct_lines("MDS-90001", ids(world), DATED, claimed=cls)
    o = one(world, build(world, terms, lines, cls="Standard"))         # described Standard, billed consistently at `cls`
    assert "well_class_inconsistent" not in categories(o) and not o.result.flagged
    assert o.result.expected_total_cents is None                       # the call-off is still missing


def test_invoices_of_one_well_that_disagree_are_flagged_across(world, terms):
    rids = ids(world)
    a = invoice("MDS-90001", W1, D1, D2, DATED, world.correct_lines("MDS-90001", rids[:2], DATED, claimed="Standard"), terms=terms)
    b = invoice("MDS-90002", W1, D3, D3, DATED, world.correct_lines("MDS-90002", rids[2:], DATED, claimed="HPHT"), terms=terms)
    out = world.audit(a, b)
    for no in ("MDS-90001", "MDS-90002"):
        f = next(f for f in out[no].findings if f.category == "well_class_inconsistent")
        assert f.rule == "class.inconsistent_across_invoices" and f.confidence is ConfidenceBand.MEDIUM
    same = world.audit(a, invoice("MDS-90002", W1, D3, D3, DATED, world.correct_lines("MDS-90002", rids[2:], DATED), terms=terms))
    assert not any(f.category == "well_class_inconsistent" for o in same.values() for f in o.findings)
