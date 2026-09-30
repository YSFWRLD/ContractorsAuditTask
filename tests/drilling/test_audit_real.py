"""The drilling audit on the real data: committed outputs are current, and the policy invariants hold on every invoice."""

import csv
from collections import Counter

import pytest

from contractor_audit.domains.drilling import DOMAIN
from contractor_audit.domains.drilling.audit.categories import CATEGORY_INFO, Category, flags
from contractor_audit.domains.drilling.audit.models import LineStatus
from contractor_audit.domains.drilling.audit.policy import AUDIT_SWITCHES
from contractor_audit.domains.drilling.pipeline import template_ids
from contractor_audit.domains.drilling.reporting import audit_outputs
from contractor_audit.shared import paths
from contractor_audit.shared.domain import RunContext
from contractor_audit.shared.findings import ConfidenceBand

OUT = paths.outputs_dir("drilling")


@pytest.fixture(scope="session")
def drilling_audit(data_root):
    report, dataset = DOMAIN.audit(RunContext.for_domain("drilling"))
    return report, dataset, {o.result.invoice_id: o for o in report.outcomes}


def test_committed_outputs_are_current_and_deterministic(drilling_audit, data_root, tmp_path):
    report, dataset, _ = drilling_audit
    written = audit_outputs.write(report, dataset, template_ids(data_root), tmp_path / "a")
    again = audit_outputs.write(report, dataset, template_ids(data_root), tmp_path / "b")
    assert [p.name for p in written] == list(audit_outputs.FILES)
    assert [p.read_bytes() for p in written] == [p.read_bytes() for p in again]
    stale = [p.name for p in written if p.read_bytes() != (OUT / p.name).read_bytes()]
    assert not stale, f"rerun `contractor-audit run --domain drilling`: {stale}"


def test_draft_predictions_schema(drilling_audit, data_root):
    _, dataset, _ = drilling_audit
    with open(OUT / "draft_predictions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == audit_outputs.TEMPLATE_COLUMNS
    assert [r["invoice_id"] for r in rows] == template_ids(data_root) and len(rows) == 1906
    totals = {i.invoice_no: i.total_cents for i in dataset.invoices}
    for r in rows:
        assert r["flagged"] in ("0", "1") and r["confidence"] in ("0.95", "0.75", "0.55")
        assert (r["error_category"] != "") == (r["flagged"] == "1")
        assert r["error_category"] == "" or Category(r["error_category"]) and flags(r["error_category"])
        assert int(r["billed_total_cents"]) == totals[r["invoice_id"]]
        assert r["expected_total_cents"] == "" or r["expected_total_cents"].lstrip("-").isdigit()
    assert not (paths.REPO_ROOT / "outputs" / "submission.csv").exists()


def test_real_audit_invariants(drilling_audit):
    report, _, by_id = drilling_audit
    for o in by_id.values():
        flagging = [f for f in o.findings if flags(f.category)]
        assert o.result.flagged == bool(flagging)
        assert o.outcome.value in ("pass", "query", "part-reject")
        for f in flagging:
            assert f.clause and f.evidence and f.check is CATEGORY_INFO[Category(f.category)].check and f.invoice_id == o.result.invoice_id
        # the call-offs are missing: no total is published where a charge's entitlement rests on them
        if o.total_status != "determined":
            assert o.result.expected_total_cents is None and o.blank_reasons
        # a clean invoice is exactly what the claimed entitlement would make it, unless a line is billed at another class's rate
        if not o.result.flagged:
            differs = any(f.rule == "entitlement.descriptive_class_differs" for f in o.findings)
            assert (o.conditional_total_cents == o.result.billed_total_cents) is not differs
            assert o.band is not ConfidenceBand.HIGH                      # its class-rated charges rest on the missing call-off
    assert report.policy.awaiting_approval == ()                     # all five decided (prompts/drilling/08)
    assert not any("below the" in x for o in by_id.values() for l in o.audit.lines for x in l.observations)


def test_entitlement_is_never_taken_from_the_invoice(drilling_audit):
    _, _, by_id = drilling_audit
    lines = [l for o in by_id.values() for l in o.audit.lines]
    conditional = Counter(l.line.service_code for l in lines if l.status is LineStatus.CONDITIONAL)
    assert set(conditional) == {"DD-120", "LW-410", "LW-411", "LW-412", "LW-413", "MW-310", "MW-320", "PD-201", "PD-210"}
    assert all(l.status is not LineStatus.DETERMINED or l.line.service_code not in conditional or l.amount_cents == 0 for l in lines)


def test_known_cases(drilling_audit):
    _, _, by_id = drilling_audit

    def cats(i):
        return {f.category for f in by_id[i].findings if flags(f.category)}
    assert {i for i, o in by_id.items() if "contract_reference_mismatch" in cats(i)} == {"MDS-00672", "MDS-00988", "MDS-01799"}
    assert {i for i, o in by_id.items() if "invoice_discount_error" in cats(i)} == {"MDS-00072", "MDS-00282", "MDS-01049"}
    assert {i for i, o in by_id.items() if "work_outside_contract_term" in cats(i)} == {"MDS-01619", "MDS-01798", "MDS-01860"}
    assert {i for i, o in by_id.items() if "invoice_arithmetic" in cats(i)} == {"MDS-00551", "MDS-00916", "MDS-01317"}
    dup = {f.line_ref: f.rule for o in by_id.values() for f in o.findings if f.category == "duplicate_charge"}
    assert dup["MDS-01352-007"] == "duplicates.across_invoices" and dup["MDS-00128-026"] == "duplicates.within_invoice"
    adj = by_id["MDS-01625"]
    assert adj.result.error_category == "backdated_adjustment_missing" and adj.band is ConfidenceBand.LOW
    assert "not_chargeable_on_standby" in cats("MDS-00626") and "discount_misapplied" in cats("MDS-00121")


def test_dependencies_are_measured_for_every_alternative(drilling_audit):
    report, _, _ = drilling_audit
    rows = {(r["switch"], r["alternative"]): r for r in report.measured.rows}
    assert ("rig_up_hour", "PER_BHA_RUN") in rows and ("volume_tier_scope", "CONTRACT_WIDE") in rows
    assert {s for s, _ in rows} >= set(AUDIT_SWITCHES)
    observed = sorted(o.result.invoice_id for o in report.outcomes if o.audit.observations)
    assert observed == ["MDS-00038", "MDS-00199", "MDS-00537", "MDS-00645", "MDS-00828", "MDS-01258"]
    assert rows[("submission_date", "INVOICE_DATE_IS_SUBMISSION")]["flags_added"] == observed    # timing only if the invoice date were proof
    # measured, not asserted: the superseded per-run reading leaves 3,897 DD-120 lines one hour below the record
    assert rows[("rig_up_hour", "PER_BHA_RUN")]["below_record_lines"] == {"DD-120": 3897}
    assert rows[("backdated_adjustment", "NO_REPRICING")]["flags_removed"] == ["MDS-01625"]
