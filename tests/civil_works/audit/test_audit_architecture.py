"""Audit layer boundaries: no pricing formulas, no floats in money, no network, pricing untouched by audit code."""

import ast
from pathlib import Path

import contractor_audit.domains.civil_works as cw
from contractor_audit.domains.civil_works.audit.assessment import _primary
from contractor_audit.domains.civil_works.audit.categories import CATEGORIES, CATEGORY_INFO
from contractor_audit.shared.findings import ConfidenceBand, Finding, Check, Outcome

AUDIT = Path(cw.__file__).parent / "audit"
PRICING_MODULES = ("pricing.py", "rates.py", "rebates.py", "valuation.py", "rounding.py")


def _trees():
    for path in sorted(AUDIT.rglob("*.py")):
        yield path, ast.parse(path.read_text(encoding="utf-8"))


def test_pricing_code_does_not_import_the_audit():
    for name in PRICING_MODULES:
        tree = ast.parse((Path(cw.__file__).parent / name).read_text(encoding="utf-8"))
        mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not any(m and ".audit" in m for m in mods), name


def test_audit_has_no_float_money_and_no_network():
    for path, tree in _trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ("float", "round"), f"{path.name}: {node.func.id}()"
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                assert not any(n.split(".")[0] in ("socket", "urllib", "http", "requests", "httpx") for n in names), path.name


def test_audit_does_not_reimplement_pricing():
    """Rules may not multiply by zone/ground/uplift factors themselves: every price comes from PricingEngine.

    review.py is exempt by design: it re-derives band-split segment rates outside the ledger to cross-check
    the engine, and never feeds a value back into a finding or total.
    """
    for path, _ in _trees():
        if path.name == "review.py":
            continue
        text = path.read_text(encoding="utf-8")
        for token in ("zone_factors[", "ground_factors[", "night_uplift_percent[", "round_built_up_rate", "site_materials_index["):
            assert token not in text, f"{path.name} uses {token}"


def test_every_category_is_documented():
    assert set(CATEGORY_INFO) == set(CATEGORIES) and len(CATEGORIES) == len({c.value for c in CATEGORIES})


def test_confidence_scores_are_fixed_and_ordered():
    assert [b.score for b in (ConfidenceBand.HIGH, ConfidenceBand.MEDIUM, ConfidenceBand.LOW)] == [0.95, 0.75, 0.55]
    assert ConfidenceBand.weakest([ConfidenceBand.HIGH, ConfidenceBand.LOW]) is ConfidenceBand.LOW
    assert ConfidenceBand.strongest([]) is ConfidenceBand.HIGH


def test_primary_category_is_deterministic():
    def f(cat, conf, impact, affects=True):
        return Finding(Check.ARITHMETIC, Outcome.PART_REJECT, "m", invoice_id="A", category=cat, rule="r", impact_cents=impact,
                       affects_total=affects, confidence=conf)
    fs = [f("unit_rate_mismatch", ConfidenceBand.HIGH, 100), f("missing_record", ConfidenceBand.HIGH, 5000),
          f("exclusion_window_violation", ConfidenceBand.LOW, 999999), f("application_timing", ConfidenceBand.HIGH, None, affects=False)]
    assert _primary(fs) == "missing_record" and _primary(list(reversed(fs))) == "missing_record"
