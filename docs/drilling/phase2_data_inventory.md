# Drilling Phase 2: data inventory

This records the structure actually found in `invoice-auditing-level-2/drilling_services/`. No field below is inferred. The counts come from the files, and are reproduced by `tests/drilling` and `artifacts/drilling/phase2_structural_validation.json`.

## Files

| path | kind | count | bytes |
|---|---|---|---|
| `contract/DDS-2025-118.pdf` | contract scan (Phase 1) | 42 pages | 8,146,739 |
| `guidelines/INVOICE_AUDIT_GUIDELINES.md` | audit checks (not data) | 1 | 2,099 |
| `invoices/invoices.csv` | invoice headers | 1,906 rows | 317,378 |
| `invoices/invoice_lines.csv` | invoice lines | 91,244 rows | 13,607,419 |
| `records/DDR_<well>_<yyyymmdd>.txt` | Daily Drilling Reports | 8,151 files | 850–1,280 each |

There are no other files and no other extensions: every file under `records/` is `.txt`.

**Encoding:**
- every file is UTF-8 without a BOM, with CRLF line endings and a final newline;
- the CSVs are pure ASCII;
- the reports contain one non-ASCII character, the em dash (U+2014) in `PART X — TITLE`.

The sha256 of each file, and the report tree hash, are in `artifacts/drilling/source_manifest.json`.

## invoices.csv (14 columns, 1,906 rows, no blanks, no ragged rows)

| column | shape | notes |
|---|---|---|
| `invoice_no` | `MDS-00001` … `MDS-01906` | unique, contiguous, in file order |
| `contract_ref` | `AAA-9999-999` | `DDS-2025-118` ×1,903; `DSS-2025-118` ×2 (MDS-00672, MDS-00988); `DDS-2025-181` ×1 (MDS-01799) |
| `contractor` | text | `Meridian Downhole Services Ltd` on every row |
| `well_name` | `NGP-XX-999` | 214 wells; prefixes BD, HA, QA, WS |
| `rig` | `NG-Rig 99` | 13 rigs; one rig per well |
| `field` | text | Qarn Alam North 521, Burqan Deep 502, Harran 492, Wadi Sahm 391; one per well |
| `well_class` | text | Standard 1,099, Extended Reach 505, HPHT 302. This is the contractor's statement; one value per well. |
| `period_start`, `period_end`, `invoice_date` | `DD-Mon-YYYY` | English month abbreviations |
| `net_amount`, `vat_amount`, `invoice_total` | `-?9+.99` | exactly two decimals; no thousands separator; no currency column |
| `adjustment` | `0.00` | 0.00 on every row |

## invoice_lines.csv (16 columns, 91,244 rows, no ragged rows)

| column | shape | blanks | notes |
|---|---|---|---|
| `line_ref` | `MDS-00001-001` | 0 | unique; always `<invoice_no>-<line_no:03>` |
| `invoice_no` | `MDS-99999` | 0 | every value exists in invoices.csv; every invoice has lines (13–93) |
| `line_no` | integer | 0 | 1..n within each invoice |
| `service_date` | `DD-Mon-YYYY` | 63 | blank only on DS-900 lines |
| `well_name` | `NGP-XX-999` | 0 | always equals the invoice's well |
| `service_code` | `AA-999` | 0 | 39 codes as printed (38 Schedule 1 codes + DS-900); one description and unit per code |
| `description`, `unit` | text | 0 | 11 units: day, person-day, metre, hour, run, trip, well, survey, point, **invoice** (DS-900 only), each |
| `hole_section` | `26"`, `17-1/2"`, `12-1/4"`, `8-1/2"`, `6"` | 63 | CSV-quoted because of `"`; blank only on DS-900 |
| `day_status` | `Operating` / `Standby` | 63 | blank only on DS-900 |
| `depth_from_m`, `depth_to_m` | integer | 88,854 | present on the 2,390 PD-210 lines only, always as a pair |
| `quantity` | integer | 0 | every quantity is a whole number |
| `unit_rate` | `-?9+.99` | 0 | negative only on DS-900 |
| `amount` | `-?9+.99` | 0 | negative only on DS-900 (63 lines) |
| `report_ref` | `DDR-999-99999999` | 63 | blank only on DS-900; the join into `records/` through the report's `Report:` field |

Service dates run from 2025-01-01 to 2027-01-23.

## Daily Drilling Reports (8,151 files)

