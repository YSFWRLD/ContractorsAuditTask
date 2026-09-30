"""Content fingerprints for raw source files, so derived artifacts can say exactly what they were built from."""

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_tree(directory: Path, pattern: str = "*") -> tuple[str, int]:
    """Order-independent fingerprint of every file matching `pattern` directly under `directory`.

    Returns (digest, file_count). Renaming, adding, removing or editing any file changes the digest.
    """
    digest = hashlib.sha256()
    files = sorted(p for p in directory.glob(pattern) if p.is_file())
    for path in files:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), len(files)
