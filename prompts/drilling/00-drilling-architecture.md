# Drilling Phase 0 — inspection and domain architecture

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-29. Given verbatim below.

---

We are now starting the DRILLING domain.

This is a phased implementation.

IMPORTANT:
Do NOT implement Drilling contract logic yet.
Do NOT audit any Drilling records yet.
Do NOT generate Drilling findings yet.
Do NOT modify the frozen Civil Works implementation unless absolutely required for shared architecture compatibility.

For this phase, your job is ONLY:

1. inspect the repository
2. inspect the Drilling task files
3. understand the Drilling data/contract structure
4. design and create the clean Drilling folder architecture
5. add only minimal scaffolding required for that architecture
6. report back to me before doing Phase 1

STOP after the architecture/scaffolding phase.

==================================================
CURRENT REPOSITORY STATE
==================================================

Local repository folder:

ContractorsAuditTask

Civil Works is complete and frozen.

Current Civil Works state:

- 900 applications
- 7,746 lines
- 77 flagged applications
- 95 findings
- 37 corrected totals published
- 40 totals intentionally blank
- 348 tests passing
- outputs deterministic
- Phase 1/2 Civil Works artifacts frozen
- no Drilling implementation exists yet
- no combined submission exists yet
- nothing has been committed or pushed
- no GitHub repository has been created yet

Civil Works architecture and implementation should be treated as an existing working domain, NOT something to refactor casually.

Do not change Civil Works outputs or behavior during this architecture phase.

==================================================
GOAL
==================================================

Create an architecture where:

Civil Works
and
Drilling

are separate domain implementations under the same overall contractor-audit project.

The design must make it obvious which code belongs to:

- shared infrastructure
- Civil Works
- Drilling

We should be able to add more contractor domains later without making the repository messy.

==================================================
STEP 1 — INSPECT EVERYTHING FIRST
==================================================

Before creating files, inspect the entire repository.

Understand:

- current src structure
- Civil Works domain structure
- tests
- prompts
- artifacts
- outputs
- CLI / entry points
- models
- reporting
- contract parsing
- audit architecture
- shared utilities

Then inspect ALL Drilling source material supplied by the task.

Find:

- contract documents
- amendments
- schedules
- appendices
- invoice/application data
- line-item data
- supporting records
- templates
- task instructions
- any labels/evaluation data if present

Do not assume Drilling resembles Civil Works.

==================================================
STEP 2 — UNDERSTAND DRILLING BEFORE DESIGNING
==================================================

Do a first-pass inventory of the Drilling domain.

Report internally:

### Contract structure
- documents
- amendments
- effective dates
- precedence rules
- pricing/rate tables
- indexed/monthly/ranged rates
- quantity rules
- caps
- adjustments
- rebates
- retention
- duplicate rules
- timing rules
- supporting-record requirements
- exclusions
- any other special clauses

### Data structure
- number of files
- schemas
- record identifiers
- line identifiers
- dates
- quantities
- units
- prices
- totals
- supporting/reference fields
- duplicate/reused identifiers
- any cross-record dependencies

At this stage do NOT decide the final interpretation of ambiguous clauses.

Just identify them.

==================================================
STEP 3 — ARCHITECTURE
==================================================

Use a clean domain-oriented structure.

Prefer something conceptually like:

src/
  contractor_audit/
    common/
      ...
    domains/
      civil_works/
        ...
      drilling/
        __init__.py
        contract/
        ingestion/
        audit/
        reporting/

tests/
  common/
  civil_works/
  drilling/

artifacts/
  civil_works/
  drilling/

outputs/
  civil_works/
  drilling/

prompts/
  civil_works/
  drilling/

Exact subfolders should follow the existing project conventions where possible.

DO NOT restructure Civil Works merely to make the example above exact.

Adapt Drilling to the existing clean architecture.

==================================================
DRILLING DOMAIN BOUNDARY
==================================================

Drilling-specific logic must live under the Drilling domain.

Examples:

src/contractor_audit/domains/drilling/

