"""Source fidelity: every contractual source is represented, fingerprinted and fully paged."""

from contractor_audit.domains.drilling.contract.loader import load_raw
from contractor_audit.domains.drilling.sources import DrillingSources
from contractor_audit.shared import paths
from contractor_audit.shared.provenance import sha256_file


def test_every_contractual_source_file_is_represented_with_its_hash(raw_terms, data_root):
    sources = DrillingSources.from_data_root(data_root)
    on_disk = {p.relative_to(data_root).as_posix(): p for d in (sources.contract_pdf.parent, sources.guidelines.parent)
               for p in d.iterdir() if p.is_file()}
    recorded = {f["file"]: f for f in raw_terms["source_files"]}
    assert set(on_disk) == set(recorded), "a contract/guidelines file is missing from contract_terms.json"
    for rel, path in on_disk.items():
        assert recorded[rel]["sha256"] == sha256_file(path), rel
        assert recorded[rel]["bytes"] == path.stat().st_size, rel


def test_the_package_is_one_42_page_scan_split_into_34_documents(raw_terms):
    pdf = next(f for f in raw_terms["source_files"] if f["file"].endswith(".pdf"))
    assert pdf["pages"] == 42 and pdf["text_layer"] is False
    docs = raw_terms["documents"]
    covered = [p for d in docs for p in range(d["pages"][0], d["pages"][1] + 1)]
    assert covered == list(range(1, 43))
    assert all(d["printed_pages"] == d["pages"] for d in docs)
    kinds = [d["kind"] for d in docs]
    assert kinds.count("instrument") == 5 and kinds.count("variation_schedule") == 1


def test_contents_and_clause_2_omit_exactly_the_unlisted_material(raw_terms):
    unlisted = {d["id"] for d in raw_terms["documents"] if not d["in_contents"] and d["kind"] not in ("agreement", "contents", "instrument")}
    assert unlisted == {"PART-VIII", "PART-IX", "SCH-2C", "SCH-2D", "SCH-7", "SCH-8", "APP-D", "APP-E", "APP-F", "APP-G", "SOV"}
    listed_in_cl2 = {d["id"] for d in raw_terms["documents"] if d["listed_in_clause_2"]}
    assert listed_in_cl2 == {"AGREEMENT", "PART-I", "PART-II", "PART-III", "PART-IV", "PART-V", "PART-VI", "PART-VII",
                             "SCH-1", "SCH-2", "SCH-3", "SCH-4", "SCH-5", "SCH-6", "APP-A", "APP-B", "APP-C"}


def test_two_transcription_passes_agree_with_each_other_and_with_the_artifact(raw_terms):
    review = paths.artifacts_dir("drilling") / "review"
    a = load_raw(review / "transcription_pass_a.json")
    b = load_raw(review / "transcription_pass_b.json")
    assert a == b
    services = {s["code"]: s for s in raw_terms["services"]}
    for code, (unit, printed) in a["sch1"].items():
        assert services[code]["unit"] == unit
        assert services[code]["rate"]["printed"].replace(",", "") == printed or services[code]["rate"]["printed"] == printed
    assert raw_terms["price_index"]["monthly_index"] == a["index"]
    assert raw_terms["lost_in_hole"]["exchange_rates"]["months"] == a["fx"]
    assert [[r["code"], r["report_term"]] for r in raw_terms["appendix_g"]["rows"]] == a["appendix_g"]
    assert raw_terms["extraction"]["cross_check"]["discrepancies"] == 0
