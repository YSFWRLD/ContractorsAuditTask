# Drilling Phase 3 — quantity summary

Phase 3 mapping and coverage statistics from the Daily Drilling Reports. Not prices, not findings; no invoice data was read.

- quantities: 114,745 (reading-independent 76,034; switch-dependent 38,711)
- by basis: {'COUNT': 2296, 'HOUR': 10523, 'LOST_IN_HOLE': 54, 'METRE': 19151, 'PERSON_DAY': 30444, 'RENTAL_DAY': 49729, 'RUN': 1451, 'STANDBY_DAY': 241, 'WELL': 856}
- canonical sha256: `b7b89e99ca4b39dcca0fa8026c69345753db677d9971a3475118e64a58e6f513`

| service | readings | basis | unit | records | total | wells | day status | conditions |
|---|---|---|---|---|---|---|---|---|
| DD-101 | (reading-independent) | PERSON_DAY | person-day | 8,151 | 16302 | 214 | {'Operating': 7770, 'Standby': 381} | {'REPORT_SIGNED=False': 3, 'REPORT_SIGNED=True': 8148} |
| DD-102 | dd102_basis=PER_COORDINATOR_RECORDED | PERSON_DAY | day | 8,151 | 8151 | 214 | {'Operating': 7770, 'Standby': 381} | {'REPORT_SIGNED=False': 3, 'REPORT_SIGNED=True': 8148} |
| DD-102 | dd102_basis=PER_DAY_TOOL_IN_HOLE | RENTAL_DAY | day | 8,151 | 8151 | 214 | {'Operating': 7770, 'Standby': 381} | {'REPORT_SIGNED=False': 3, 'REPORT_SIGNED=True': 8148} |
| DD-110 | (reading-independent) | RENTAL_DAY | day | 3,304 | 3304 | 214 | {'Operating': 3164, 'Standby': 140} | {'REPORT_SIGNED=False': 2, 'REPORT_SIGNED=True': 3302} |
| DD-111 | (reading-independent) | RUN | run | 654 | 654 | 214 | {'n/a': 654} | {'RECORD_PART_B=True': 654, 'REPORT_SIGNED=True': 654} |
| DD-120 | dd120_hours=CIRCULATING_ONLY | HOUR | hour | 4,790 | 80334 | 214 | {'Operating': 4606, 'Standby': 184} | {'OPERATING_DAY=False': 184, 'OPERATING_DAY=True': 4606, 'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 4789} |
| DD-120 | dd120_hours=CIRCULATING_PLUS_BACK_REAMING | HOUR | hour | 4,790 | 82738 | 214 | {'Operating': 4606, 'Standby': 184} | {'OPERATING_DAY=False': 184, 'OPERATING_DAY=True': 4606, 'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 4789} |
| DD-121 | dd121_condition=STANDBY_DAY_RSS_IN_HOLE | STANDBY_DAY | day | 241 | 241 | 146 | {'Standby': 241} | {'REPORT_SIGNED=True': 241, 'STANDBY_DAY=True': 241} |
| DD-130 | (reading-independent) | COUNT | survey | 480 | 717 | 189 | {'Operating': 480} | {'OPERATING_DAY=True': 480, 'RECORD_PART_C=False': 1, 'RECORD_PART_C=True': 479, 'REPORT_SIGNED=True': 480} |
| DD-140 | (reading-independent) | WELL | well | 214 | 214 | 214 | {'n/a': 214} | {} |
| HC-601 | (reading-independent) | RENTAL_DAY | day | 1,767 | 1767 | 214 | {'Operating': 1682, 'Standby': 85} | {'REPORT_SIGNED=False': 2, 'REPORT_SIGNED=True': 1765} |
| HC-610 | (reading-independent) | COUNT | trip | 943 | 943 | 214 | {'Operating': 943} | {'OPERATING_DAY=True': 943, 'REPORT_SIGNED=True': 943} |
| HC-620 | (reading-independent) | RENTAL_DAY | day | 8,151 | 8151 | 214 | {'Operating': 7770, 'Standby': 381} | {'REPORT_SIGNED=False': 3, 'REPORT_SIGNED=True': 8148} |
| HC-630 | hc630_basis=DAILY_COUNT | COUNT | run | 428 | 428 | 214 | {'Operating': 428} | {'OPERATING_DAY=True': 428, 'REPORT_SIGNED=True': 428} |
| HC-630 | hc630_basis=PER_BHA_RUN | RUN | run | 428 | 428 | 214 | {'n/a': 428} | {} |
| HC-640 | (reading-independent) | RENTAL_DAY | day | 2,257 | 2257 | 214 | {'Operating': 2142, 'Standby': 115} | {'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 2256} |
| LH-711 | (reading-independent) | LOST_IN_HOLE | each | 10 | 10 | 10 | {'Operating': 10} | {'RECORD_PART_E=True': 10, 'REPORT_SIGNED=True': 10} |
| LH-712 | (reading-independent) | LOST_IN_HOLE | each | 17 | 17 | 17 | {'Operating': 17} | {'RECORD_PART_E=True': 17, 'REPORT_SIGNED=True': 17} |
| LH-713 | (reading-independent) | LOST_IN_HOLE | each | 19 | 19 | 19 | {'Operating': 19} | {'RECORD_PART_E=True': 19, 'REPORT_SIGNED=True': 19} |
| LH-714 | appendix_g_reading=LITERAL | LOST_IN_HOLE | each | 8 | 8 | 8 | {'Operating': 8} | {'RECORD_PART_E=True': 8, 'REPORT_SIGNED=True': 8} |
| LW-401 | (reading-independent) | PERSON_DAY | person-day | 3,430 | 3430 | 214 | {'Operating': 3265, 'Standby': 165} | {'REPORT_SIGNED=True': 3430} |
| LW-410 | metre_source=DAILY_DEPTH_ADVANCE;appendix_g_reading=LITERAL | METRE | metre | 2,964 | 315300 | 214 | {'Operating': 2964} | {'OPERATING_DAY=True': 2964, 'RECORD_PART_B=True': 2964, 'REPORT_SIGNED=True': 2964} |
| LW-410 | metre_source=DAILY_DEPTH_ADVANCE;appendix_g_reading=LWD_ROWS_SHIFTED | METRE | metre | 2,250 | 255195 | 214 | {'Operating': 2250} | {'OPERATING_DAY=True': 2250, 'RECORD_PART_B=True': 2250, 'REPORT_SIGNED=True': 2250} |
| LW-410 | metre_source=PART_B_RUN_METRES;appendix_g_reading=LITERAL | METRE | metre | 500 | 315300 | 214 | {'n/a': 500} | {'RECORD_PART_B=True': 500} |
| LW-410 | metre_source=PART_B_RUN_METRES;appendix_g_reading=LWD_ROWS_SHIFTED | METRE | metre | 369 | 255195 | 214 | {'n/a': 369} | {'RECORD_PART_B=True': 369} |
| LW-411 | metre_source=DAILY_DEPTH_ADVANCE;appendix_g_reading=LITERAL | METRE | metre | 2,250 | 255195 | 214 | {'Operating': 2250} | {'OPERATING_DAY=True': 2250, 'RECORD_PART_B=True': 2250, 'REPORT_SIGNED=True': 2250} |
| LW-411 | metre_source=DAILY_DEPTH_ADVANCE;appendix_g_reading=LWD_ROWS_SHIFTED | METRE | metre | 955 | 108074 | 90 | {'Operating': 955} | {'OPERATING_DAY=True': 955, 'RECORD_PART_B=True': 955, 'REPORT_SIGNED=True': 955} |
| LW-411 | metre_source=PART_B_RUN_METRES;appendix_g_reading=LITERAL | METRE | metre | 369 | 255195 | 214 | {'n/a': 369} | {'RECORD_PART_B=True': 369} |
| LW-411 | metre_source=PART_B_RUN_METRES;appendix_g_reading=LWD_ROWS_SHIFTED | METRE | metre | 156 | 108074 | 90 | {'n/a': 156} | {'RECORD_PART_B=True': 156} |
| LW-412 | metre_source=DAILY_DEPTH_ADVANCE;appendix_g_reading=LITERAL | METRE | metre | 955 | 108074 | 90 | {'Operating': 955} | {'OPERATING_DAY=True': 955, 'RECORD_PART_B=True': 955, 'REPORT_SIGNED=True': 955} |
| LW-412 | metre_source=PART_B_RUN_METRES;appendix_g_reading=LITERAL | METRE | metre | 156 | 108074 | 90 | {'n/a': 156} | {'RECORD_PART_B=True': 156} |
| LW-413 | (reading-independent) | COUNT | point | 445 | 2870 | 188 | {'Operating': 445} | {'OPERATING_DAY=True': 445, 'RECORD_PART_B=True': 445, 'REPORT_SIGNED=True': 445} |
| LW-420 | (reading-independent) | RUN | run | 369 | 369 | 214 | {'n/a': 369} | {'RECORD_PART_D=False': 2, 'RECORD_PART_D=True': 367, 'REPORT_SIGNED=True': 369} |
| LW-430 | (reading-independent) | WELL | well | 214 | 214 | 214 | {'n/a': 214} | {} |
| MB-701 | (reading-independent) | WELL | well | 214 | 214 | 214 | {'n/a': 214} | {} |
| MB-702 | (reading-independent) | WELL | well | 214 | 214 | 214 | {'n/a': 214} | {} |
| MW-301 | (reading-independent) | PERSON_DAY | person-day | 8,151 | 16302 | 214 | {'Operating': 7770, 'Standby': 381} | {'REPORT_SIGNED=False': 3, 'REPORT_SIGNED=True': 8148} |
| MW-310 | (reading-independent) | RENTAL_DAY | day | 8,151 | 8151 | 214 | {'Operating': 7770, 'Standby': 381} | {'REPORT_SIGNED=False': 3, 'REPORT_SIGNED=True': 8148} |
| MW-320 | (reading-independent) | RENTAL_DAY | day | 4,847 | 4847 | 214 | {'Operating': 4606, 'Standby': 241} | {'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 4846} |
| MW-330 | (reading-independent) | RENTAL_DAY | day | 8,151 | 8151 | 214 | {'Operating': 7770, 'Standby': 381} | {'REPORT_SIGNED=False': 3, 'REPORT_SIGNED=True': 8148} |
| PD-201 | (reading-independent) | PERSON_DAY | person-day | 2,561 | 2561 | 114 | {'Operating': 2434, 'Standby': 127} | {'PERFORMANCE_SECTION_NOMINATED=None': 2561, 'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 2560} |
| PD-210 | (reading-independent) | METRE | metre | 7,427 | 1064300 | 214 | {'Operating': 7427} | {'PERFORMANCE_SECTION_NOMINATED=False': 2890, 'PERFORMANCE_SECTION_NOMINATED=None': 4537, 'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 7426} |
| PD-220 | (reading-independent) | RENTAL_DAY | day | 1,190 | 1190 | 114 | {'Operating': 1130, 'Standby': 60} | {'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 1189} |
| PD-230 | (reading-independent) | RENTAL_DAY | day | 1,190 | 1190 | 114 | {'Operating': 1130, 'Standby': 60} | {'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 1189} |
| RM-510 | metre_source=DAILY_DEPTH_ADVANCE | METRE | metre | 679 | 108886 | 74 | {'Operating': 679} | {'OPERATING_DAY=True': 679, 'RECORD_PART_B=True': 679, 'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 678} |
| RM-510 | metre_source=PART_B_RUN_METRES | METRE | metre | 121 | 108886 | 74 | {'n/a': 121} | {'RECORD_PART_B=True': 121} |
| RM-511 | (reading-independent) | RENTAL_DAY | day | 803 | 803 | 74 | {'Operating': 753, 'Standby': 50} | {'REPORT_SIGNED=False': 1, 'REPORT_SIGNED=True': 802} |
| RM-520 | (reading-independent) | RENTAL_DAY | day | 1,767 | 1767 | 214 | {'Operating': 1682, 'Standby': 85} | {'REPORT_SIGNED=False': 2, 'REPORT_SIGNED=True': 1765} |
| RM-530 | (reading-independent) | HOUR | hour | 943 | 5199 | 214 | {'Operating': 943} | {'OPERATING_DAY=True': 943, 'REPORT_SIGNED=True': 943} |

## Interpretation switches

| switch | ambiguity | applies in | readings (Phase 3 quantities) | default | approval needed |
|---|---|---|---|---|---|
| appendix_g_reading | AMB-17 | PHASE_3_QUANTITIES | LITERAL (7202), LWD_ROWS_SHIFTED (3730) | LITERAL | yes |
| appendix_g_duplicates | AMB-16 | PHASE_3_QUANTITIES | CONTEXT_SELECTS (0), UNRESOLVED (0) | CONTEXT_SELECTS | no |
| dd102_basis | AMB-18 | PHASE_3_QUANTITIES | PER_COORDINATOR_RECORDED (8151), PER_DAY_TOOL_IN_HOLE (8151) | PER_COORDINATOR_RECORDED | yes |
| hc630_basis | AMB-19 | PHASE_3_QUANTITIES | DAILY_COUNT (428), PER_BHA_RUN (428) | DAILY_COUNT | yes |
| dd121_condition | AMB-20 | PHASE_3_QUANTITIES | STANDBY_DAY_RSS_IN_HOLE (241), EVERY_STANDBY_DAY_OF_RSS_WELL (0) | STANDBY_DAY_RSS_IN_HOLE | yes |
| dd120_hours | AMB-06 | PHASE_3_QUANTITIES | CIRCULATING_ONLY (4790), CIRCULATING_PLUS_BACK_REAMING (4790) | — | yes |
| metre_source | AMB-24 | PHASE_3_QUANTITIES | DAILY_DEPTH_ADVANCE (10053), PART_B_RUN_METRES (1671) | DAILY_DEPTH_ADVANCE | yes |
| lih_hours | AMB-22 | PHASE_3_QUANTITIES | PART_E_STATED (0), TOOL_ACCUMULATED (0) | PART_E_STATED | yes |
| report_vocabulary | AMB-15 | PHASE_5_AUDIT | RIG_WORDS_VALID (0), CODES_REQUIRED (0) | RIG_WORDS_VALID | yes |
| rig_up_hour | AMB-05 | PHASE_4_PRICING | PER_DAY_THEN_MINIMUM (0), PER_BHA_RUN (0), NO_DEDUCTION (0), MINIMUM_THEN_PER_DAY (0) | — | yes |
| pd210_class_factor | AMB-02 | PHASE_4_PRICING | APPLY (0), DO_NOT_APPLY (0) | — | yes |
| standby_section_factor | AMB-03 | PHASE_4_PRICING | APPLY (0), OMIT (0) | — | yes |
| rig_services_index | AMB-04 | PHASE_4_PRICING | APPLY_FROM_FIRST_MONTH (0), NOT_APPLIED (0) | APPLY_FROM_FIRST_MONTH | yes |
| dd120_rate_from_feb_2026 | AMB-07 | PHASE_4_PRICING | LATER_ISSUED_GOVERNS (0), LATER_EFFECTIVE_GOVERNS (0), MONTHLY_TABLE_SEPARATE (0) | — | yes |
| monthly_rate_basis | AMB-08 | PHASE_4_PRICING | BASE_RATE_THEN_BUILD_UP (0), FINAL_RATE (0) | BASE_RATE_THEN_BUILD_UP | yes |
| principal_discount_combination | AMB-09 | PHASE_4_PRICING | LATER_REPLACES (0), CUMULATIVE (0) | LATER_REPLACES | no |
| volume_tier_scope | AMB-10 | PHASE_4_PRICING | PER_WELL (0), CONTRACT_WIDE (0) | — | yes |
| contract_year_2 | AMB-11 | PHASE_4_PRICING | STARTS_2026_01_01 (0), YEAR_1_EXTENDED (0) | STARTS_2026_01_01 | yes |
| lih_replacement_value | AMB-21 | PHASE_4_PRICING | SCHEDULE_2D_CONVERTED (0), SCHEDULE_6_USD (0) | SCHEDULE_2D_CONVERTED | yes |
| ds900_threshold_basis | AMB-26 | PHASE_4_PRICING | SERVICES_ONLY (0), ALL_CHARGES (0) | SERVICES_ONLY | yes |
| unranked_precedence | AMB-01 | PHASE_4_PRICING | NO_RANK_CASE_BY_CASE (0), RANK_BY_NAME (0), CLAUSE_2_EXHAUSTIVE (0) | — | yes |
| backdated_adjustment | AMB-12 | PHASE_5_AUDIT | CONTRACT_WIDE_ON_OR_AFTER (0), CONTRACT_WIDE_AFTER (0), PER_WELL (0), NO_REPRICING (0) | — | yes |
| calloff_evidence | AMB-13 | PHASE_5_AUDIT | INVOICE_STATEMENT_UNVERIFIED (0), UNVERIFIABLE_QUERY (0) | — | yes |
| record_signatories | AMB-14 | PHASE_5_AUDIT | DDR_SIGNATURES_COVER_PARTS (0), FORM_SIGNATORIES_REQUIRED (0) | DDR_SIGNATURES_COVER_PARTS | yes |
| missing_record_consequence | AMB-23 | PHASE_5_AUDIT | PART_REJECT (0), QUERY (0) | — | yes |
| submission_date | AMB-25 | PHASE_5_AUDIT | INVOICE_DATE_IS_SUBMISSION (0), UNKNOWN_QUERY (0) | — | yes |

## Reports affected

- by ambiguity: {'AMB-05': 5305, 'AMB-06': 5305, 'AMB-13': 6827, 'AMB-16': 8151, 'AMB-17': 8151, 'AMB-18': 8151, 'AMB-19': 428, 'AMB-20': 241, 'AMB-22': 54, 'AMB-24': 3657}
- by switch: {'appendix_g_reading': 2975, 'calloff_evidence': 6827, 'contract_year_2': 6827, 'dd102_basis': 8151, 'dd120_hours': 4790, 'dd120_rate_from_feb_2026': 8151, 'dd121_condition': 241, 'hc630_basis': 428, 'lih_hours': 54, 'lih_replacement_value': 54, 'metre_source': 3657, 'monthly_rate_basis': 6557, 'pd210_class_factor': 6827, 'principal_discount_combination': 8151, 'rig_services_index': 8151, 'rig_up_hour': 5305, 'standby_section_factor': 381, 'volume_tier_scope': 6827}

## Evidence facts (recorded, not used to choose a reading)

- **AMB-17, AMB-24** Runs whose tools include 'gamma tool' (literal LW-410) and runs with Part B metres logged > 0. {'runs': 1369, 'runs_with_gamma_tool': 500, 'runs_with_metres_logged': 500, 'runs_where_both_hold': 500}
- **AMB-17** Runs whose tools include 'resistivity tool' (literal LW-411 density and neutron) and runs carrying a radioactive source (T9: density and neutron need one). {'runs_with_resistivity_tool': 369, 'runs_carrying_source': 369, 'runs_where_both_hold': 369, 'runs_with_density_neutron': 156}
- **AMB-24** Runs whose tools include 'hole opener' (RM-511, the underreamer of cl. 25) and runs with metres reamed > 0. {'runs_with_hole_opener': 121, 'runs_with_metres_reamed': 121, 'runs_where_both_hold': 121}
- **AMB-17** Days with 'logging engineers' on tour, and days with any literal LWD tool word in the hole. {'days_with_logging_crew': 3430, 'days_with_lwd_word': 3430, 'days_where_both_hold': 3430}
- **AMB-13** Hole sections on days with 'performance engineer' on tour (performance-drilled sections are nominated in call-offs, which are not provided). {'sections': {'12-1/4"': 1190, '8-1/2"': 1371}}
- **AMB-05, AMB-06, AMB-20** Standby days: circulating hours are still recorded on some; the rotary steerable is in the hole on some. {'standby_days': 381, 'standby_days_with_circulating_hours': 290, 'standby_days_with_rss_in_hole': 241}
- **AMB-14, AMB-23** Records named by Schedule 5 that are absent on a day they apply (structural; consequence undecided). {'gyro_count_without_part_c': ['DDR-009-20251211'], 'source_runs_without_part_d_on_first_day': ['DDR-029-20260515', 'DDR-201-20251115']}
