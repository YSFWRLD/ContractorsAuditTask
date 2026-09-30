from contractor_audit.shared.provenance import sha256_file, sha256_tree


def test_tree_digest_changes_on_edit_rename_add(tmp_path):
    (tmp_path / "a.txt").write_text("one", encoding="utf-8")
    (tmp_path / "b.txt").write_text("two", encoding="utf-8")
    base, count = sha256_tree(tmp_path, "*.txt")
    assert count == 2

    (tmp_path / "b.txt").write_text("two!", encoding="utf-8")
    edited, _ = sha256_tree(tmp_path, "*.txt")
    (tmp_path / "b.txt").rename(tmp_path / "c.txt")
    renamed, _ = sha256_tree(tmp_path, "*.txt")
    (tmp_path / "d.txt").write_text("", encoding="utf-8")
    added, n = sha256_tree(tmp_path, "*.txt")
    assert len({base, edited, renamed, added}) == 4 and n == 3


def test_tree_digest_ignores_other_patterns(tmp_path):
    (tmp_path / "a.txt").write_text("one", encoding="utf-8")
    before, _ = sha256_tree(tmp_path, "*.txt")
    (tmp_path / "notes.md").write_text("x", encoding="utf-8")
    assert sha256_tree(tmp_path, "*.txt")[0] == before


def test_file_digest(tmp_path):
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    assert sha256_file(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