Do not put Drilling contract rules in shared/common code.

Shared code should contain only genuinely reusable mechanics such as:

- common money helpers
- deterministic rounding
- generic file loading
- shared base models
- common output serialization
- CLI infrastructure

A rule is not "shared" merely because Civil Works and Drilling both happen to use something with a similar name.

For example:

Civil Works:
"daily limit"

and Drilling:
"daily limit"

may have completely different contract semantics.

Keep domain rules separate unless the behavior is truly generic.

==================================================
STEP 4 — CREATE ONLY MINIMAL SCAFFOLDING
==================================================

Create enough structure that Phase 1 has a clean place to go.

Examples may include:

src/contractor_audit/domains/drilling/__init__.py

src/contractor_audit/domains/drilling/contract/
src/contractor_audit/domains/drilling/ingestion/
src/contractor_audit/domains/drilling/audit/
src/contractor_audit/domains/drilling/reporting/

tests/drilling/

prompts/drilling/

artifacts/drilling/

outputs/drilling/

But do NOT fill these with speculative business logic.

Only add:

- package files
- skeletal models/interfaces if genuinely useful
- placeholder-free structure
- architecture tests if appropriate
- README/index updates necessary to explain the domain layout

Avoid empty junk files purely to make folders exist.

==================================================
STEP 5 — DRILLING PHASE PLAN
==================================================

Based on what you inspected, propose the remaining implementation phases.

Use something approximately like:

Phase 1 — source inventory + deterministic contract extraction
Phase 2 — data ingestion + structural validation
Phase 3 — deterministic audit rules
Phase 4 — ambiguous semantic/contract review if needed
Phase 5 — totals + confidence + reporting
Phase 6 — adversarial review / sensitivity analysis
Phase 7 — freeze + combined submission

BUT adapt the phases to the actual Drilling problem.

Do not blindly copy Civil Works.

If Drilling has a radically different contract structure, design phases around that.

==================================================
CRITICAL RULES
==================================================

1. DO NOT implement the full Drilling solution.

2. DO NOT start writing pricing formulas.

3. DO NOT resolve ambiguous contract clauses yet.

4. DO NOT make AI/LLM/Jev calls.

5. DO NOT generate final Drilling outputs.

6. DO NOT generate combined submission.

7. DO NOT modify Civil Works findings, artifacts or outputs.

8. DO NOT commit.

9. DO NOT push.

10. DO NOT create a GitHub repository.

11. DO NOT search other candidates' repositories or forks.

12. Everything needed to understand the task must come from:
   - the local task files
   - the contract
   - the provided data
   - the existing project architecture

==================================================
ARCHITECTURE QUALITY CHECK
==================================================

Before stopping, verify:

- Drilling has a clear domain boundary.
- Civil Works still runs unchanged.
- Existing Civil Works tests still pass.
- No circular imports.
- No Drilling logic leaked into shared code.
- No duplicate generic infrastructure was unnecessarily created.
- Future domains could be added cleanly.
- No output files were generated accidentally.
- No contract interpretation was silently hardcoded.

==================================================
REPORT BACK
==================================================

STOP after this phase.

Do not continue into Phase 1.

Report back with:

### 1. What you found

Brief overview of the Drilling contract/data shape.

### 2. Architecture created

Show the relevant tree, for example:

src/...
tests/...
artifacts/...
outputs/...
prompts/...

Only show meaningful paths.

### 3. Shared vs domain-specific

Explain what stays shared and what belongs exclusively to Drilling.

### 4. Proposed phases

Give the recommended implementation phases and what each phase will accomplish.

### 5. Risks / unusual features

List any Drilling-specific features that are likely to require extra care later.

### 6. Files created/modified

Exact list.

### 7. Regression

Report:
- tests run
- tests passing
- confirmation Civil Works outputs/artifacts were untouched

### 8. Git status

Report:
- modified files
- new files
- confirmation nothing was committed or pushed

Then STOP and wait for my next instruction.

I will review your report and give you the prompt for Phase 1.
