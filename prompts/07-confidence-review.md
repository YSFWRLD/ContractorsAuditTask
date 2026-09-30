Do one final focused review of CONFIDENCE ONLY.

Do not change audit detection, flags, expected totals, categories, pricing, Civil indexation, AMB-13, well-class consistency, or submission-date logic.

The targeted patch caused 554 previously MEDIUM unflagged Drilling invoices to become LOW, mainly because the AMB-10 `volume_tier_scope` alternative would flag them.

Before we accept that large confidence change, trace the semantics and provenance of AMB-10's LOW grade.

Answer these questions:

1. Where exactly is AMB-10 assigned LOW?
   - file;
   - code/data field;
   - decision/prompt that introduced it.

2. What does that LOW grade mean?
   - low confidence in the selected `PER_WELL` reading?
   - low plausibility of the `CONTRACT_WIDE` alternative?
   - generic ambiguity severity?
   - something else?

3. Re-read the contract basis for AMB-10.
   Specifically assess the phrase:
   "metres already drilled on the well in the Contract Year"

   Determine, from contract text only, how strong `PER_WELL` is relative to `CONTRACT_WIDE`.

4. Explain why an unflagged invoice that would become flagged only under the CONTRACT_WIDE alternative should receive:
   - LOW (0.55),
   - MEDIUM (0.75),
   - or another existing band.

   Do not invent a new numerical confidence value.

5. Quantify the effect:
   - how many of the 554 downgraded invoices are LOW solely because of AMB-10;
   - how many also depend on another LOW reading;
   - list all LOW-grade switches causing unflagged invoice downgrades.

6. Check the confidence model semantically:
   A weak alternative should not automatically make the chosen result weak merely because it produces different flags.
   Conversely, if the selected reading itself genuinely has LOW evidential confidence, the downgrade is justified.

7. Compare this to the official scoring requirement:
   confidence is evaluated against actual precision.
   We have no labels, so do not claim statistical calibration.

Do NOT make changes yet.

Return:

# FINAL CONFIDENCE REVIEW

## AMB-10 GRADE PROVENANCE
## CONTRACTUAL STRENGTH
## WHAT LOW MEANS
## 554-INVOICE BREAKDOWN
## OTHER LOW SWITCHES
## RECOMMENDATION

End with exactly one recommendation:

- KEEP CURRENT CONFIDENCE OUTPUT
- CHANGE AMB-10 GRADE WITH CONTRACTUAL JUSTIFICATION
- CHANGE CONFIDENCE PROPAGATION LOGIC

If recommending a change, explain the smallest defensible change.

Do not commit or push.
