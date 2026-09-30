"""Every open Phase 1 reading is a named switch; defaults come only from Phase 1 preferences."""

from contractor_audit.domains.drilling.contract.models import AmbiguityStatus
from contractor_audit.domains.drilling.interpretation.switches import NOT_DERIVED, AppliesIn, phase3_switches


def test_every_ambiguity_with_an_effect_has_a_switch(switches, ambiguities):
    covered = {s.ambiguity_id for s in switches.values()}
    expected = {a for a, amb in ambiguities.items() if amb.status is not AmbiguityStatus.NOTED}
    assert covered == expected
    assert len({s.name for s in switches.values()}) == len(switches)


def test_readings_mirror_the_register_and_defaults_are_not_invented(switches, ambiguities):
    for s in switches.values():
        amb = ambiguities[s.ambiguity_id]
        assert {r.ambiguity_reading for r in s.readings} == {r.id for r in amb.readings}
        if amb.preferred_reading is None:
            assert s.default is None
        else:
            assert s.reading(s.default).ambiguity_reading == amb.preferred_reading
        assert s.requires_approval == (amb.status in (AmbiguityStatus.OPEN, AmbiguityStatus.EVIDENCE_NOT_PROVIDED))


def test_phase3_switches_are_evaluated_under_every_reading(switches, interpretation):
    seen = {}
    for q in interpretation.quantities:
        for name, value in q.readings:          # a quantity that exists only under that reading
            seen.setdefault(name, set()).add(value)
        for key, _ in q.detail:                 # or one quantity carrying the figure under each reading (lih_hours)
            if "." in key:
                name, value = key.split(".", 1)
                seen.setdefault(name, set()).add(value)
    for name, s in phase3_switches(switches).items():
        if s.requires_approval:
            expected = {v for v in s.values if (name, v) not in NOT_DERIVED}
            assert seen.get(name) == expected, name
    assert ("dd121_condition", "EVERY_STANDBY_DAY_OF_RSS_WELL") in NOT_DERIVED
    assert switches["lih_hours"].applies_in is AppliesIn.PHASE_3_QUANTITIES
    assert switches["rig_up_hour"].applies_in is AppliesIn.PHASE_4_PRICING
    assert switches["backdated_adjustment"].applies_in is AppliesIn.PHASE_5_AUDIT


def test_resolved_by_text_switches_are_fixed_at_their_text_reading(switches):
    assert (switches["appendix_g_duplicates"].default, switches["appendix_g_duplicates"].requires_approval) == ("CONTEXT_SELECTS", False)
    assert (switches["principal_discount_combination"].default, switches["principal_discount_combination"].requires_approval) == ("LATER_REPLACES", False)


def test_switches_needing_approval(switches):
    needing = sorted(n for n, s in switches.items() if s.requires_approval)
    assert "appendix_g_duplicates" not in needing and len(needing) == 24
