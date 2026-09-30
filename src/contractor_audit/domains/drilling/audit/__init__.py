"""The twelve guideline checks for drilling invoices.

Joins ingestion (what was billed and what the Daily Drilling Reports record) with contract (what is
payable) and emits shared `Finding`s and `InvoiceResult`s. Rules live here; rates and prices come
from `contract`, never recomputed in a rule.
"""
