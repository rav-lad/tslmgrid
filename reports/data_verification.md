# Data verification against independent references

Dataset: `data/processed/ch_hourly.parquet`, 52608 hours, 2019-12-31 23:00:00+00:00 to 2025-12-31 22:00:00+00:00 (UTC).

## 1. Swissgrid annual totals (sheet `Uebersicht`) vs our hourly sums

| year | series | ours (MWh) | Swissgrid sheet (MWh) | rel. diff |
| --- | --- | --- | --- | --- |
| 2020 | production | 67,652,570 | 5,640,485 | 1.1e+01 |
| 2020 | end-user consumption | 54,659,690 | 5,661,051 | 8.7e+00 |
| 2020 | total consumption | 62,420,797 | 6,228,140 | 9.0e+00 |
| 2021 | production | 61,562,502 | 61,562,502 | 9.1e-15 |
| 2021 | end-user consumption | 56,792,303 | 56,792,303 | 2.9e-15 |
| 2021 | total consumption | 64,413,509 | 64,413,509 | 2.8e-15 |
| 2022 | production | 60,791,981 | 60,791,981 | 5.1e-15 |
| 2022 | end-user consumption | 55,451,790 | 55,451,790 | 3.6e-15 |
| 2022 | total consumption | 64,678,189 | 64,678,189 | 3.3e-15 |
| 2023 | production | 67,960,463 | 67,960,463 | 4.2e-15 |
| 2023 | end-user consumption | 53,478,446 | 53,478,446 | 7.4e-15 |
| 2023 | total consumption | 62,081,599 | 62,081,599 | 7.3e-15 |
| 2024 | production | 75,565,203 | 75,565,203 | 7.1e-15 |
| 2024 | end-user consumption | 53,369,089 | 53,369,089 | 6.0e-15 |
| 2024 | total consumption | 61,626,683 | 61,626,683 | 1.2e-15 |
| 2025 | production | 61,685,613 | 61,685,613 | 3.7e-15 |
| 2025 | end-user consumption | 53,495,504 | 53,495,504 | 2.4e-15 |
| 2025 | total consumption | 62,077,642 | 62,077,642 | 3.4e-15 |

Largest relative difference, 2021-2025: **9.1e-15** (identical up to float rounding).

2020: the cached values of the summary sheet match neither the year nor any month of the time series (the formulas were last evaluated before the April 2021 re-publication of the data). 2020 is therefore checked only against Energy-Charts in section 2.

## 2. Energy-Charts (Fraunhofer ISE, ENTSO-E data) hourly Swiss data

Overlap: 52608 hours. Generation columns summed: Nuclear, Hydro Run-of-River, Hydro water reservoir, Hydro pumped storage, Others, Wind onshore, Solar.

| comparison | Pearson r (hourly) | Pearson r (daily) | mean ratio ours/EC |
| --- | --- | --- | --- |
| Swissgrid total consumption vs EC load | 0.903 | 0.927 | 0.942 |
| Swissgrid end-user consumption vs EC load | 0.778 | 0.850 | 0.817 |
| Swissgrid production vs EC generation sum | 0.953 | 0.958 | 0.938 |
| Swissgrid net import vs EC cross-border | 0.990 | 0.992 | 1.137 |

Per year, daily r of Swissgrid total consumption vs EC load: 2020: 1.000, 2021: 0.972, 2022: 1.000, 2023: 0.829, 2024: 0.903, 2025: 0.964.

## 3. MeteoSwiss daily means (Zürich / Fluntern) vs our hourly station data

- Daily window UTC day 00-24: 2193 days; temperature r = 1.0000, mean abs diff 0.028 °C; radiation r = 1.0000, mean abs diff 0.27 W/m².
- Daily window UTC day 23-23 (= CET civil day): 2192 days; temperature r = 0.9999, mean abs diff 0.089 °C; radiation r = 1.0000, mean abs diff 0.25 W/m².

## 4. Known real-world events visible in the data

- COVID-19 lockdown (CH, from 16 Mar 2020): weekday mean 23 Mar-17 Apr 2020 = 6,051 MW vs same weeks 2021 = 6,731 MW.
- Christmas: mean load 25 Dec 2024 = 6,339 MW vs weekday mean 2-13 Dec 2024 = 7,776 MW.
- Net import by year (TWh): 2020: -5.20, 2021: +2.90, 2022: +3.93, 2023: -5.87, 2024: -13.91, 2025: +0.41. Switzerland was a net importer in 2021-2022 and a large net exporter in 2024 (very high hydro output).
- 1 August (national day): 2024-08-01 mean 4,434 MW vs Thursday 2024-07-25 5,077 MW.
