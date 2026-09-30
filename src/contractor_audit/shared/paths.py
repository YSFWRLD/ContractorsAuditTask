"""Where raw task data, derived artifacts and final outputs live.

Raw task data is read-only. Everything the pipeline produces goes under
artifacts/<domain>/ (intermediate) or outputs/<domain>/ (final); the combined submission is the root submission.csv.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_ENV_VAR = "CONTRACTOR_AUDIT_DATA"
DEFAULT_DATA_DIRNAME = "invoice-auditing-level-2"


def task_data_root() -> Path:
    """Root of the untouched task checkout; override with $CONTRACTOR_AUDIT_DATA."""
    override = os.environ.get(DATA_ENV_VAR)
    return Path(override).resolve() if override else REPO_ROOT / DEFAULT_DATA_DIRNAME


def artifacts_dir(domain: str) -> Path:
    return REPO_ROOT / "artifacts" / domain


def outputs_dir(domain: str) -> Path:
    return REPO_ROOT / "outputs" / domain


def submission_path() -> Path:
    """The combined submission, at the repository root (the challenge's deliverable)."""
    return REPO_ROOT / "submission.csv"


def template_path() -> Path:
    """The upstream submission template: its ids and order define the submission."""
    return task_data_root() / "submission_template.csv"
