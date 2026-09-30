import pytest

from contractor_audit.shared import paths


@pytest.fixture(scope="session")
def data_root():
    root = paths.task_data_root()
    if not root.is_dir():
        pytest.skip(f"task data not found at {root}; set ${paths.DATA_ENV_VAR}")
    return root
