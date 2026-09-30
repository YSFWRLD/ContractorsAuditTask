"""Civil works audit layer: compares what was billed with what the contract supports.

Pricing (`pricing.py`, `valuation.py`) says what should be paid; the audit compares that with
the application and explains every difference. No audit condition lives in the pricing code.
"""
