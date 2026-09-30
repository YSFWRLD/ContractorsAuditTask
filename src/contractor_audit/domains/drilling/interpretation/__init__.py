"""Report evidence -> contract service candidates -> evidence-backed quantities. No pricing, no findings.

`models` (typed results), `provenance` (field references back to the report), `switches` (every open
contract reading as a named switch), `service_mapping` (report words -> Appendix G candidates),
`ambiguity` (context resolution and alternative readings), `quantities` (daily evidence),
`run_quantities` (once per BHA run), `well_quantities` (once per well), `lost_in_hole` (Part E) and
`engine.interpret` (the whole pass over the reports).

Only reports and the contract model are read here. Invoices, billed codes, rates and amounts never are:
`interpret` does not accept them.
"""
