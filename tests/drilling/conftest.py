import pytest

from contractor_audit.domains.drilling.contract.loader import (
    AMBIGUITIES_FILENAME, TERMS_FILENAME, load_ambiguities, load_contract_terms, load_raw,
)
from contractor_audit.domains.drilling.ingestion.indexes import build_indexes
from contractor_audit.domains.drilling.ingestion.loaders import load_dataset
from contractor_audit.domains.drilling.ingestion.validation import validate
from contractor_audit.domains.drilling.interpretation.engine import interpret
from contractor_audit.domains.drilling.interpretation.switches import build_switches
from contractor_audit.domains.drilling.reporting import ambiguity_evidence
from contractor_audit.shared import paths

ARTIFACTS = paths.artifacts_dir("drilling")
TERMS_PATH = ARTIFACTS / TERMS_FILENAME
AMBIGUITIES_PATH = ARTIFACTS / AMBIGUITIES_FILENAME


@pytest.fixture(scope="session")
def raw_terms():
    return load_raw(TERMS_PATH)


@pytest.fixture(scope="session")
def raw_ambiguities():
    return load_raw(AMBIGUITIES_PATH)


@pytest.fixture(scope="session")
def terms():
    return load_contract_terms(TERMS_PATH, AMBIGUITIES_PATH)


@pytest.fixture(scope="session")
def ambiguities():
    return {a.id: a for a in load_ambiguities(AMBIGUITIES_PATH)}


@pytest.fixture(scope="session")
def dataset(data_root):
    return load_dataset(data_root)


@pytest.fixture(scope="session")
def indexes(dataset):
    return build_indexes(dataset)


@pytest.fixture(scope="session")
def structural(dataset, indexes):
    return validate(dataset, indexes)


@pytest.fixture(scope="session")
def evidence(dataset, indexes, terms):
    return ambiguity_evidence.collect(dataset, indexes, terms)


@pytest.fixture(scope="session")
def switches(ambiguities):
    return build_switches(ambiguities)


@pytest.fixture(scope="session")
def interpretation(dataset, terms, ambiguities):
    return interpret(dataset.reports, terms, ambiguities)


@pytest.fixture(scope="session")
def reports_by_id(dataset):
    return {r.report_id: r for r in dataset.reports}
