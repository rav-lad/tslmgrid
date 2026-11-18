# Alert review: outcomes of the flagged days

Flagged days (|z| >= 3) by split and outcome:

| split      |   consistent |   deviation_remains |   insufficient_evidence |   All |
|:-----------|-------------:|--------------------:|------------------------:|------:|
| holdout    |            6 |                   5 |                       0 |    11 |
| test       |           17 |                   3 |                       0 |    20 |
| train      |           41 |                   3 |                      55 |    99 |
| validation |           20 |                   3 |                       0 |    23 |
| All        |           84 |                  14 |                      55 |   153 |

Flagged days by context and outcome:

|                                  |   consistent |   deviation_remains |   insufficient_evidence |
|:---------------------------------|-------------:|--------------------:|------------------------:|
| ('bridge_day', 'christmas')      |            1 |                   0 |                       0 |
| ('bridge_day', 'regular')        |            4 |                   0 |                       2 |
| ('bridge_day', 'summer')         |            2 |                   0 |                       0 |
| ('full_holiday', 'christmas')    |            9 |                   0 |                       3 |
| ('full_holiday', 'regular')      |           22 |                   1 |                       3 |
| ('full_holiday', 'summer')       |            4 |                   0 |                       0 |
| ('lockdown', 'regular')          |            0 |                   0 |                      26 |
| ('ordinary', 'christmas')        |           21 |                   6 |                      19 |
| ('ordinary', 'regular')          |            0 |                   4 |                       0 |
| ('ordinary', 'summer')           |           12 |                   3 |                       1 |
| ('partial_holiday', 'christmas') |            4 |                   0 |                       1 |
| ('partial_holiday', 'regular')   |            5 |                   0 |                       0 |

Profile of the flagged days (ties apart):

| split      |   saturday |   sunday |   tie |   weekday |
|:-----------|-----------:|---------:|------:|----------:|
| holdout    |          2 |        5 |     2 |         2 |
| test       |          6 |        4 |     6 |         4 |
| train      |         30 |       23 |     9 |        27 |
| validation |          9 |        2 |     6 |         6 |

All reviewed days by split and outcome (training pool included):

| split      |   consistent |   deviation_remains |   insufficient_evidence |   All |
|:-----------|-------------:|--------------------:|------------------------:|------:|
| holdout    |          267 |                  36 |                       1 |   304 |
| test       |          310 |                  51 |                       4 |   365 |
| train      |         1136 |                  49 |                     275 |  1460 |
| validation |          321 |                  40 |                       5 |   366 |
| All        |         2034 |                 176 |                     285 |  2495 |

Calibration (train years 2021-2023): robust spread of the day-level residual {'ordinary': 2.03, 'period': 4.83, 'holiday': 3.19} %, days {'ordinary': 901, 'period': 115, 'holiday': 30}; hourly localized spreads (%): ordinary: [2.13, 2.12, 2.27, 2.43, 2.47, 2.48, 2.38, 2.01, 1.5, 1.42, 1.83, 2.27, 2.76, 2.99, 3.15, 3.1, 2.79, 2.23, 1.87, 1.72, 1.56, 1.62, 1.69, 1.85]; period: [1.92, 1.81, 1.64, 1.88, 1.79, 1.77, 2.04, 1.87, 1.61, 1.8, 1.94, 1.83, 1.79, 1.69, 1.96, 2.05, 1.77, 1.56, 1.76, 1.83, 1.61, 1.82, 1.8, 2.07]; holiday: [3.0, 3.31, 3.6, 3.29, 3.5, 3.44, 3.74, 2.34, 1.6, 1.85, 2.18, 2.98, 3.06, 4.17, 4.14, 3.64, 3.44, 2.72, 2.74, 1.86, 2.06, 1.8, 2.4, 1.42]

Flagged days where a deviation remains:

- 2021-12-24 (train, Friday 24 December 2021; no public holiday; inside the Christmas school holidays (22 December - 6 January)): day residual -5.1% (z -1.05), hours 00:00-04:59, recent level +3.7%
- 2021-12-29 (train, Wednesday 29 December 2021; no public holiday; inside the Christmas school holidays (22 December - 6 January)): day residual -0.2% (z -0.04), hours 11:00-14:59, recent level +2.7%
- 2023-12-27 (train, Wednesday 27 December 2023; no public holiday; inside the Christmas school holidays (22 December - 6 January)): day residual -4.2% (z -0.87), hours 12:00-15:59, recent level +0.7%
- 2024-07-29 (validation, Monday 29 July 2024; no public holiday; inside the core summer holidays (14 July - 15 August)): day residual -6.1% (z -1.25), hours 10:00-14:59, recent level +1.1%
- 2024-07-30 (validation, Tuesday 30 July 2024; no public holiday; inside the core summer holidays (14 July - 15 August)): day residual -5.9% (z -1.21), hours 20:00-23:59, recent level +0.8%
- 2024-08-05 (validation, Monday 5 August 2024; no public holiday; inside the core summer holidays (14 July - 15 August)): day residual -1.9% (z -0.39), hours 11:00-13:59, recent level +0.0%
- 2025-01-03 (test, Friday 3 January 2025; no public holiday; inside the Christmas school holidays (22 December - 6 January)): day residual -3.1% (z -0.64), hours 11:00-14:59, recent level +1.6%
- 2025-12-22 (test, Monday 22 December 2025; no public holiday; inside the Christmas school holidays (22 December - 6 January)): day residual -1.4% (z -0.3), hours 00:00-03:59, recent level +1.7%
- 2025-12-31 (test, Wednesday 31 December 2025; Restoration Day, a public holiday for 5.9% of the population; inside the Christmas school holidays (22 December - 6 January)): day residual 4.0% (z 0.82), hours 11:00-14:59, recent level +0.6%
- 2026-01-10 (holdout, Saturday 10 January 2026; no public holiday): day residual 11.2% (z 5.55), hours 00:00-00:59, 05:00-23:59, recent level +0.2%
- 2026-01-11 (holdout, Sunday 11 January 2026; no public holiday): day residual 9.2% (z 4.54), hours 00:00-01:59, 06:00-23:59, recent level -0.1%
- 2026-04-03 (holdout, Friday 3 April 2026; Good Friday, a public holiday for 89.6% of the population): day residual 6.8% (z 2.12), hours 05:00-08:59, recent level +0.8%
- 2026-07-01 (holdout, Wednesday 1 July 2026; no public holiday): day residual 6.7% (z 3.32), hours 00:00-01:59, 04:00-13:59, recent level +1.3%
- 2026-10-25 (holdout, Sunday 25 October 2026; no public holiday): day residual 7.8% (z 3.87), hours 02:00-04:59, 07:00-21:59, recent level +2.1%
