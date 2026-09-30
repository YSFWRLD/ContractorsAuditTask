"""Appendix G is contract data, preserved exactly as printed, and lives in the contract layer only."""

import ast
from pathlib import Path

import contractor_audit.domains.drilling as drilling

PRINTED = [
    ("DD-101", "directional hands"), ("DD-102", "night man"), ("DD-110", "mud motor"), ("DD-120", "rotary steerable"),
    ("HC-601", "circulating sub"), ("HC-620", "drilling jars"), ("HC-640", "float sub"), ("LH-711", "mud motor"),
    ("LH-712", "rotary steerable"), ("LH-713", "MWD collar"), ("LH-714", "gamma tool"), ("LW-401", "logging engineers"),
    ("LW-410", "gamma tool"), ("LW-411", "resistivity tool"), ("LW-412", "density-neutron"), ("MW-301", "MWD engineers"),
    ("MW-310", "MWD collar"), ("MW-320", "survey package"), ("MW-330", "real-time link"), ("PD-201", "performance engineer"),
    ("PD-220", "bit and reamer"), ("PD-230", "hydraulics package"), ("RM-511", "hole opener"), ("RM-520", "stabiliser string"),
]


def test_all_24_rows_are_preserved_in_printed_order(terms):
    assert [(m.code, m.report_term) for m in terms.appendix_g] == PRINTED
    assert [m.row for m in terms.appendix_g] == list(range(1, 25))


def test_terms_that_map_to_two_codes_are_kept_not_collapsed(terms):
    assert terms.codes_for_report_term("mud motor") == ("DD-110", "LH-711")
    assert terms.codes_for_report_term("rotary steerable") == ("DD-120", "LH-712")
    assert terms.codes_for_report_term("MWD collar") == ("LH-713", "MW-310")
    assert terms.codes_for_report_term("gamma tool") == ("LH-714", "LW-410")


def test_surprising_pairings_are_literal_not_corrected(terms):
    literal = {(m.code, m.report_term) for m in terms.appendix_g}
    for pair in [("LW-410", "gamma tool"), ("LW-411", "resistivity tool"), ("LW-412", "density-neutron"),
                 ("DD-102", "night man"), ("MW-320", "survey package"), ("HC-640", "float sub"), ("PD-220", "bit and reamer")]:
        assert pair in literal
    assert terms.services["LW-411"].appendix_g_terms == ("resistivity tool",)
    assert terms.services["LW-411"].description == "LWD density and neutron, logged"


def test_the_mapping_is_not_hardcoded_in_ingestion_or_audit_code():
    """Appendix G terms are read from the contract artifact; no other layer may carry them as string constants."""
    words = {t for _, t in PRINTED}
    root = Path(drilling.__file__).parent
    for layer in ("ingestion", "audit", "reporting", "contract"):
        for path in (root / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                          if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                          and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
            constants = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings}
            assert not (constants & words), f"{path.name} hardcodes Appendix G terms {constants & words}"
