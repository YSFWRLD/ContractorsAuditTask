"""The upstream task data must be byte-for-byte what the committed source inventory recorded."""

import json

from contractor_audit.domains.civil_works.artifacts import SOURCE_INVENTORY, source_inventory
from contractor_audit.shared import paths


def test_task_data_matches_recorded_fingerprints(data_root, cw_sources):
    recorded = json.loads((paths.artifacts_dir("civil_works") / SOURCE_INVENTORY).read_text(encoding="utf-8"))
    assert source_inventory(cw_sources, data_root) == recorded


def test_inventory_counts(data_root, cw_sources):
    inv = source_inventory(cw_sources, data_root)
    rows = {f["path"]: f.get("data_rows") for f in inv["files"]}
    assert rows["civilwork/invoices/applications.csv"] == 900
    assert rows["civilwork/invoices/application_lines.csv"] == 7746
    assert inv["records"]["files"] == 2169
    assert inv["task_wide"][0]["data_rows"] == 2806
