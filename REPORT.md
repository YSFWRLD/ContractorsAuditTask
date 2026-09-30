# Contractor invoice audit: final report

`submission.csv` holds 2,806 rows: 900 civil works applications (`PA-*`) and 1,906 drilling invoices (`MDS-*`), in the template's order. To reproduce it, follow the README. The decisions behind it are in `DECISION_LOG.md`.

## Approach

1. **Contract extraction from the scanned PDFs.** Neither contract has a text layer. Each was transcribed once, during development, from page renders into a reviewed JSON with page citations. Every table was read twice and the two readings compared by script, with 0 discrepancies. Contradictions were recorded as ambiguities, not resolved silently. The audit reads the JSON; it never runs OCR.
2. **Deterministic, typed ingestion.** Invoices, lines and site records or Daily Drilling Reports are parsed into typed objects that keep their raw values and source positions. Nothing is re-identified from price.
3. **Evidence-first mapping.** Report wording is mapped to contract items through the contract's own vocabulary (drilling Appendix G). Each chargeable quantity is derived from the record and cites the fields it came from.
4. **Interpretation switches.** Every contested reading is a named switch with its readings, basis and grade. Working readings were chosen from the contract text, never from how well they fit the billing. The alternatives are measured, not discarded.
5. **Contract-side pricing before invoice comparison.** The payable figure for each charge is computed from the contract and the record before any invoice value is read. The invoice's figures are then compared with it.
6. **Audit against the 12 guideline checks.** Each finding has:
   - its check and category;
   - the clause relied on and the evidence chain;
   - the billed and contract values, and the monetary impact where determinable;
   - whether it changes or blocks the total.
7. **Uncertainty.** The audit is re-run with each alternative reading. Conclusions that change under an alternative carry that reading's grade.

## Results (frozen)

| | invoices | flagged | unflagged | findings | corrected totals published | blank |
|---|---|---|---|---|---|---|
| Civil works | 900 | 77 | 823 | 95 | 37 of 77 flagged | 40 |
| Drilling | 1,906 | 114 | 1,792 | 152 flagging (+ 29,160 AMB-13 queries) | 0 | 1,906 |
| **Combined** | **2,806** | **191** | **2,615** | | | 1,946 |

- **Confidence, civil works:** flagged HIGH 66 / MEDIUM 9 / LOW 2; unflagged HIGH 571 / MEDIUM 250 / LOW 2.
- **Confidence, drilling:** flagged HIGH 99 / MEDIUM 14 / LOW 1; unflagged MEDIUM 1,783 / LOW 9.
- **Most common primary categories, civil works:** unit-rate mismatch 26, duplicate record 19.
- **Most common primary categories, drilling:** quantity above the record 21, build-up factor misapplied 15, lost-in-hole valuation 8, unsupported service 7.

There are no labels, so no precision or recall is claimed, and nothing here measures correctness. The final flagged share is 6.8% (civil works 8.6%, drilling 6.0%). This is reported only as an after-the-fact sanity observation. The challenge's stated 5–8% prevalence was not used to create, remove or tune findings, and the share is not evidence that the flags are right.

## Error analysis: how this approach systematically goes wrong

**1. Missing contractual evidence.**
- *Problem:* some entitlements rest on documents that are not in the data. The drilling call-offs state each well's class and the sections nominated for performance drilling. No invoice submission date is recorded anywhere.
- *Example:* every drilling report has MW-310, a class-rated tool. So every drilling invoice has at least one charge whose rate depends on an unknown class, and no drilling corrected total can be published. MDS-00215 describes its well as Standard but bills one line at the HPHT rate. That is recorded, but not flagged: the invoice's class field is descriptive, and only the call-off decides the class.
- *Mitigation:* such charges are `EVIDENCE_NOT_PROVIDED`. They are still checked for quantity, record, duplication and arithmetic, and a rate no possible class produces is still a finding. The corrected total stays blank, and a conditional total (the contractor's claim assumed true) is kept only as analysis.
- *Cost:* on the score's amount component, flagged drilling invoices carry no corrected total.

**2. Contradictory or ambiguous provisions.**
- *Problem:* the contracts contradict themselves. Worked examples disagree with clauses, instruments cite clauses that don't exist, and "on or after" sits beside "after".
- *Example:* drilling Clause 21A's rig-up hour. The first approved reading deducted it once per BHA run. That left 3,897 DD-120 lines exactly one hour below the record. Deducting it every day, which is what the clause's own words say, reconciles them all. The reading was changed in review, with the reason recorded.
- *Mitigation:* each ambiguity is a switch, and `sensitivity.md` shows what every alternative would flag or unflag. Low-grade dependencies lower confidence rather than being hidden. Unresolved or evidence-dependent readings blank a corrected total instead of guessing it.

**3. Free-text record-to-service interpretation.**
- *Problem:* the records use site language, not item codes. Identifying which item a charge belongs to is an inference.
- *Example:* drilling Appendix G pairs some rig words with surprising codes. Its LWD rows look shifted by one. Reading them as shifted would flag 831 more invoices; the literal reading was approved. In civil works, a record of the wrong series or item is caught as `item_record_mismatch`.
- *Mitigation:*
  - one table-driven vocabulary per contract;
  - reading-dependent quantities are carried under every reading;
  - a charge the record does not evidence is `unsupported_service`, never re-identified by its price.

**4. Invoice-level timing, adjustment and duplicate edge cases.**
- *Problem:* back-dated amendments, split or misdated lines, and invoices that overlap in time.
- *Examples:*
  - The drilling Amendment No. 3 adjustment belongs "on the first invoice submitted on or after" its issue date. With no submission dates, MDS-01625 is identified by invoice date, and the finding is LOW.
  - MDS-01352-007 re-bills, under the wrong date and on a later invoice, metres already charged in full.
- *Mitigation:*
  - a ledger of report evidence already charged, in submission order, catches duplicates within and across invoices;
  - Clause 36A decides which side of an amendment a charge is priced on;
  - timing rules that depend on a submission date the data lacks are not flagged; the facts are recorded as observations.

## Confidence and unresolved amounts

- **Confidence is evidence quality, not a probability.**
  - HIGH (0.95): a direct contradiction between complete data and a settled clause.
  - MEDIUM (0.75): depends on a defensible reading, or on evidence known to be missing.
  - LOW (0.55): depends on one of the least certain readings.
- **Drilling unflagged invoices are MEDIUM at best**, because their class-rated charges cannot be verified.
- **Corrected totals are published only under a STRICT rule:** every component must be determined, and no unresolved reading or missing evidence may change it. Otherwise the field is blank (never 0), with the reason in the domain's audit CSV.
- **Conditional drilling totals are analysis only.** They take each call-off-dependent charge at the contractor's claimed class. They equal the billed total on every unflagged invoice except two (MDS-00215 and MDS-01445, the descriptive-class queries). That is calibration evidence, not entitlement, and they never enter `submission.csv`.

## AI assistance

AI assistance (Claude Code) was used throughout: contract transcription from page renders, code, tests and documents. Every prompt is versioned in `prompts/`, with a note per phase on how AI was used. No language model runs at audit time; the pipeline is deterministic Python.
