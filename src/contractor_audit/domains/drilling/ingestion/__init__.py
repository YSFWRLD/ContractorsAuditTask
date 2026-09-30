"""Raw drilling files -> typed, traceable records. No contract knowledge.

`models` (typed records), `values` (strict value parsers), `invoices` (the two CSVs), `reports` (Daily
Drilling Reports, Parts A-E and signatures), `loaders.load_dataset`, `indexes` (duplicate-safe lookups),
`timelines` (wells and BHA runs) and `validation` (structural observations, never findings).

Invoices and lines keep Decimal rates, integer-cent money, parsed dates and the raw strings. Reports keep
the rig's own words exactly as written: turning "mud motor" or "directional hands" into a service code is
contract interpretation (Appendix G) and belongs in a later phase, never here.
"""
