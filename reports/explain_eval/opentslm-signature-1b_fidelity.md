# Rationale figures: opentslm-signature-1b

| group                    | system                |   n |   parsed |   level_mae |   level_within_3 |   level_sign |   daypart_rel_mae |   profile_acc |   structure_acc |   hours_jaccard |
|:-------------------------|:----------------------|----:|---------:|------------:|-----------------:|-------------:|------------------:|--------------:|----------------:|----------------:|
| holdout 2026 / flagged   | opentslm-signature-1b |  11 |    1     |        1.36 |            1     |        1     |              3.46 |         0.444 |           0.636 |           0.48  |
| holdout 2026 / flagged   | stated means          |  11 |    1     |        0.51 |            1     |        1     |              5.62 |       nan     |         nan     |         nan     |
| holdout 2026 / flagged   | weekday only          |  11 |    1     |       10.87 |            0     |        0.636 |              4.95 |         0.333 |           0.455 |         nan     |
| holdout 2026 / real      | opentslm-signature-1b | 304 |    0.997 |        0.43 |            1     |        1     |              2.19 |         0.939 |           0.848 |           0.107 |
| holdout 2026 / real      | stated means          | 304 |    1     |        0.14 |            1     |        1     |              2.03 |       nan     |         nan     |         nan     |
| holdout 2026 / real      | weekday only          | 304 |    1     |        3.32 |            0.543 |        0.659 |              1.96 |         0.953 |           0.911 |         nan     |
| holdout 2026 / simulated | opentslm-signature-1b |  25 |    1     |        0.65 |            1     |        1     |              4.72 |         0.909 |           0.32  |           0.039 |
| holdout 2026 / simulated | stated means          |  25 |    1     |        0.3  |            1     |        1     |              4.44 |       nan     |         nan     |         nan     |
| holdout 2026 / simulated | weekday only          |  25 |    1     |        4.49 |            0.36  |        0.25  |              4.42 |         0.909 |           0.04  |         nan     |
| test 2025 / flagged      | opentslm-signature-1b |  20 |    1     |        0.96 |            1     |        1     |              2.84 |         0.643 |           0.5   |           0.329 |
| test 2025 / flagged      | stated means          |  20 |    1     |        0.64 |            1     |        1     |              5.79 |       nan     |         nan     |         nan     |
| test 2025 / flagged      | weekday only          |  20 |    1     |       11.69 |            0     |        1     |              4.96 |         0.286 |           0.35  |         nan     |
| test 2025 / real         | opentslm-signature-1b | 365 |    0.997 |        0.43 |            0.997 |        1     |              2.35 |         0.956 |           0.734 |           0.064 |
| test 2025 / real         | stated means          | 365 |    1     |        0.18 |            1     |        1     |              2.35 |       nan     |         nan     |         nan     |
| test 2025 / real         | weekday only          | 365 |    1     |        3.5  |            0.556 |        0.673 |              2.23 |         0.959 |           0.808 |         nan     |
| test 2025 / simulated    | opentslm-signature-1b |  25 |    1     |        0.55 |            1     |        1     |              5.49 |         0.792 |           0.16  |           0.018 |
| test 2025 / simulated    | stated means          |  25 |    1     |        0.36 |            1     |        1     |              5.1  |       nan     |         nan     |         nan     |
| test 2025 / simulated    | weekday only          |  25 |    1     |        3.75 |            0.44  |        0.5   |              4.97 |         0.75  |           0     |         nan     |

Flagged real days (|z| >= 3) of 2025 and 2026, measured against read:

