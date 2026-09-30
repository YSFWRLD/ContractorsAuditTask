"""Civil works entry point: raw files -> canonical models -> checks -> InvoiceResults."""

from pathlib import Path

from contractor_audit.domains.civil_works import artifacts
from contractor_audit.domains.civil_works.sources import CivilWorksSources
from contractor_audit.shared.domain import RunContext
from contractor_audit.shared.findings import InvoiceResult


class CivilWorksDomain:
    name = "civil_works"

    def required_sources(self, data_root: Path) -> list[Path]:
        return CivilWorksSources.from_data_root(data_root).required()

    def build_artifacts(self, ctx: RunContext) -> list[Path]:
        ctx.artifacts_dir.mkdir(parents=True, exist_ok=True)
        return artifacts.build(ctx.data_root, ctx.artifacts_dir).written

    def run(self, ctx: RunContext) -> list[InvoiceResult]:
        """Audit every application and write the civil works draft outputs (not the combined submission)."""
        from contractor_audit.domains.civil_works.audit.assessment import audit
        from contractor_audit.domains.civil_works.audit.context import load_audit_data
        from contractor_audit.domains.civil_works.audit.reports import invoice_results, write_outputs

        result = audit(load_audit_data(ctx.data_root, ctx.artifacts_dir))
        write_outputs(result, ctx.outputs_dir)
        return invoice_results(result)


DOMAIN = CivilWorksDomain()