- **File name:** `DDR_<well>_<yyyymmdd>.txt`. It always agrees with the report's Well and Date, but the join key is the **`Report:` field**, e.g. `DDR-011-20260225`, which is `DDR-<well number>-<yyyymmdd>`.
- **Uniqueness:** Report ids are unique, and so are (well, date) pairs.
- **Dates:** 2025-01-01 to 2026-11-27.

### Layout

```
DAILY DRILLING REPORT
Report: … / Contract: … / Well: … / Rig: … / Date: DD-Mon-YYYY        header (every report)
PART A — OPERATIONS SUMMARY   13 fields                               every report
PART B — BHA RUN RECORD        8 fields                               every report
PART C — GYRO SURVEY RECORD    Gyro surveys taken, Surveyed section    479 reports
PART D — RADIOACTIVE SOURCE HANDLING  Source run, Sources handled, Source handling certified   367
PART E — LOST IN HOLE          Lost in hole run, Lost in hole tool, Circulating hours accumulated on the well   54
Signed (Company Representative): <name>                               one trailing block, after the last part
Signed (lead directional driller): <name>
```

**Part A fields:**
- Hole section;
- Status (Operating 7,770, Standby 381);
- Depth start and Depth end (m MD, integers);
- Circulating hours (whole hours);
- BHA run;
- In the hole: a comma list of rig words;
- Crew on tour: `<count> <role>` items;
- counts of Gyro surveys, Pressure points, Wiper trips, Back-reaming hours and Clean-out runs.

**Part B fields:**
- Run;
- Run first day and Run last day;
- Tools in run: the same list as In the hole on every report;
- Run circulating hours;
- Metres logged and Metres reamed;
- Radioactive source carried: Yes 2,590, No 5,561.

**Part variants (6):**

| parts present | reports |
|---|---|
| A+B | 7,258 |
| A+B+C | 476 |
| A+B+D | 363 |
| A+B+E | 47 |
| A+B+D+E | 4 |
| A+B+C+E | 3 |

**Vocabulary (rig words, verbatim):**
- tools, 15: MWD collar, bit and reamer, circulating sub, density-neutron, drilling jars, float sub, gamma tool, hole opener, hydraulics package, mud motor, real-time link, resistivity tool, rotary steerable, stabiliser string, survey package;
- crew roles, 5: directional hands, night man, logging engineers, MWD engineers, performance engineer.

No report field carries a service code.

**Constant values:**
- `Contract` is `DDS-2025-118` on every report;
- `Sources handled` is always `density and neutron`;
- `Source handling certified` is always `Yes`.

**Anomalies in the files:**
- No duplicated labels, no unknown labels, no non `Label: value` lines, no blank values.
- Exception: 3 reports have both signature lines as underscores: DDR-055-20250503, DDR-149-20251122, DDR-218-20251029.
- One report (DDR-009-20251211) records 1 gyro survey in Part A but has no Part C.

**Correction to Phase 0:** Part C appears on **479** reports, not 486.

## Relationships observed

- **References:**
  - every line's `report_ref` resolves;
  - every report is cited by at least one line;
  - one report, DDR-063-20260427, is cited by two invoices (MDS-01340, MDS-01352).
- **Line vs report:**
  - well, hole section and status always agree;
  - the invoice's rig always agrees with the report's rig;
  - 8 lines carry a service date different from their report's date.
- **Wells:** 214 in both the invoices and the reports. The reports are on consecutive days with no gaps. Each day's depth start equals the previous day's depth end, and depth never decreases.
- **BHA runs:** 1,369 (well, run) pairs, numbered 1..n per well. For each run, Part B's first and last day equal the first and last report of the run, and the run's reports are consecutive. Its Run circulating hours equal the sum of the daily circulating hours, and its tools and section are stated identically on every day.
- **Invoice periods:**
  - no report day falls outside an invoice period;
  - three invoices (MDS-01619, MDS-01798, MDS-01860) have periods running into January 2027, beyond their well's last report, and overlap later invoices on the same well (13 overlapping pairs);
  - 3 lines have a service date outside their invoice period.
- **Recorded arithmetic (descriptive):**
  - the net amount equals the sum of line amounts on every invoice;
  - net + VAT differs from the total on MDS-00551, MDS-00916 and MDS-01317;
  - the stated quantity × rate differs from the stated amount on 3 lines.

These are all structural observations. Their contractual meaning is left to the audit phases.
