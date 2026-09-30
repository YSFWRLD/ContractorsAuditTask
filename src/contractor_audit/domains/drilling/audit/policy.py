"""The readings the audit runs under, and the confidence grade of every reading a conclusion can depend on.

Pricing readings come from the Phase 4 selection: approved by the user, or resolved by the contract text.
The five switches the Phase 1 register left for the audit (AMB-12, 14, 15, 23, 25) were run at a WORKING reading
chosen from the contract text (the Phase 1 preference, or the policy the frozen civil works audit applies to the
same question), and were then decided by the user (prompts/drilling/08-audit-review-decisions.md): AMB-12, 14,
15 and 23 approved at that reading; AMB-25 decided as EVIDENCE_NOT_PROVIDED (the submission date is not in the
data, and the invoice date does not prove it). A reading without an approval falls back to the working reading
and is labelled unapproved. Every alternative is still measured (`audit.dependencies`). None was chosen by
comparing with billed amounts.

Grades describe evidence quality, never how well a reading fits the billing:
    contract text resolves it                          HIGH
    approved pricing reading                           the confidence recorded when it was recommended
    AMB-13 (the call-off is not in the data)           MEDIUM: the absence is certain, the class is not
    audit-phase reading                                the grade below
An approval records a decision; it adds no evidence, so it never raises a grade (AMB-05 and AMB-12 stay LOW). A grade
changes only on contractual grounds, recorded with its history (AMB-10: LOW to MEDIUM, `phase4_recommendations.json`).
"""

import json
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from contractor_audit.domains.drilling.contract.models import Ambiguity
from contractor_audit.domains.drilling.interpretation.switches import Switch
from contractor_audit.domains.drilling.pricing.selection import Selection, Source
from contractor_audit.shared.findings import ConfidenceBand, Dependency

RECOMMENDATIONS_FILENAME = "phase4_recommendations.json"
AUDIT_SWITCHES = ("backdated_adjustment", "record_signatories", "missing_record_consequence", "submission_date", "report_vocabulary")


@dataclass(frozen=True)
class WorkingReading:
    switch: str
    ambiguity: str
    value: str
    band: ConfidenceBand
    basis: str


WORKING_READINGS: dict[str, WorkingReading] = {w.switch: w for w in (
    WorkingReading("record_signatories", "AMB-14", "DDR_SIGNATURES_COVER_PARTS", ConfidenceBand.MEDIUM,
                   "Phase 1 preferred reading A: Schedule 5 says Parts B-E are parts of the one Daily Drilling Report and there are no "
                   "separate documents; a Schedule prevails over a Part (cl. 2); Appendices D-F are illustrative forms."),
    WorkingReading("report_vocabulary", "AMB-15", "RIG_WORDS_VALID", ConfidenceBand.MEDIUM,
                   "Phase 1 preferred reading A: 19A says the report is written in the ordinary words of the rig and does not carry "
                   "service codes; Appendix G exists to map those words."),
    WorkingReading("missing_record_consequence", "AMB-23", "PART_REJECT", ConfidenceBand.MEDIUM,
                   "Clause 37: a charge 'is not payable until' its record has been delivered, so it is not payable on this invoice; "
                   "the same policy the frozen civil works audit applies (missing_record_consequence = not payable in this application)."),
    WorkingReading("submission_date", "AMB-25", "UNKNOWN_QUERY", ConfidenceBand.MEDIUM,
                   "The data carries an invoice date only (NP-06), and the invoice date does not prove when an invoice was submitted: "
                   "the submission date is EVIDENCE_NOT_PROVIDED. Clause 33 timing is not judged from the invoice date; the invoice-date "
                   "facts are kept as observations."),
    WorkingReading("backdated_adjustment", "AMB-12", "CONTRACT_WIDE_ON_OR_AFTER", ConfidenceBand.LOW,
                   "Clause 36A's own words: 'a single adjustment on the first invoice submitted on or after the date of issue, and on "
                   "no other'. Amendment No. 3 says 'after'; Clause 32 (per-well invoices) supports one adjustment per well. The text "
                   "does not settle it (LOW, as the same question is graded in civil works)."),
)}

