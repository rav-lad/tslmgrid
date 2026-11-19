# Day signature: baselines

| group                       | system       |   n |   parsable |   accuracy |   macro_f1 |   recall_ordinary |   recall_public_holiday |   recall_bridge_day |   recall_christmas_period |   recall_summer_holidays | recall_lockdown   |   recall_irregularity |
|:----------------------------|:-------------|----:|-----------:|-----------:|-----------:|------------------:|------------------------:|--------------------:|--------------------------:|-------------------------:|:------------------|----------------------:|
| holdout 2026 / flagged      | curve kNN    |  11 |          1 |      0.727 |      0.562 |             1     |                   0.75  |                   0 |                     0.5   |                  nan     |                   |                nan    |
| holdout 2026 / flagged      | weekday only |  11 |          1 |      0.364 |      0.133 |             1     |                   0     |                   0 |                     0     |                  nan     |                   |                nan    |
| holdout 2026 / real         | curve kNN    | 304 |          1 |      0.914 |      0.518 |             0.981 |                   0.667 |                   0 |                     0.167 |                    0.606 |                   |                nan    |
| holdout 2026 / real         | weekday only | 304 |          1 |      0.849 |      0.184 |             1     |                   0     |                   0 |                     0     |                    0     |                   |                nan    |
| holdout 2026 / simulated    | curve kNN    |  25 |          1 |      0.6   |      0.75  |           nan     |                 nan     |                 nan |                   nan     |                  nan     |                   |                  0.6  |
| holdout 2026 / simulated    | weekday only |  25 |          1 |      0     |      0     |           nan     |                 nan     |                 nan |                   nan     |                  nan     |                   |                  0    |
| test 2025 / flagged         | curve kNN    |  20 |          1 |      0.65  |      0.533 |           nan     |                   0.667 |                   0 |                     0.636 |                    1     |                   |                nan    |
| test 2025 / flagged         | weekday only |  20 |          1 |      0     |      0     |           nan     |                   0     |                   0 |                     0     |                    0     |                   |                nan    |
| test 2025 / real            | curve kNN    | 365 |          1 |      0.918 |      0.576 |             0.974 |                   0.667 |                   0 |                     0.438 |                    0.71  |                   |                nan    |
| test 2025 / real            | weekday only | 365 |          1 |      0.844 |      0.183 |             1     |                   0     |                   0 |                     0     |                    0     |                   |                nan    |
| test 2025 / simulated       | curve kNN    |  25 |          1 |      0.84  |      0.913 |           nan     |                 nan     |                 nan |                   nan     |                  nan     |                   |                  0.84 |
| test 2025 / simulated       | weekday only |  25 |          1 |      0     |      0     |           nan     |                 nan     |                 nan |                   nan     |                  nan     |                   |                  0    |
| validation 2024 / flagged   | curve kNN    |  23 |          1 |      0.739 |      0.586 |           nan     |                   0.667 |                   0 |                     0.9   |                    0.8   |                   |                nan    |
| validation 2024 / flagged   | weekday only |  23 |          1 |      0     |      0     |           nan     |                   0     |                   0 |                     0     |                    0     |                   |                nan    |
| validation 2024 / real      | curve kNN    | 151 |          1 |      0.868 |      0.646 |             0.968 |                   0.778 |                   0 |                     0.625 |                    0.767 |                   |                nan    |
| validation 2024 / real      | weekday only | 151 |          1 |      0.623 |      0.153 |             1     |                   0     |                   0 |                     0     |                    0     |                   |                nan    |
| validation 2024 / simulated | curve kNN    |  25 |          1 |      0.76  |      0.864 |           nan     |                 nan     |                 nan |                   nan     |                  nan     |                   |                  0.76 |
| validation 2024 / simulated | weekday only |  25 |          1 |      0     |      0     |           nan     |                 nan     |                 nan |                   nan     |                  nan     |                   |                  0    |

Real days of 2025 and 2026, calendar label (rows) against weekday only (columns):

| calendar         |   ordinary |
|:-----------------|-----------:|
| bridge_day       |          2 |
| christmas_period |         22 |
| ordinary         |        566 |
| public_holiday   |         15 |
| summer_holidays  |         64 |

Real days of 2025 and 2026, calendar label (rows) against curve kNN (columns):

| calendar         |   christmas_period |   irregularity |   lockdown |   ordinary |   public_holiday |   summer_holidays |
|:-----------------|-------------------:|---------------:|-----------:|-----------:|-----------------:|------------------:|
| bridge_day       |                  1 |              0 |          1 |          0 |                0 |                 0 |
| christmas_period |                  8 |              0 |          1 |          4 |                2 |                 7 |
| ordinary         |                  0 |              1 |          1 |        553 |                0 |                11 |
| public_holiday   |                  1 |              0 |          2 |          0 |               10 |                 2 |
| summer_holidays  |                  1 |              0 |          0 |         19 |                2 |                42 |
