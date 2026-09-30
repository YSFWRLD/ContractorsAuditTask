"""Phase 4 freeze: the policies the civil works audit is frozen with."""

import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from contractor_audit.domains.civil_works.audit.assessment import assess, run_alternatives
from contractor_audit.domains.civil_works.audit.categories import CATEGORIES, CATEGORY_PRECEDENCE, primary_key, primary_tier
from contractor_audit.domains.civil_works.audit.engine import run_audit
from contractor_audit.domains.civil_works.audit.options import TotalPolicy
from contractor_audit.domains.civil_works.audit.review import CATEGORY_TESTS, CHECKLIST
from contractor_audit.domains.civil_works.interpretation import (WORKING_INTERPRETATION as W, ExclusionWindow,
                                                                 IndexedRateMethod, MonthlyRateTreatment)
from contractor_audit.shared.findings import Check, ConfidenceBand

from .conftest import categories, d

D = Decimal
TESTS = Path(__file__).resolve().parents[1]


def _assessed(case, policy=TotalPolicy.STRICT):
    data = case.build()
    return {a.application_no: a for a in assess(data, run_audit(data), run_alternatives(data), policy).applications}


# --------------------------------------------------------------------------- total policy

def test_strict_policy_blanks_a_total_an_unresolved_reading_changes(case):
    case.app("PA-1", d("2025-07-25"))
    case.line("PA-1", "D.41.020", 10, d("2025-07-15"), zone="Z2 North Spur")            # monthly rate: depends on an unresolved reading
    case.line("PA-1", "A.11.010", 100, d("2025-07-14"), rate="4.00", amount=40000)       # overbilled: flags the application
    strict = _assessed(case)["PA-1"]
    assert strict.flagged and strict.expected_total_cents is None
    assert strict.primary_blank_reason == "unresolved_interpretation:monthly_rate_treatment" and strict.total_status == "undetermined"
    graded = _assessed(case, TotalPolicy.GRADED)["PA-1"]
    assert graded.expected_total_cents == strict.contract_total_cents                     # analysis only, never the default


def test_strict_policy_publishes_a_total_no_reading_changes(case):
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "A.11.010", 100, d("2025-03-03"), rate="4.00", amount=40000)
    a = _assessed(case)["PA-1"]
    assert a.expected_total_cents == 38500 and a.total_status == "corrected" and a.outcome == "part-reject"
    assert a.confidence is ConfidenceBand.HIGH


def test_timing_only_breach_is_flagged_without_repricing(case):
    case.app("PA-1", d("2025-04-10"))                                                       # 31 days after the period closed
    case.line("PA-1", "A.11.010", 100, d("2025-03-10"))
    a = _assessed(case)["PA-1"]
    assert a.flagged and a.categories == ("application_timing",)
    assert a.expected_total_cents == a.billed_total_cents and a.total_status == "unchanged" and a.outcome == "query"
    assert a.confidence is ConfidenceBand.MEDIUM                                            # breach certain, consequence not stated


def test_clause_44_leaves_one_measurement_per_item_area_day(case):
    """Two same-day measurements of one item in one work area are a Clause 44 duplicate first: the later is
    disallowed in full, so the Clause 31 cap can only ever bind a single line and its total is defined."""
    case.app("PA-1", d("2025-03-20")).app("PA-2", d("2025-03-21"))
    case.line("PA-1", "E.51.020", 1, d("2025-03-03"))
    case.line("PA-2", "E.51.020", 1, d("2025-03-03"))
    run = run_audit(case.build())
    assert categories(run) == ["duplicate_line"] and run.unresolved == ()


def test_multi_line_cap_guard_blanks_when_reached(case):
    """Defensive guard: if several measurements ever shared the day (not possible while Clause 44 applies), the
    contract would not say which bears the excess, so every application involved is marked unresolved."""
    from contractor_audit.domains.civil_works.audit.context import AuditContext
    from contractor_audit.domains.civil_works.audit.models import Unresolved
    from contractor_audit.domains.civil_works.audit.rules import limits
    case.app("PA-1", d("2025-03-20")).app("PA-2", d("2025-03-21"))
    case.line("PA-1", "E.51.020", 1, d("2025-03-03"))
    case.line("PA-2", "E.51.020", 1, d("2025-03-03"))
    ctx = AuditContext(case.build())
    out = limits.check(ctx, {l.line_ref: l.quantity for l in ctx.lines})
    assert {(u.application_no, u.reason) for u in out if isinstance(u, Unresolved)} == {("PA-1", "limit_allocation_unresolved"), ("PA-2", "limit_allocation_unresolved")}
    assert [o.finding.line_ref for o in out if not isinstance(o, Unresolved)] == ["PA-2-01"]


