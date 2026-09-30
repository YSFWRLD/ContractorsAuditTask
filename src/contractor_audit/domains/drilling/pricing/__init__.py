"""Evidence-backed quantities -> contract prices, under an explicit selection of readings. No invoice is read.

`selection` (which reading of each switch, and whether it is approved; pricing refuses to start when a
required switch has no value), `models` (priced quantities with a step-by-step trace), `rounding`,
`rates` (the rate statement in force on the service date), `build_up` (Clause 17A/18 and the principal
discount), `quantity_rules` (chargeability, the 21A rig-up hour, the 6-hour minimum, daily limits),
`tiers` (PD-210 Contract-Year volume tiers), `lost_in_hole` (Clause 31/31A valuation) and `engine.price`.

A result is canonical only when every switch it used is approved or resolved by the contract text.
Invoice-level items (the Clause 38 discount, VAT, the 36A adjustment) need invoice assembly and are not
priced here.
"""
