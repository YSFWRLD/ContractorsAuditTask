# Phase 0 — repository inspection + architecture

Tool: Claude Code (Claude Opus 5.5). Date: 2026-09-29. Given verbatim below.

---

We are starting a new local implementation of this contractor auditing task.

Repository folder:

ContractorsAuditTask

We will work locally first.

There is currently NO GitHub repository for my solution.

Do NOT:
- create a GitHub repository
- commit
- push
- open a PR
- modify the original task data
- begin implementing Civil Works audit rules yet

This project will eventually support at least:

1. Civil Works — implement this first
2. Drilling — implement later

The architecture must therefore be clean enough that adding Drilling later does NOT require rewriting the Civil Works implementation or the shared core.

However, do NOT over-engineer for hypothetical future features.

==================================================
WORKFLOW
==================================================

We are going to build this in phases.

For every phase:

1. inspect first
2. implement only that phase
3. run relevant checks/tests
4. report exactly what you found and changed
5. STOP

Do not continue to the next phase until I explicitly tell you to.

For this prompt, perform ONLY:

PHASE 0 — REPOSITORY INSPECTION + ARCHITECTURE

Do NOT start Phase 1.

==================================================
PHASE 0 — STEP 1: INSPECT THE ENTIRE TASK
==================================================

Read the local repository carefully.

Identify:

- task instructions
- README files
- Civil Works source files
- Civil Works contracts / BOQs / invoices / reports / spreadsheets / JSON / CSV / PDFs / text files
- Drilling source files
- templates
- expected output format
- examples
- labels / ground truth if any
- evaluation instructions
- scoring rules
- required deliverables
- important constraints
- ambiguity / uncertainty guidance
- any AI usage requirements
- any source files that must remain unchanged

Do not assume that Civil Works works like Drilling.

Do not assume this task works like a previous project.

Use the actual files in this repository as the source of truth.

If PDFs or spreadsheets exist, inspect them using appropriate local tools.

Do not use the internet unless the task itself explicitly requires outside information.

==================================================
STEP 2: UNDERSTAND THE TWO DOMAINS
==================================================

Before creating code, determine what belongs to:

SHARED CORE

versus:

CIVIL WORKS SPECIFIC

versus eventually:

DRILLING SPECIFIC

The core principle should be:

raw task files
    ↓
domain-specific parsing / interpretation
    ↓
canonical internal models
    ↓
domain-specific audit rules
    ↓
shared findings / result representation
    ↓
domain-specific outputs
    ↓
combined submission/report if required

Do not put Civil Works business rules inside shared modules.

Shared code should contain only genuinely reusable concepts such as:

- common data models
- money / numeric utilities if applicable
- generic finding/result structures
- shared validation
- file loading utilities where genuinely common
- output/submission helpers if both domains can use them
- common confidence / uncertainty representation if appropriate
- reusable CLI/application wiring where appropriate

Civil Works should own:

- its document parsing
- its terminology
- its matching logic
- its contract interpretation
- its audit rules
- its pricing/calculation logic
- its Civil Works-specific validations
- its evidence/provenance
- its tests

Later, Drilling should be addable as another domain module instead of adding conditionals throughout Civil Works.

BAD:

if contractor_type == "civil":
    ...
elif contractor_type == "drilling":
    ...

spread across many shared files.

GOOD:

shared application/core
    +
civil_works module
    +
future drilling module

==================================================
STEP 3: CREATE THE PROJECT ARCHITECTURE
==================================================

After understanding the task, create a clean project structure.

Adapt the exact names if the repository/task strongly suggests better names, but aim for something conceptually like:

ContractorsAuditTask/
│
├── README.md
├── <original task files/directories — untouched>
│
├── src/
│   └── contractor_audit/
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── shared/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── findings.py
│       │   ├── validation.py
│       │   └── ...
│       │
│       └── domains/
│           ├── __init__.py
│           │
│           └── civil_works/
│               ├── __init__.py
│               ├── models.py
│               ├── contract.py
│               ├── parser.py
│               ├── matcher.py
│               ├── rules.py
│               ├── audit.py
│               └── pipeline.py
│
├── tests/
│   ├── shared/
│   └── civil_works/
│
├── artifacts/
│   └── civil_works/
│
├── outputs/
│   └── civil_works/
│
└── prompts/
    └── civil_works/

This is an example, NOT a requirement to blindly create every file.

Only create files/directories that make sense after inspecting the actual task.

==================================================
IMPORTANT ARCHITECTURE RULE
==================================================

Do NOT create a full fake `drilling/` implementation.

We have not studied or implemented Drilling yet.

The architecture should simply make this future addition natural:

