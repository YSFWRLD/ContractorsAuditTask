"""A small synthetic drilling world for audit tests: report texts through the real parser, invoices built by hand.

`World.correct_lines` writes the invoice a careful contractor would send for some reports: every quantity the
reports evidence, at the contract rate (the claimed class for class-rated services), so a test can mutate one
thing and see exactly one kind of finding.
"""

import json
from dataclasses import replace
from datetime import date
from decimal import Decimal

from contractor_audit.domains.drilling.audit.bundle import build_bundle
from contractor_audit.domains.drilling.audit.dependencies import Measured
from contractor_audit.domains.drilling.audit.engine import audit
from contractor_audit.domains.drilling.audit.invoices import discount, vat
from contractor_audit.domains.drilling.audit.policy import build_policy
from contractor_audit.domains.drilling.audit.results import finalize
from contractor_audit.domains.drilling.ingestion.models import DrillingDataset, DrillingInvoice, InvoiceLine, SourceRef
from contractor_audit.domains.drilling.ingestion.reports import parse_report_text
from contractor_audit.domains.drilling.interpretation.engine import interpret
from contractor_audit.domains.drilling.pricing.models import PricingStatus
from contractor_audit.domains.drilling.pricing.rounding import half_even_cents
from contractor_audit.domains.drilling.pricing.selection import APPROVED_FILENAME, build_selection
from contractor_audit.shared import paths

CONTRACT, CONTRACTOR = "DDS-2025-118", "Meridian Downhole Services Ltd"
TOOLS = ("MWD collar", "drilling jars", "mud motor", "real-time link", "rotary steerable", "float sub")
CREW = "2 directional hands, 1 night man, 2 MWD engineers, 1 performance engineer"


def d(text: str) -> date:
    return date.fromisoformat(text)


def fmt(day: date) -> str:
    return day.strftime("%d-%b-%Y")


def report(well: str, day: date, *, status="Operating", section='12-1/4"', start=1000, end=1200, circ=15, run=1, first=None, last=None,
           tools=TOOLS, crew=CREW, gyro=0, pressure=0, wiper=0, back=0, cleanout=0, logged=0, reamed=0, source=False,
           extra_parts="", signed=True):
    number = well.split("-")[-1]
    rid = f"DDR-{number}-{day:%Y%m%d}"
    sign = ("Signed (Company Representative): P. Lindqvist\nSigned (lead directional driller): M. Farouk" if signed
            else "Signed (Company Representative): ____\nSigned (lead directional driller): ____")
    text = f"""DAILY DRILLING REPORT
Report: {rid}
Contract: {CONTRACT}
Well: {well}
Rig: NG-Rig 90
Date: {fmt(day)}

PART A — OPERATIONS SUMMARY
Hole section: {section}
Status: {status}
Depth start (m MD): {start}
Depth end (m MD): {end}
Circulating hours: {circ}
BHA run: {run}
In the hole: {", ".join(tools)}
Crew on tour: {crew}
Gyro surveys: {gyro}
Pressure points: {pressure}
Wiper trips: {wiper}
Back-reaming hours: {back}
Clean-out runs: {cleanout}

PART B — BHA RUN RECORD
Run: {run}
Run first day: {fmt(first or day)}
Run last day: {fmt(last or day)}
Tools in run: {", ".join(tools)}
Run circulating hours: {circ}
Metres logged: {logged}
Metres reamed: {reamed}
Radioactive source carried: {"Yes" if source else "No"}
{extra_parts}
{sign}
"""
    return parse_report_text(text, f"drilling_services/records/DDR_{well}_{day:%Y%m%d}.txt")


def line(invoice_no: str, n: int, day: date | None, well: str, code: str, qty, rate, report_ref: str | None, *, terms, amount=None,
         unit=None, description=None, status="Operating", section='12-1/4"', depth_from=None, depth_to=None) -> InvoiceLine:
    s = terms.services.get(code)
    qty, rate = (None if qty is None else Decimal(qty)), (None if rate is None else Decimal(rate))
    amount = amount if amount is not None or qty is None or rate is None else half_even_cents(qty * rate * 100)
    ref = f"{invoice_no}-{n:03d}"
    return InvoiceLine(ref, invoice_no, n, day, well, code, description if description is not None else (s.description if s else "Discount"),
                       unit or (s.unit if s else "invoice"), section, status, depth_from, depth_to, qty, rate, amount, report_ref, (),
                       SourceRef("drilling_services/invoices/invoice_lines.csv", n, ref))