| date       | weekday   | calendar         |   level |   model_level | profile   | model_profile   | structure   | model_structure   |
|:-----------|:----------|:-----------------|--------:|--------------:|:----------|:----------------|:------------|:------------------|
| 2025-01-01 | Wed       | christmas_period |   -20.7 |         -18.8 | sunday    | saturday        | reshapes    | confined          |
| 2025-01-02 | Thu       | christmas_period |   -16.1 |         -15.1 | sunday    | saturday        | confined    | spans             |
| 2025-01-03 | Fri       | christmas_period |   -10.7 |         -10.5 | saturday  | weekday         | confined    | spans             |
| 2025-04-18 | Fri       | public_holiday   |   -17.9 |         -18.3 | saturday  | saturday        | reshapes    | confined          |
| 2025-04-21 | Mon       | public_holiday   |   -19.1 |         -18.8 | sunday    | sunday          | reshapes    | reshapes          |
| 2025-05-01 | Thu       | public_holiday   |    -7.8 |          -6.5 | saturday  | weekday         | confined    | spans             |
| 2025-05-29 | Thu       | public_holiday   |   -16.3 |         -15   | saturday  | saturday        | reshapes    | confined          |
| 2025-05-30 | Fri       | bridge_day       |    -9.7 |          -8.3 | sunday    | saturday        | confined    | confined          |
| 2025-06-09 | Mon       | public_holiday   |   -18.1 |         -16.1 | sunday    | sunday          | reshapes    | reshapes          |
| 2025-07-29 | Tue       | summer_holidays  |   -11.7 |         -12.9 | weekday   | weekday         | spans       | spans             |
| 2025-07-31 | Thu       | summer_holidays  |   -12.7 |         -13.3 | weekday   | weekday         | spans       | spans             |
| 2025-08-01 | Fri       | public_holiday   |   -23.4 |         -22.3 | saturday  | sunday          | confined    | reshapes          |
| 2025-12-22 | Mon       | christmas_period |   -10.5 |         -10.5 | weekday   | weekday         | spans       | spans             |
| 2025-12-23 | Tue       | christmas_period |   -11.6 |         -11.1 | weekday   | saturday        | spans       | spans             |
| 2025-12-24 | Wed       | christmas_period |   -13   |         -12.4 | weekday   | weekday         | spans       | spans             |
| 2025-12-25 | Thu       | christmas_period |   -20   |         -18.8 | saturday  | sunday          | confined    | reshapes          |
| 2025-12-26 | Fri       | christmas_period |   -18.7 |         -18.9 | sunday    | saturday        | confined    | confined          |
| 2025-12-29 | Mon       | christmas_period |   -11.7 |         -12.3 | saturday  | weekday         | spans       | spans             |
| 2025-12-30 | Tue       | christmas_period |   -11.7 |         -11.1 | saturday  | saturday        | spans       | confined          |
| 2025-12-31 | Wed       | christmas_period |   -12.5 |          -9.6 | saturday  | saturday        | confined    | reshapes          |
| 2026-01-01 | Thu       | christmas_period |   -16.5 |         -16.8 | saturday  | sunday          | reshapes    | reshapes          |
| 2026-01-02 | Fri       | christmas_period |   -12.5 |          -9.9 | saturday  | weekday         | confined    | spans             |
| 2026-01-10 | Sat       | ordinary         |    11.2 |           8.4 | sunday    | saturday        | spans       | spans             |
| 2026-01-11 | Sun       | ordinary         |     9.2 |           7   | sunday    | saturday        | spans       | confined          |
| 2026-04-03 | Fri       | public_holiday   |   -12.2 |         -11.1 | sunday    | saturday        | confined    | confined          |
| 2026-04-06 | Mon       | public_holiday   |   -16.7 |         -15.2 | sunday    | sunday          | reshapes    | reshapes          |
| 2026-05-14 | Thu       | public_holiday   |   -15.5 |         -16.1 | sunday    | sunday          | confined    | confined          |
| 2026-05-15 | Fri       | bridge_day       |    -9.5 |          -8.9 | weekday   | weekday         | spans       | spans             |
| 2026-05-25 | Mon       | public_holiday   |   -17.2 |         -18   | sunday    | weekday         | reshapes    | confined          |
| 2026-07-01 | Wed       | ordinary         |     6.7 |           5   | weekday   | weekday         | spans       | spans             |
| 2026-10-25 | Sun       | ordinary         |     7.8 |           7   | saturday  | sunday          | spans       | confined          |