src/contractor_audit/domains/drilling/

Later Drilling should be able to provide its own:

- parser
- models where needed
- matching
- rules
- audit
- pipeline
- tests
- artifacts
- outputs

without modifying Civil Works business logic.

If a tiny interface/protocol/shared model is genuinely needed to establish this boundary, create it.

Do not create speculative abstractions just because Drilling might need them later.

==================================================
STEP 4: PRESERVE RAW TASK DATA
==================================================

Treat the original task data as immutable source material.

Do not:

- rewrite contracts
- normalize source spreadsheets in place
- edit invoice data
- rename source files unless absolutely required
- delete files
- overwrite templates

Derived data must go under something like:

artifacts/civil_works/

Generated final results must go under:

outputs/civil_works/

Tests must use fixtures/copies where mutation is necessary.

==================================================
STEP 5: MINIMAL APPLICATION BOUNDARIES
==================================================

Establish a clean direction of dependencies.

Prefer:

CLI / application
        ↓
Civil Works pipeline
        ↓
Civil Works parser / matcher / rules
        ↓
shared models/utilities

NOT:

shared modules importing Civil Works.

The shared layer must not know Civil Works-specific terminology.

Avoid circular dependencies.

==================================================
STEP 6: TEST ARCHITECTURE
==================================================

Set up the test layout now.

Do NOT implement full audit tests yet.

At this stage, only add minimal architectural/smoke tests if useful, for example:

- package imports cleanly
- Civil Works pipeline object/module can be loaded
- raw source paths can be located
- output/artifact directories are separate from raw data

Do not create fake tests that test nothing useful just to increase test count.

==================================================
STEP 7: PROJECT CONFIGURATION
==================================================

Inspect the repository before deciding whether it should use:

- requirements.txt
- pyproject.toml
- an existing dependency system

Do not add unnecessary libraries.

If dependencies are already defined, preserve the existing approach unless there is a clear reason not to.

Do not install or add AI/LLM frameworks during Phase 0.

We have not decided that they are necessary.

==================================================
STEP 8: DOCUMENT THE ARCHITECTURE
==================================================

Add a short architecture section/document explaining:

1. what is shared
2. what belongs to Civil Works
3. where raw task data lives
4. where derived artifacts live
5. where final outputs live
6. how Drilling can be added later
7. dependency direction

Keep it concise.

Do not write pages of speculative architecture documentation.

==================================================
STEP 9: DO NOT IMPLEMENT BUSINESS LOGIC
==================================================

This is critical.

During Phase 0, do NOT yet implement:

- Civil Works audit findings
- pricing calculations
- invoice corrections
- contract interpretation rules
- semantic matching
- fuzzy matching
- LLM matching
- anomaly detection
- scoring
- final submission generation

We first need to understand the data and architecture.

Phase 1 will handle actual Civil Works understanding/normalization after I review your report.

==================================================
PHASE 0 FINAL REPORT
==================================================

When finished, STOP.

Do not continue to Phase 1.

Report back using this structure:

# Phase 0 Complete

## 1. Task structure found

List the important source files/directories.

Separate:

- Civil Works
- Drilling
- shared/task-wide files

## 2. Civil Works data

Explain briefly:

- what files exist
- formats
- approximate sizes / row counts / page counts where useful
- what appears to be the contract/source of truth
- what appears to be the billed/work data
- what output the task expects

Do NOT perform the full audit yet.

## 3. Drilling data

Briefly explain what exists only so we know the architecture can accommodate it.

Do NOT analyze or implement Drilling yet.

## 4. Requirements discovered

List the actual requirements from the task.

Distinguish required vs inferred.

## 5. Architecture created

Show the resulting directory tree.

Explain each important module in ONE sentence.

## 6. Shared vs Civil Works boundary

Clearly state what is in shared code and what remains Civil Works-specific.

## 7. Future Drilling integration

Explain exactly where a future Drilling implementation would plug in.

Confirm whether adding it should require changes to Civil Works.

## 8. Files created or modified

List every file.

## 9. Tests/checks run

Report results.

## 10. Questions / ambiguities

List anything in the task that genuinely needs a decision before implementation.

Do not invent questions when the source is clear.

## 11. Recommended Phase 1

Based on the actual files you inspected, tell me what Phase 1 should accomplish.

Do NOT implement it.

==================================================
FINAL CONSTRAINTS
==================================================

READ/CREATE LOCALLY ONLY.

Do not:

- commit
- push
- create GitHub repo
- create PR
- begin Drilling
- begin Civil Works business rules
- change raw task data
- move to Phase 1

Finish Phase 0, report, and STOP.
