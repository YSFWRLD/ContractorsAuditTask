"""Civil works audit rules, one module per guideline check family.

Quantity-stage rules (run in QUANTITY_RULES order) read the application data and may cap a
line's payable quantity. Valuation-stage rules compare billed figures with the Phase 2 pricing
of the billed and payable quantities. No rule computes a price itself.
"""