def invoice(no: str, well: str, start: date, end: date, dated: date | None, lines, *, terms, cls="Standard", ref=CONTRACT, contractor=CONTRACTOR,
            adjustment=0, net=None, vat_cents=None, total=None, with_discount=True) -> tuple[DrillingInvoice, list[InvoiceLine]]:
    lines = list(lines)
    services = sum(l.amount_cents for l in lines if l.service_code != "DS-900")
    if with_discount and discount(terms, services) and not any(l.service_code == "DS-900" for l in lines):
        lines.append(line(no, len(lines) + 1, None, well, "DS-900", 1, Decimal(discount(terms, services)) / 100, None, terms=terms, section=None, status=None))
    net = sum(l.amount_cents for l in lines) if net is None else net
    vat_cents = vat(terms, net) if vat_cents is None else vat_cents
    total = net + vat_cents if total is None else total
    inv = DrillingInvoice(no, ref, contractor, well, "NG-Rig 90", "Test", cls, start, end, dated, net, vat_cents, total, adjustment, (),
                          SourceRef("drilling_services/invoices/invoices.csv", 1, no))
    return inv, lines


class World:
    def __init__(self, terms, ambiguities, switches, approved, reports):
        self.terms, self.reports, self.switches = terms, list(reports), switches
        self.result = interpret(self.reports, terms, ambiguities)
        self.selection = build_selection(switches, approved)
        self.bundle = build_bundle(self.result, terms, switches, self.selection)
        raw = json.loads((paths.artifacts_dir("drilling") / APPROVED_FILENAME).read_text(encoding="utf-8"))
        self.policy = build_policy(self.selection, raw, switches)

    def audit(self, *invoices, policy=None):
        invs = [i for i, _ in invoices]
        lines = [l for _, ls in invoices for l in ls]
        run = audit(DrillingDataset(tuple(invs), tuple(lines), tuple(self.reports), ()), self.terms, self.bundle, policy or self.policy)
        return {o.result.invoice_id: o for o in finalize(run, Measured())}

    def priced(self, report_id: str, code: str):
        return self.bundle.at_report(report_id, code)

    def correct_lines(self, invoice_no: str, report_ids, dated: date, claimed="Standard", skip=()) -> list[InvoiceLine]:
        """Every evidenced charge of these reports at the contract rate (claimed class / nomination for conditional ones)."""
        out = []
        retro_issue = max(i.issued for i in self.terms.instruments if i.retroactive)
        for rid in report_ids:
            seen = set()
            for p in sorted((p for p in self.bundle.canonical if rid in p.report_ids), key=lambda p: p.qid):
                if p.status is PricingStatus.NOT_CHARGEABLE or p.service_code in skip or p.qid in seen:
                    continue
                seen.add(p.qid)
                q = self.bundle.quantities[p.qid]
                ref = p
                if p.status is PricingStatus.EVIDENCE_NOT_PROVIDED and p.service_code in self.bundle.class_services:
                    ref = self.bundle.conditional(p.qid)[claimed]
                rate = ref.parts[0].rate_cents
                if ref.rate_without_retroactive_cents is not None and dated < retro_issue:
                    rate = ref.rate_without_retroactive_cents
                detail = dict(q.detail)
                out.append(line(invoice_no, len(out) + 1, q.date, q.well, p.service_code, p.chargeable_quantity, Decimal(rate) / 100, rid,
                                terms=self.terms, status=q.day_status or "Operating", section=q.hole_section,
                                depth_from=int(detail["from_m"]) if "from_m" in detail else None,
                                depth_to=int(detail["to_m"]) if "to_m" in detail else None))
        return out


def with_line(lines, ref, **changes):
    """The lines with one line replaced; amount follows quantity x rate unless given."""
    out = []
    for l in lines:
        if l.line_ref == ref:
            l = replace(l, **changes)
            if "amount_cents" not in changes and l.quantity is not None and l.unit_rate is not None:
                l = replace(l, amount_cents=half_even_cents(l.quantity * l.unit_rate * 100))
        out.append(l)
    return out


def find(lines, code, n=0):
    return [l for l in lines if l.service_code == code][n]


def categories(outcome) -> set[str]:
    from contractor_audit.domains.drilling.audit.categories import flags
    return {f.category for f in outcome.findings if flags(f.category)}
