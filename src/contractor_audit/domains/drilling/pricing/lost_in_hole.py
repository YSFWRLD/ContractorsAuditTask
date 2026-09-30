"""Lost-in-hole valuation (Clause 31, 31A, P12): replacement value less depreciation, charged as one unit.

    lih_replacement_value   SCHEDULE_2D_CONVERTED: SAR value / halalas-per-USD of the month of loss, rounded half-even
                            SCHEDULE_6_USD: the USD value as let
    lih_hours               PART_E_STATED (approved): the hours Part E states
Depreciation is 1 per cent for each complete 25 hours, not more than 50 per cent; the result is rounded (cl. 17).
"""

from decimal import Decimal

from contractor_audit.domains.drilling.contract.models import ContractTerms
from contractor_audit.domains.drilling.interpretation.models import Quantity
from contractor_audit.domains.drilling.pricing.build_up import Unpriceable
from contractor_audit.domains.drilling.pricing.models import RateSource, Step
from contractor_audit.domains.drilling.pricing.rounding import half_even_cents
from contractor_audit.domains.drilling.pricing.selection import Selection


def value_lost_tool(terms: ContractTerms, q: Quantity, selection: Selection) -> tuple[RateSource, tuple[Step, ...], int, list[tuple[str, str]]]:
    lih = terms.lost_in_hole
    source = selection.value("lih_replacement_value")
    hours_reading = selection.value("lih_hours")
    used = [("lih_replacement_value", source), ("lih_hours", hours_reading)]
    steps: list[Step] = []
    month = q.date.strftime("%Y-%m")
    if source == "SCHEDULE_2D_CONVERTED":
        halalas = lih.replacement_sar_halalas[q.service_code]
        fx = lih.fx_halalas_per_usd.get(month)
        if fx is None:
            raise Unpriceable(f"no exchange rate published for {month}")
        value = half_even_cents(Decimal(halalas) / fx * 100)
        rate = RateSource("SCHEDULE_2D", "REPLACEMENT_VALUE_SAR", value, None, None, month, 19, (f"SCHEDULE_2D:{halalas} halalas", f"SCHEDULE_6:{lih.replacement_usd_cents_as_let[q.service_code]}"))
        steps.append(Step("convert SAR", "31A / Schedule 2D", Decimal(halalas), f"1/{fx} halalas per USD", value, f"rate for {month}"))
    else:
        value = lih.replacement_usd_cents_as_let[q.service_code]
        rate = RateSource("SCHEDULE_6", "REPLACEMENT_VALUE_USD", value, None, None, None, 25, (f"SCHEDULE_6:{value}",))
    hours = int(dict(q.detail)[f"lih_hours.{hours_reading}"])
    percent = min(Decimal(hours // lih.depreciation_block_hours) * lih.depreciation_percent_per_block, lih.depreciation_cap_percent)
    out = half_even_cents(Decimal(value) * (1 - percent / 100))
    steps.append(Step("depreciation", "31 / P12", Decimal(value), str(1 - percent / 100), out, f"{hours} h -> {percent}%"))
    return rate, tuple(steps), out, used