def test_single_line_daily_limit_breach_has_a_defined_total(case):
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "E.51.020", 3, d("2025-03-03"))
    a = _assessed(case)["PA-1"]
    assert a.expected_total_cents == 68400 and a.blank_reasons == ()


# --------------------------------------------------------------------------- categories and precedence

def test_item_not_in_contract(case):
    case.app("PA-1", d("2025-03-20"))
    ref = case.line("PA-1", "A.11.010", 5, d("2025-03-03"))
    case.lines[-1]["item_code"] = "PR.01"                                                   # a Schedule 8 lump sum, not a Schedule 1 item
    run = run_audit(case.build())
    assert categories(run, ref) == ["item_not_in_contract"]
    assert [u.reason for u in run.unresolved] == ["rate_not_established"] and run.contract_totals["PA-1"] is None


def test_wrong_record_is_reported_once(case):
    case.app("PA-1", d("2025-03-20"))
    rec = case.record("PT-00001", "built 3 large chamber, 1800 dia precast", d("2025-03-09"), area="S-02 Platform South")
    ref = case.line("PA-1", "B.23.020", 10, d("2025-03-03"), record=rec)
    assert categories(run_audit(case.build()), ref) == ["item_record_mismatch"]


def test_primary_category_precedence_ignores_amounts(case):
    case.app("PA-1", d("2025-04-10"), contract_ref="CW-2024-0417-CIV")                     # tier 4 and tier 5 findings
    case.line("PA-1", "A.11.010", 100, d("2025-03-10"), rate="4.00", amount=40000)         # unit rate: small, tier 1
    case.line("PA-1", "B.21.030", 900, d("2025-03-11"))                                    # missing record: large, tier 1
    a = _assessed(case)["PA-1"]
    assert set(a.categories) == {"application_timing", "contract_reference_mismatch", "missing_record", "unit_rate_mismatch"}
    assert a.primary_category == "missing_record"                                          # precedence, not the larger amount
    tiers = sorted((primary_tier(f), f.category) for f in a.findings)
    assert [t for t, _ in tiers] == [1, 1, 4, 5]


def test_precedence_is_total_and_fixed():
    assert set(CATEGORY_PRECEDENCE) == set(CATEGORIES) and len(CATEGORY_PRECEDENCE) == len(CATEGORIES)
    assert CATEGORY_PRECEDENCE[-1].value == "application_timing"


# --------------------------------------------------------------------------- unresolved readings

def test_indexation_uncertainty(case):
    case.app("PA-1", d("2025-05-20"))
    ref = case.line("PA-1", "C.31.010", 48, d("2025-05-13"), zone="Z2 North Spur", ground="G2 Firm Sabkha")   # billed 93.75 (29A)
    assert run_audit(case.build()).findings == ()
    alt = run_audit(case.build(), interp=W.with_(indexed_rate_method=IndexedRateMethod.APPENDIX_B_UNINDEXED))
    assert categories(alt, ref) == ["unit_rate_mismatch"] and alt.findings[0].expected == "91.37"
    a = _assessed(case)["PA-1"]
    assert not a.flagged and a.confidence is ConfidenceBand.HIGH           # settled by the text (Clause 2, Sch 2A); App B kept as sensitivity
    assert {d.switch for d in a.would_flag_under} == {"indexed_rate_method"}
    assert all(d.band is ConfidenceBand.HIGH for d in a.would_flag_under)


@pytest.mark.parametrize("day, rate", [("2025-04-30", "67.31"), ("2025-05-01", "227.37"), ("2025-09-30", "233.73"),
                                       ("2025-10-01", "233.73"), ("2025-11-30", "233.73"), ("2025-12-01", "229.60")])
def test_monthly_rate_boundaries(case, day, rate):
    """D.41.020 in Z2 (x1.06): BoQ 63.50, May 214.50, Sep 220.50 carried to Oct/Nov, S2 228.00 less 5% from December."""
    case.app("PA-1", d(day) + timedelta(10))
    ref = case.line("PA-1", "D.41.020", 10, d(day), zone="Z2 North Spur")
    run = run_audit(case.build())
    assert run.findings == () and run.lines[ref].contract_billed.unit_rate == D(rate)


def test_monthly_rate_uncertainty(case):
    case.app("PA-1", d("2025-07-25"))
    ref = case.line("PA-1", "D.41.020", 10, d("2025-07-15"), zone="Z2 North Spur")
    alt = run_audit(case.build(), interp=W.with_(monthly_rate_treatment=MonthlyRateTreatment.FINAL_RATE))
    assert categories(alt, ref) == ["unit_rate_mismatch"] and alt.findings[0].expected == "226.40"


@pytest.mark.parametrize("gap, working, alternative", [(-3, False, False), (-2, False, False), (0, True, False),
                                                        (2, True, True), (3, False, False)])
