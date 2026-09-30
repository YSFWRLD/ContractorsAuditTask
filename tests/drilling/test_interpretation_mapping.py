"""Report words map only to contract candidates, with explicit statuses and exact provenance."""

from collections import Counter

from contractor_audit.domains.drilling.interpretation.ambiguity import literal_vocabulary, shifted_vocabulary, vocabularies
from contractor_audit.domains.drilling.interpretation.models import MappingStatus


def test_the_vocabulary_is_the_contracts_appendix_g(terms):
    literal = literal_vocabulary(terms)
    assert set(literal.codes) == {m.report_term for m in terms.appendix_g}
    for term, codes in literal.codes.items():
        assert codes == terms.codes_for_report_term(term)


def test_the_shifted_reading_moves_only_the_lwd_rows(terms):
    literal, shifted = literal_vocabulary(terms), shifted_vocabulary(terms)
    changed = {t for t in literal.codes if set(literal.codes[t]) != set(shifted.codes[t])}
    assert changed == {"gamma tool", "resistivity tool", "density-neutron"}
    assert shifted.codes["gamma tool"] == () and shifted.codes["resistivity tool"] == ("LH-714", "LW-410")
    assert shifted.codes["density-neutron"] == ("LW-411",) and not shifted.term_for("LW-412")


def test_every_candidate_is_an_allowed_contract_code(interpretation, terms):
    vocabs = vocabularies(terms)
    for m in interpretation.mappings:
        allowed = set(vocabs["LITERAL"].codes.get(m.term, ())) | set(vocabs["LWD_ROWS_SHIFTED"].codes.get(m.term, ()))
        assert {c.service_code for c in m.candidates} <= allowed, m.term
        assert all(c.service_code in terms.services for c in m.candidates)


def test_statuses_by_term(interpretation):
    statuses = {}
    for m in interpretation.mappings:
        statuses.setdefault((m.source_field.label, m.term), set()).add(m.status)
    unresolved = {t for (_, t), s in statuses.items() if MappingStatus.UNRESOLVED_INTERPRETATION in s}
    assert unresolved == {"gamma tool", "resistivity tool", "density-neutron"}
    by_context = {t for (_, t), s in statuses.items() if MappingStatus.IDENTIFIED_BY_CONTEXT in s}
    assert by_context == {"mud motor", "rotary steerable", "MWD collar"}
    assert all(len(s) == 1 for s in statuses.values())
    assert not any(MappingStatus.AMBIGUOUS in s for s in statuses.values())


def test_duplicate_terms_resolve_only_through_their_field_context(interpretation, terms):
    for m in interpretation.mappings:
        if m.status is not MappingStatus.IDENTIFIED_BY_CONTEXT:
            continue
        (cand,) = m.candidates
        lost = terms.services[cand.service_code].rate_basis.value == "CLAUSE_31"
        assert lost == (m.source_field.section == "E"), (m.term, m.source_field.label)
        assert "AMB-16" in cand.ambiguity_ids and "footnote" in cand.note


def test_reading_dependent_terms_keep_every_readings_candidates(interpretation):
    m = next(m for m in interpretation.mappings if m.term == "resistivity tool")
    assert {(c.service_code, c.readings) for c in m.candidates} == {
        ("LW-411", (("appendix_g_reading", "LITERAL"),)), ("LW-410", (("appendix_g_reading", "LWD_ROWS_SHIFTED"),))}
    gamma = next(m for m in interpretation.mappings if m.term == "gamma tool" and m.source_field.section == "A")
    assert [c.service_code for c in gamma.candidates] == ["LW-410"] and "no candidate under LWD_ROWS_SHIFTED" in gamma.unresolved_reason


def test_mapping_provenance_points_at_the_exact_report_line(interpretation, reports_by_id):
    for m in interpretation.mappings[::97]:
        r = reports_by_id[m.report_id]
        raw = next(f for f in r.fields if f.section == m.source_field.section and f.label == m.source_field.label)
        assert (raw.value, raw.line, r.source.file) == (m.source_field.raw_value, m.source_field.line, m.source_field.source_file)
        assert m.term in raw.value


def test_every_report_is_interpreted_and_every_word_is_mapped(interpretation, dataset):
    assert interpretation.reports_interpreted == 8151
    words = Counter(w for r in dataset.reports for w in r.operations.in_the_hole) + Counter(c.role for r in dataset.reports for c in r.operations.crew)
    mapped = Counter(m.term for m in interpretation.mappings if m.source_field.section == "A")
    assert mapped == words
    assert sum(1 for m in interpretation.mappings if m.source_field.section == "E") == 54
