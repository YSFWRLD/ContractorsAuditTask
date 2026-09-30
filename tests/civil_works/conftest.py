import pytest

from contractor_audit.domains.civil_works.contract import EXTRACTION_FILENAME, load_contract, load_raw_extraction
from contractor_audit.domains.civil_works.loaders import load_application_lines, load_applications
from contractor_audit.domains.civil_works.records import load_records
from contractor_audit.domains.civil_works.sources import CivilWorksSources
from contractor_audit.shared import paths

EXTRACTION_PATH = paths.artifacts_dir("civil_works") / EXTRACTION_FILENAME


@pytest.fixture(scope="session")
def raw_extraction():
    return load_raw_extraction(EXTRACTION_PATH)


@pytest.fixture(scope="session")
def terms():
    return load_contract(EXTRACTION_PATH)


@pytest.fixture(scope="session")
def cw_sources(data_root):
    return CivilWorksSources.from_data_root(data_root)


@pytest.fixture(scope="session")
def applications(cw_sources):
    return load_applications(cw_sources.applications_csv)


@pytest.fixture(scope="session")
def lines(cw_sources):
    return load_application_lines(cw_sources.application_lines_csv)


@pytest.fixture(scope="session")
def record_set(cw_sources):
    return load_records(cw_sources.records_dir)
