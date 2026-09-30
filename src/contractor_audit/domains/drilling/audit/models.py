"""What the drilling audit produces before findings are graded: line assessments and invoice valuations."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from contractor_audit.domains.drilling.ingestion.models import DrillingInvoice, InvoiceLine
from contractor_audit.shared.findings import Finding


class LineStatus(StrEnum):
    DETERMINED = "DETERMINED"        # the payable amount is established from contract and report (it may be 0)
    CONDITIONAL = "CONDITIONAL"      # payable only if the missing call-off establishes the entitlement (AMB-13)
    UNDETERMINED = "UNDETERMINED"    # cannot be valued from the supplied evidence (identification, record held back, no price)
    INVOICE_LEVEL = "INVOICE_LEVEL"  # DS-900: valued on the invoice total (cl. 38)


class TotalStatus(StrEnum):
    DETERMINED = "determined"        # every component is established
    CONDITIONAL = "conditional"      # established only if the call-off confirms the claimed entitlement
    UNDETERMINED = "undetermined"    # a component cannot be valued


@dataclass
class LineAssessment:
    line: InvoiceLine
    status: LineStatus
    payable_quantity: Decimal | None = None
    contract_rate_cents: int | None = None        # the rate in force (claimed-class conditional rate for CONDITIONAL lines)
    amount_cents: int | None = None               # DETERMINED: payable amount; CONDITIONAL: conditional amount
    matched: tuple[str, ...] = ()                 # qids of the report evidence the line was matched to
    findings: list[Finding] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)   # recorded, never findings (e.g. billed below the record)
    retro_difference_cents: int | None = None     # 36A: (A3 rate - rate known before it) x payable quantity, if billed before issue
    permissible_classes: frozenset[str] | None = None   # class-rated lines: the contract classes whose rate equals the billed rate
    class_constrains: bool = False                # the classes do not all give the same rate, so the billed rate narrows them


@dataclass(frozen=True)
class InvoiceValuation:
    status: TotalStatus
    services_cents: int | None
    discount_cents: int | None       # DS-900 (negative)
    adjustment_cents: int | None     # Clause 36A
    net_cents: int | None
    vat_cents: int | None
    total_cents: int | None
    reasons: tuple[str, ...] = ()    # why the total is not determined


@dataclass
class InvoiceAudit:
    invoice: DrillingInvoice
    lines: list[LineAssessment]
    findings: list[Finding]                        # invoice-level findings plus every line finding
    valuation: InvoiceValuation                    # canonical: CONDITIONAL / UNDETERMINED lines leave it open
    conditional: InvoiceValuation                  # claimed entitlement confirmed (analysis only, never payable)
    observations: list[str] = field(default_factory=list)   # facts recorded without a finding (e.g. invoice date vs period, AMB-25)


@dataclass(frozen=True)
class AuditRun:
    invoices: dict[str, InvoiceAudit]
    readings: tuple[tuple[str, str, str], ...]
    adjustment_invoices: tuple[str, ...]           # where Clause 36A puts the adjustment under the reading used
