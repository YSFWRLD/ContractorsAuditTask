"""Synthetic audit cases, plus one full real-data audit shared by the session.

`Case` builds a small AuditData whose clean lines are billed exactly at the Phase 2 contract price,
so a test can introduce one deviation and see exactly which finding it produces.
"""

from datetime import date, timedelta
from decimal import ROUND_FLOOR, Decimal

import pytest

from contractor_audit.domains.civil_works.audit.assessment import audit
from contractor_audit.domains.civil_works.audit.context import AuditData, load_audit_data
from contractor_audit.domains.civil_works.audit.engine import run_audit
from contractor_audit.domains.civil_works.models import Application, ApplicationLine
from contractor_audit.domains.civil_works.pricing import LineContext, PricingEngine
from contractor_audit.domains.civil_works.record_quantities import extract_quantity
from contractor_audit.domains.civil_works.records import RECORD_TYPES, parse_record
from contractor_audit.shared import paths

D = Decimal
AREA, ZONE = "S-01 Platform North", "Z1 Compound"


class Case:
    def __init__(self, terms, raw):
        self.terms, self.raw = terms, raw
        self.engine = PricingEngine(terms)
        self.apps: dict[str, dict] = {}
        self.lines: list[dict] = []
        self.records: dict = {}

    def app(self, no, applied, **overrides):
        self.apps[no] = dict(application_no=no, applied=applied, **overrides)
        return self

    def line(self, app_no, code, qty, day, *, zone=ZONE, area=AREA, ground=None, night=False, record=None,
             rate=None, amount=None, unit=None):
        applied = self.apps[app_no]["applied"]
        if rate is None or amount is None:
            price = self.engine.price(LineContext(code, day, zone, area, ground, night, known_at=applied), D(qty))
            rate = price.unit_rate if rate is None else D(rate)
            amount = price.amount_cents if amount is None else amount
        n = sum(1 for l in self.lines if l["application_no"] == app_no) + 1
        self.lines.append(dict(line_ref=f"{app_no}-{n:02d}", application_no=app_no, line_no=n, work_date=day, site=area,
                               item_code=code, description=self.terms.boq[code].description, unit=unit or self.terms.boq[code].unit,
                               site_zone=zone, ground_class=ground, quantity=D(qty), rate_applied=D(rate), amount_cents=amount,
                               night_work=night, record_ref=record, source_row=0, raw={}))
        return self.lines[-1]["line_ref"]

    def record(self, ticket, body, day=None, *, area=AREA, week_beginning=None, days_on=(), unsigned=False, ground=None):
        prefix = ticket[:2]
        head = f"Week beginning: {week_beginning:%d/%m/%Y}\nDays on: " + ", ".join(f"{d:%a %d/%m}" for d in days_on) + "\n" \
            if week_beginning else f"Date: {day:%d/%m/%Y}\n"
        if ground:
            head += f"Ground: {ground}\n"
        eng = "____________________" if unsigned else "N. Basri"
        text = (f"{RECORD_TYPES[prefix]}\nTicket: {ticket}\nJob: Northern Access Road, Package 4\nArea: {area}\n{head}\n{body}\n\n"
                f"Signed (foreman): K. Doyle\nCountersigned (Engineer's representative): {eng}\n")
        self.records[ticket] = parse_record(text, f"{ticket}.txt")[0]
        return ticket

    def build(self) -> AuditData:
        lines = [ApplicationLine(**l) for l in self.lines]
        apps = []
        for no, a in self.apps.items():
            mine = [l for l in lines if l.application_no == no]
            total = a.get("total", sum(l.amount_cents for l in mine))
            ret = a.get("retention", int((D(total) * 5 / 100).to_integral_value(rounding=ROUND_FLOOR)))
            adj, rel = a.get("adjustment", 0), a.get("released", 0)
            apps.append(Application(no, a.get("contract_ref", "CW-2025-0417-CIV"), a.get("subcontractor", "Ridgeway Civil Engineering LLC"),
                                    AREA, ZONE, a.get("period_from", min(l.work_date for l in mine)), a.get("period_to", max(l.work_date for l in mine)),
                                    a["applied"], total, ret, a.get("net", total + adj - ret + rel), adj, rel, 0, {}))
        return AuditData(self.terms, self.raw, tuple(apps), tuple(lines), dict(self.records),
                         {t: extract_quantity(r) for t, r in self.records.items()})

    def run(self, **kw):
        return run_audit(self.build(), **kw)


@pytest.fixture
def case(terms, raw_extraction):
    return Case(terms, raw_extraction)


def categories(run, line_ref=None, app=None):
    return sorted(f.category for f in run.findings if (line_ref is None or f.line_ref == line_ref) and (app is None or f.invoice_id == app))


@pytest.fixture(scope="session")
def audit_data(data_root):
    return load_audit_data(data_root, paths.artifacts_dir("civil_works"))


@pytest.fixture(scope="session")
def audit_result(audit_data):
    return audit(audit_data)


def d(text):
    return date.fromisoformat(text)


def week(start: date, n: int):
    return tuple(start + timedelta(i) for i in range(n))
