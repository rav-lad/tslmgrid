# Window review: baselines

| group                                          | system    |   n |   answered_yes |   accuracy |   recall_drop |   recall_spike |   recall_level_shift |   recall_10-15% |   recall_15-20% |   recall_20-25% |   recall_25-36% |
|:-----------------------------------------------|:----------|----:|---------------:|-----------:|--------------:|---------------:|---------------------:|----------------:|----------------:|----------------:|----------------:|
| holdout 2026 / perturbations                   | rules     |  80 |          0.6   |      0.6   |         0.318 |          0.829 |                0.522 |           0.143 |           0.692 |           0.64  |           0.629 |
| holdout 2026 / perturbations                   | threshold |  80 |          0.75  |      0.75  |         0.591 |          0.829 |                0.783 |           0.286 |           0.846 |           0.8   |           0.771 |
| holdout 2026 / real ordinary days, labelled no | rules     | 247 |          0     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| holdout 2026 / real ordinary days, labelled no | threshold | 247 |          0.008 |      0.992 |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| holdout 2026 / real special days, labelled no  | rules     |  46 |          0     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| holdout 2026 / real special days, labelled no  | threshold |  46 |          0.457 |      0.543 |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| holdout 2026 / real, labelled yes              | rules     |  11 |          1     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| holdout 2026 / real, labelled yes              | threshold |  11 |          1     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| test 2025 / perturbations                      | rules     |  80 |          0.537 |      0.537 |         0.364 |          0.533 |                0.882 |           0.833 |           0.353 |           0.565 |           0.559 |
| test 2025 / perturbations                      | threshold |  80 |          0.725 |      0.725 |         0.667 |          0.7   |                0.882 |           0.833 |           0.588 |           0.739 |           0.765 |
| test 2025 / real ordinary days, labelled no    | rules     | 302 |          0     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| test 2025 / real ordinary days, labelled no    | threshold | 302 |          0     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| test 2025 / real special days, labelled no     | rules     |  57 |          0     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| test 2025 / real special days, labelled no     | threshold |  57 |          0.561 |      0.439 |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| test 2025 / real, labelled yes                 | rules     |   6 |          1     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |
| test 2025 / real, labelled yes                 | threshold |   6 |          1     |      1     |       nan     |        nan     |              nan     |         nan     |         nan     |         nan     |         nan     |

Real days labelled yes and flagged real days (|z| >= 3), 2025 and 2026:

| date       | weekday   | kind            | period    |   level_pct |     z | label   | threshold   | rules   |
|:-----------|:----------|:----------------|:----------|------------:|------:|:--------|:------------|:--------|
| 2025-01-01 | Wed       | full_holiday    | christmas |       -20.4 | -6.96 | no      | yes         | no      |
| 2025-01-02 | Thu       | partial_holiday | christmas |       -16.4 | -5.44 | no      | yes         | no      |
| 2025-01-03 | Fri       | ordinary        | christmas |        -9.3 | -3.09 | no      | yes         | no      |
| 2025-04-18 | Fri       | full_holiday    | regular   |       -17.6 | -7.03 | no      | yes         | no      |
| 2025-04-21 | Mon       | full_holiday    | regular   |       -18.2 | -7.8  | no      | yes         | no      |
| 2025-05-01 | Thu       | partial_holiday | regular   |        -6.2 | -3    | no      | no          | no      |
| 2025-05-04 | Sun       | ordinary        | regular   |         4.1 | -0.4  | yes     | yes         | yes     |
| 2025-05-29 | Thu       | full_holiday    | regular   |       -17.1 | -6.32 | no      | yes         | no      |
| 2025-05-30 | Fri       | bridge_day      | regular   |        -9.8 | -3.93 | no      | yes         | no      |
| 2025-06-09 | Mon       | full_holiday    | regular   |       -17.8 | -7.13 | no      | yes         | no      |
| 2025-07-29 | Tue       | ordinary        | summer    |       -10.4 | -3.09 | no      | yes         | no      |
| 2025-07-31 | Thu       | ordinary        | summer    |       -11.4 | -3.37 | no      | yes         | no      |
| 2025-08-01 | Fri       | full_holiday    | summer    |       -23.3 | -7.43 | no      | yes         | no      |
| 2025-09-02 | Tue       | ordinary        | regular   |        -8.9 | -1.04 | yes     | yes         | yes     |
| 2025-09-21 | Sun       | ordinary        | regular   |         2.7 |  0.62 | yes     | yes         | yes     |
| 2025-10-23 | Thu       | ordinary        | regular   |         7.9 |  2.29 | yes     | yes         | yes     |
| 2025-10-26 | Sun       | ordinary        | regular   |         7.3 |  1.72 | yes     | yes         | yes     |
| 2025-10-27 | Mon       | ordinary        | regular   |         8.3 |  2.21 | yes     | yes         | yes     |
| 2025-12-22 | Mon       | ordinary        | christmas |        -9.8 | -3.09 | no      | yes         | no      |
| 2025-12-23 | Tue       | ordinary        | christmas |       -11.2 | -3.37 | no      | yes         | no      |
| 2025-12-24 | Wed       | ordinary        | christmas |       -12.6 | -3.96 | no      | yes         | no      |
| 2025-12-25 | Thu       | full_holiday    | christmas |       -19.5 | -6.68 | no      | yes         | no      |
| 2025-12-26 | Fri       | full_holiday    | christmas |       -17   | -6.08 | no      | yes         | no      |
| 2025-12-29 | Mon       | ordinary        | christmas |       -10.7 | -3.94 | no      | yes         | no      |
| 2025-12-30 | Tue       | ordinary        | christmas |       -10.7 | -3.74 | no      | yes         | no      |
| 2025-12-31 | Wed       | ordinary        | christmas |       -11.9 | -4.22 | no      | yes         | no      |
| 2026-01-01 | Thu       | full_holiday    | christmas |       -15.1 | -5.79 | no      | yes         | no      |
| 2026-01-02 | Fri       | partial_holiday | christmas |       -11   | -4.2  | no      | yes         | no      |
| 2026-01-08 | Thu       | ordinary        | regular   |         7.6 |  2.28 | yes     | yes         | yes     |
| 2026-01-09 | Fri       | ordinary        | regular   |         8.4 |  2.04 | yes     | yes         | yes     |
| 2026-01-10 | Sat       | ordinary        | regular   |        11.1 |  3.82 | yes     | yes         | yes     |
| 2026-01-11 | Sun       | ordinary        | regular   |         9.3 |  3.31 | yes     | yes         | yes     |
| 2026-01-12 | Mon       | ordinary        | regular   |         7.5 |  2.04 | yes     | yes         | yes     |
| 2026-01-13 | Tue       | ordinary        | regular   |         7.6 |  2.05 | yes     | yes         | yes     |
| 2026-04-03 | Fri       | full_holiday    | regular   |        -9.7 | -4.52 | no      | yes         | no      |
| 2026-04-06 | Mon       | full_holiday    | regular   |       -16.8 | -6.05 | no      | yes         | no      |
| 2026-04-12 | Sun       | ordinary        | regular   |         2.7 |  0.89 | yes     | yes         | yes     |
| 2026-05-14 | Thu       | full_holiday    | regular   |       -14.6 | -5.92 | no      | yes         | no      |
| 2026-05-15 | Fri       | bridge_day      | regular   |        -9.5 | -3.76 | no      | yes         | no      |
| 2026-05-25 | Mon       | full_holiday    | regular   |       -17.2 | -6    | no      | yes         | no      |
| 2026-07-01 | Wed       | ordinary        | regular   |         7.7 |  3.23 | yes     | yes         | yes     |
| 2026-08-17 | Mon       | ordinary        | regular   |         7.9 |  2.46 | yes     | yes         | yes     |
| 2026-08-21 | Fri       | ordinary        | regular   |         9.6 |  2.61 | yes     | yes         | yes     |
| 2026-09-01 | Tue       | ordinary        | regular   |        -7.3 |  0.12 | yes     | yes         | yes     |
| 2026-10-25 | Sun       | ordinary        | regular   |         5.1 |  3.15 | no      | no          | no      |
