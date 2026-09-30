# Drilling Phase 3 — service mapping

Phase 3 mapping and coverage statistics from the Daily Drilling Reports. Not prices, not findings; no invoice data was read.

- reports interpreted: 8,151 of 8,151; with at least one mapped service: 8,151
- term mappings: 84,036 — deterministic 76,915, ambiguous 0, switch-dependent 7,121
- by status: {'IDENTIFIED': 60567, 'IDENTIFIED_BY_CONTEXT': 16348, 'UNRESOLVED_INTERPRETATION': 7121}
- service coverage: {'services_in_schedule_1': 38, 'services_evidenced_under_some_reading': 38, 'services_never_evidenced': [], 'services_evidenced_only_under_some_readings': ['LH-714', 'LW-412']}
- terms with no candidate under some reading: ['gamma tool']
- terms mapping to more than one code: {'LITERAL': ['MWD collar', 'gamma tool', 'mud motor', 'rotary steerable'], 'LWD_ROWS_SHIFTED': ['MWD collar', 'mud motor', 'resistivity tool', 'rotary steerable']}

| field | term | statuses | codes (literal) | codes (LWD rows shifted) |
|---|---|---|---|---|
| Crew on tour | MWD engineers | {'IDENTIFIED': 8151} | MW-301 | MW-301 |
| Crew on tour | directional hands | {'IDENTIFIED': 8151} | DD-101 | DD-101 |
| Crew on tour | logging engineers | {'IDENTIFIED': 3430} | LW-401 | LW-401 |
| Crew on tour | night man | {'IDENTIFIED': 8151} | DD-102 | DD-102 |
| Crew on tour | performance engineer | {'IDENTIFIED': 2561} | PD-201 | PD-201 |
| In the hole | MWD collar | {'IDENTIFIED_BY_CONTEXT': 8151} | LH-713, MW-310 | LH-713, MW-310 |
| In the hole | bit and reamer | {'IDENTIFIED': 1190} | PD-220 | PD-220 |
| In the hole | circulating sub | {'IDENTIFIED': 1767} | HC-601 | HC-601 |
| In the hole | density-neutron | {'UNRESOLVED_INTERPRETATION': 1093} | LW-412 | LW-411 |
| In the hole | drilling jars | {'IDENTIFIED': 8151} | HC-620 | HC-620 |
| In the hole | float sub | {'IDENTIFIED': 2257} | HC-640 | HC-640 |
| In the hole | gamma tool | {'UNRESOLVED_INTERPRETATION': 3430} | LH-714, LW-410 |  |
| In the hole | hole opener | {'IDENTIFIED': 803} | RM-511 | RM-511 |
| In the hole | hydraulics package | {'IDENTIFIED': 1190} | PD-230 | PD-230 |
| In the hole | mud motor | {'IDENTIFIED_BY_CONTEXT': 3304} | DD-110, LH-711 | DD-110, LH-711 |
| In the hole | real-time link | {'IDENTIFIED': 8151} | MW-330 | MW-330 |
| In the hole | resistivity tool | {'UNRESOLVED_INTERPRETATION': 2590} | LW-411 | LH-714, LW-410 |
| In the hole | rotary steerable | {'IDENTIFIED_BY_CONTEXT': 4847} | DD-120, LH-712 | DD-120, LH-712 |
| In the hole | stabiliser string | {'IDENTIFIED': 1767} | RM-520 | RM-520 |
| In the hole | survey package | {'IDENTIFIED': 4847} | MW-320 | MW-320 |
| Lost in hole tool | MWD collar | {'IDENTIFIED_BY_CONTEXT': 19} | LH-713, MW-310 | LH-713, MW-310 |
| Lost in hole tool | gamma tool | {'UNRESOLVED_INTERPRETATION': 8} | LH-714, LW-410 |  |
| Lost in hole tool | mud motor | {'IDENTIFIED_BY_CONTEXT': 10} | DD-110, LH-711 | DD-110, LH-711 |
| Lost in hole tool | rotary steerable | {'IDENTIFIED_BY_CONTEXT': 17} | DD-120, LH-712 | DD-120, LH-712 |