def test_exclusion_direction_and_boundaries(case, gap, working, alternative):
    """A.14.020 is excluded only after A.14.010 (Sch 4 Part 5: 'following'), up to and including day +2."""
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "A.14.010", 5, d("2025-03-10"), record=case.record("CT-00001", "brought in 5 cube of fill, compacted in layers", d("2025-03-10")))
    ref = case.line("PA-1", "A.14.020", 5, d("2025-03-10") + timedelta(gap))
    assert (categories(run_audit(case.build()), ref) == ["exclusion_window_violation"]) is working
    alt = run_audit(case.build(), interp=W.with_(exclusion_window=ExclusionWindow.SAME_DAY_EXCLUDED))
    assert (categories(alt, ref) == ["exclusion_window_violation"]) is alternative


@pytest.mark.parametrize("before, qty, split, rate, amount", [
    (58, 2, False, "4120.00", 824000),        # 58 + 2 ends exactly on the 60 t edge: all at 100%
    (58, 3, True, "4120.00", 1223640),        # crosses: 2 x 4120.00 + 1 x 3996.40, printed at the pre-rebate rate
    (60, 1, False, "3996.40", 399640),        # starts on the edge: wholly in the 97% band
])
def test_band_edge_boundaries(case, before, qty, split, rate, amount):
    """B.23.010's first band ends at 60 t (Sch 4 Part 3: '1 to 60', '61 to 240')."""
    case.app("PA-1", d("2025-03-20"))
    case.line("PA-1", "B.23.010", before, d("2025-03-03"), record=case.record("JS-00001", f"fixed {before} tonne of bar, cut and bent to schedule", d("2025-03-03")))
    ref = case.line("PA-1", "B.23.010", qty, d("2025-03-04"), record=case.record("JS-00002", f"fixed {qty} tonne of bar, cut and bent to schedule", d("2025-03-04")),
                    rate=rate, amount=amount)
    run = run_audit(case.build())
    assert run.lines[ref].contract_billed.is_split is split
    assert run.findings == ()


# --------------------------------------------------------------------------- real data

def test_real_freeze_numbers(audit_result):
    apps = audit_result.applications
    flagged = [a for a in apps if a.flagged]
    assert (len(apps), len(flagged), len(audit_result.findings)) == (900, 77, 95)
    published = [a for a in flagged if a.expected_total_cents is not None]
    assert len(published) + sum(a.expected_total_cents is None for a in flagged) == len(flagged)
    assert all(a.primary_blank_reason == (a.blank_reasons[0] if a.blank_reasons else "") for a in apps)
    assert all(a.total_status == "correct" for a in apps if not a.flagged)


def test_real_timing_only_applications(audit_result):
    only = [a for a in audit_result.applications if a.categories == ("application_timing",)]
    assert {a.application_no for a in only} == {"PA-00125", "PA-00699", "PA-00708"}
    assert all(a.confidence is ConfidenceBand.MEDIUM and a.outcome == "query" for a in only)


def test_real_backdated_adjustment_sensitivity(audit_result):
    a6 = next(a for a in audit_result.applications if a.application_no == "PA-00006")
    assert a6.confidence is ConfidenceBand.LOW and a6.primary_category == "adjustment_missing"
    alt = next(r for r in audit_result.alternatives if r.field == "retro_adjustment_trigger")
    assert {f.invoice_id for f in alt.run.findings if f.category == "adjustment_missing"} == {"PA-00443", "PA-00678"}


def test_real_retention_release_is_outside_the_total(audit_result):
    a = next(a for a in audit_result.applications if a.application_no == "PA-00678")
    rel = next(f for f in a.findings if f.rule == "adjustments.clause_45a_retention_release")
    assert rel.outside_total and not rel.affects_total and a.primary_category == "work_after_final_completion"


def test_real_duplicate_ordering_is_a_measured_dependency(audit_result):
    moving = [f for f in audit_result.findings if any(d.switch == "measurement_order" for d in f.dependencies if d.effect == "finding_absent")]
    assert len(moving) == 7 and all(f.confidence is ConfidenceBand.MEDIUM for f in moving)


# --------------------------------------------------------------------------- the review's references are real

def test_review_names_real_tests():
    names = set()
    for p in TESTS.rglob("test_*.py"):
        names |= {f"{p.relative_to(TESTS).as_posix()}::{m}" for m in re.findall(r"^def (test_\w+)", p.read_text(encoding="utf-8"), re.M)}
    refs = list(CATEGORY_TESTS.values())
    for *_, tests in CHECKLIST:
        head, _, rest = tests.partition("::")
        refs += [f"{head}::{t.strip()}" for t in rest.split(";")]
    assert set(CATEGORY_TESTS) == {c.value for c in CATEGORIES}
    assert [c for c, *_ in CHECKLIST] == list(Check)
    missing = [r for r in refs if r not in names]
    assert not missing, missing