_BANDS = {"HIGH": ConfidenceBand.HIGH, "MEDIUM": ConfidenceBand.MEDIUM, "LOW": ConfidenceBand.LOW}

# The submission-date proxy (AMB-25). The data carries no submission date. The invoice date is used for one purpose
# only: a deterministic processing order (ties by invoice number), which decides which of two charges of the same
# evidence is reported as the repeat, and which invoice Clause 36A's "first invoice submitted on or after" and "an
# invoice submitted before the date of issue" point at. It is never presented as the submission date, and no Clause 33
# timing finding is raised from it. A conclusion whose correctness depends on the actual submission order carries the
# AMB-25 dependency below; conclusions resting on work dates or the invoice's own period do not.
SUBMISSION_PROXY = ("invoice-date order (processing proxy; the submission date is not in the data, AMB-25)")


def processing_key(invoice) -> tuple:
    """Deterministic processing order: invoice date, then invoice number. A proxy, not the submission order."""
    return (invoice.invoice_date or date.max, invoice.invoice_no)


def submission_order_dependency(effect: str = "finding_absent") -> Dependency:
    """AMB-25: under another (unknown) submission order this conclusion may move to another invoice or disappear."""
    return Dependency("submission_date", SUBMISSION_PROXY, "the actual submission order (not in the data)", effect,
                      WORKING_READINGS["submission_date"].band)


@dataclass(frozen=True)
class AuditReading:
    switch: str
    value: str
    approved: bool


@dataclass(frozen=True)
class AuditPolicy:
    selection: Selection                  # pricing and quantity readings (approved / contract text)
    audit: dict[str, AuditReading]        # the audit-phase readings

    def value(self, switch: str) -> str:
        if switch in self.audit:
            return self.audit[switch].value
        return self.selection.value(switch)

    def with_audit(self, switch: str, value: str) -> "AuditPolicy":
        return replace(self, audit={**self.audit, switch: AuditReading(switch, value, False)})

    def with_selection(self, selection: Selection) -> "AuditPolicy":
        return replace(self, selection=selection)

    @property
    def awaiting_approval(self) -> tuple[str, ...]:
        return tuple(n for n in AUDIT_SWITCHES if not self.audit[n].approved)

    def readings(self) -> list[tuple[str, str, str]]:
        """(switch, value, source) for every reading the audit used."""
        out = [(n, c.value, c.source.value) for n, c in sorted(self.selection.choices.items())]
        out += [(n, r.value, "APPROVED" if r.approved else "WORKING (not approved)") for n, r in sorted(self.audit.items())]
        return out


def build_policy(selection: Selection, approved_raw: dict, switches: dict[str, Switch]) -> AuditPolicy:
    """Approved audit-phase readings where the approvals file has them; the working reading otherwise."""
    approved = {a["switch"]: a["value"] for a in approved_raw.get("approvals", []) if a["switch"] in AUDIT_SWITCHES}
    audit = {}
    for name in AUDIT_SWITCHES:
        value = approved.get(name, WORKING_READINGS[name].value)
        if value not in switches[name].values:
            raise ValueError(f"{value!r} is not a reading of {name}")
        audit[name] = AuditReading(name, value, name in approved)
    return AuditPolicy(selection, audit)


def load_recommendations(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def reading_grades(policy: AuditPolicy, switches: dict[str, Switch], ambiguities: dict[str, Ambiguity],
                   recommendations: dict) -> dict[str, ConfidenceBand]:
    """The grade of each switch's current reading (see the module docstring)."""
    recommended = {r["switch"]: r["confidence"] for r in recommendations.get("recommendations", [])}
    grades = {}
    for name, sw in switches.items():
        choice = policy.selection.choices.get(name)
        if name == "calloff_evidence":
            grades[name] = ConfidenceBand.MEDIUM
        elif name in policy.audit:
            grades[name] = WORKING_READINGS[name].band
        elif choice is not None and choice.source is Source.CONTRACT_TEXT:
            grades[name] = ConfidenceBand.HIGH
        else:
            grades[name] = _BANDS.get(recommended.get(name) or ambiguities[sw.ambiguity_id].confidence or "", ConfidenceBand.MEDIUM)
    return grades
