## 2020-W14 (train) label `covid_lockdown`, anomalous days ['2020-03-30', '2020-03-31', '2020-04-02', '2020-04-03']

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 30 March 2020 to Sunday 5 April 2020 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: The expected consumption follows from the weekday profile, the temperature and the solar radiation. The week averaged 6.1 °C, 2.2 °C below the seasonal normal, which raises expected consumption by about 224 MW. Monday 30 March 2020: 6,823 MW against an expected 7,468 MW, 8.6% below (z = -3.0). Monday 30 March 2020 falls in the COVID-19 lockdown of spring 2020. Tuesday 31 March 2020: 6,729 MW against an expected 7,479 MW, 10.0% below (z = -3.5). Tuesday 31 March 2020 falls in the COVID-19 lockdown of spring 2020. Thursday 2 April 2020: 6,311 MW against an expected 6,935 MW, 9.0% below (z = -3.2). Thursday 2 April 2020 falls in the COVID-19 lockdown of spring 2020. On Friday 3 April 2020, consumption averaged 6,122 MW, 10.0% below the expected 6,805 MW (z = -3.5). Friday 3 April 2020 falls in the COVID-19 lockdown of spring 2020. The strongest anomaly (Tuesday 31 March 2020) is due to the COVID-19 lockdown. Answer: covid_lockdown

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 30 March 2020 to Sunday 5 April 2020 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: The days that deviate from the expectation are: Monday 30 March 2020 (8.6% below expectation, z = -3.0); Tuesday 31 March 2020 (10.0% below expectation, z = -3.5); Thursday 2 April 2020 (9.0% below expectation, z = -3.2); Friday 3 April 2020 (10.0% below expectation, z = -3.5). Answer: 2020-03-30, 2020-03-31, 2020-04-02, 2020-04-03

**exchange**

> Q: Hourly data for Switzerland from Monday 30 March 2020 to Sunday 5 April 2020 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net exporter: net exports averaged 352 MW, with net imports in 57.7% of the hours. Production in the Swiss control block averaged 7,223 MW while total consumption averaged 6,870 MW, a surplus of 353 MW. Net imports came from France (749 MW). Net exports went to Germany (455 MW), Italy (410 MW), Austria (236 MW). Answer: net exporter

## 2021-W08 (train) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 22 February 2021 to Sunday 28 February 2021 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: I compare each day with the consumption expected from its weekday, temperature and solar radiation. Temperatures averaged 7.7 °C, 2.8 °C above normal for the season; this lowers the expected load by roughly 282 MW. Every day stays within the normal range; the largest gap is 4.0% below expectation, on Sunday 28 February 2021 (z = -1.4). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 22 February 2021 to Sunday 28 February 2021 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Every day of the window stays within the normal range of the weather- and calendar-adjusted expectation. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 22 February 2021 to Sunday 28 February 2021 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net importer: net imports averaged 768 MW, with net imports in 80.4% of the hours. Domestic production averaged 6,716 MW against a total consumption of 7,479 MW, a shortfall of 764 MW. Net imports came from France (1,875 MW), Germany (1,246 MW), Austria (761 MW). Net exports went to Italy (3,113 MW). Answer: net importer

## 2021-W39 (train) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 27 September 2021 to Sunday 3 October 2021 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: The expected consumption follows from the weekday profile, the temperature and the solar radiation. Temperatures averaged 14.7 °C, 1.0 °C above normal for the season; this lowers the expected load by roughly 76 MW. Every day stays within the normal range; the largest gap is 4.5% above expectation, on Monday 27 September 2021 (z = 1.5). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 27 September 2021 to Sunday 3 October 2021 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Every day of the window stays within the normal range of the weather- and calendar-adjusted expectation. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 27 September 2021 to Sunday 3 October 2021 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net importer this window, with average net imports of 1,714 MW; 89.9% of the hours were net importing. Production in the Swiss control block averaged 5,151 MW while total consumption averaged 6,862 MW, a shortfall of 1,711 MW. Net imports came from Germany (2,435 MW), France (1,410 MW). Net exports went to Italy (2,014 MW), Austria (118 MW). Answer: net importer

## 2022-W02 (train) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 10 January 2022 to Sunday 16 January 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: I compare each day with the consumption expected from its weekday, temperature and solar radiation. Temperatures averaged -0.7 °C, 2.9 °C below normal for the season; this raises the expected load by roughly 269 MW. No day leaves the normal range: the largest deviation is 3.4% above expectation on Wednesday 12 January 2022 (z = 1.2). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 10 January 2022 to Sunday 16 January 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: No day of this window deviates enough from its expected consumption to count as anomalous. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 10 January 2022 to Sunday 16 January 2022 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net importer this window, with average net imports of 1,622 MW; 75.0% of the hours were net importing. Production in the Swiss control block averaged 7,279 MW while total consumption averaged 8,893 MW, a shortfall of 1,614 MW. Net imports came from Germany (2,078 MW), Austria (610 MW). Net exports went to Italy (1,022 MW), France (43 MW). Answer: net importer

## 2022-W03 (train) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 17 January 2022 to Sunday 23 January 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: Each day is compared with what its weekday, weather and season predict. Temperatures averaged 1.1 °C, 1.2 °C below normal for the season; this raises the expected load by roughly 115 MW. Every day stays within the normal range; the largest gap is 4.3% above expectation, on Thursday 20 January 2022 (z = 1.4). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 17 January 2022 to Sunday 23 January 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: No day of this window deviates enough from its expected consumption to count as anomalous. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 17 January 2022 to Sunday 23 January 2022 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net importer this window, with average net imports of 1,707 MW; 79.8% of the hours were net importing. Production in the Swiss control block averaged 7,044 MW while total consumption averaged 8,743 MW, a shortfall of 1,699 MW. Net imports came from Germany (2,452 MW), Austria (595 MW), France (46 MW). Net exports went to Italy (1,387 MW). Answer: net importer

## 2022-W04 (train) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 24 January 2022 to Sunday 30 January 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: The expected consumption follows from the weekday profile, the temperature and the solar radiation. The week averaged 1.2 °C, 1.1 °C below the seasonal normal, which raises expected consumption by about 128 MW. No day leaves the normal range: the largest deviation is 3.0% above expectation on Saturday 29 January 2022 (z = 1.0). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 24 January 2022 to Sunday 30 January 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Every day of the window stays within the normal range of the weather- and calendar-adjusted expectation. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 24 January 2022 to Sunday 30 January 2022 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net importer this window, with average net imports of 1,011 MW; 66.7% of the hours were net importing. Production in the Swiss control block averaged 7,558 MW while total consumption averaged 8,561 MW, a shortfall of 1,003 MW. Net imports came from Germany (1,978 MW), Austria (599 MW). Net exports went to Italy (1,393 MW), France (172 MW). Answer: net importer

## 2022-W15 (train) label `public_holiday`, anomalous days ['2022-04-15']

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 11 April 2022 to Sunday 17 April 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Friday 15 April 2022: Good Friday (public holiday for 89.6% of the population). Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: The expected consumption follows from the weekday profile, the temperature and the solar radiation. Temperatures averaged 12.6 °C, 3.0 °C above normal for the season; this lowers the expected load by roughly 272 MW. On Friday 15 April 2022, consumption averaged 4,962 MW, 16.9% below the expected 5,975 MW (z = -5.9). Friday 15 April 2022 was Good Friday, a public holiday for 89.6% of the population. The largest deviation, on Friday 15 April 2022, is explained by a public holiday. Answer: public_holiday

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 11 April 2022 to Sunday 17 April 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Friday 15 April 2022: Good Friday (public holiday for 89.6% of the population). Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: The days that deviate from the expectation are: Friday 15 April 2022 (16.9% below expectation, z = -5.9). Answer: 2022-04-15

**exchange**

> Q: Hourly data for Switzerland from Monday 11 April 2022 to Sunday 17 April 2022 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net importer: net imports averaged 395 MW, with net imports in 64.9% of the hours. Domestic production averaged 6,528 MW against a total consumption of 6,917 MW, a shortfall of 390 MW. Net imports came from Germany (1,543 MW), Austria (1,008 MW), France (286 MW). Net exports went to Italy (2,442 MW). Answer: net importer

## 2022-W21 (train) label `public_holiday`, anomalous days ['2022-05-26']

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 23 May 2022 to Sunday 29 May 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Thursday 26 May 2022: Ascension Day (public holiday for 100.0% of the population). Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: The expected consumption follows from the weekday profile, the temperature and the solar radiation. Temperatures averaged 16.1 °C, 0.5 °C above normal for the season; this raises the expected load by roughly 11 MW. Thursday 26 May 2022: 4,851 MW against an expected 5,731 MW, 15.3% below (z = -5.4). Thursday 26 May 2022 was Ascension Day, a public holiday for 100.0% of the population. The strongest anomaly (Thursday 26 May 2022) is due to a public holiday. Answer: public_holiday

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 23 May 2022 to Sunday 29 May 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Thursday 26 May 2022: Ascension Day (public holiday for 100.0% of the population). Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Anomalous days: Thursday 26 May 2022 (15.3% below expectation, z = -5.4). Answer: 2022-05-26

**exchange**

> Q: Hourly data for Switzerland from Monday 23 May 2022 to Sunday 29 May 2022 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net exporter: net exports averaged 345 MW, with net imports in 47.0% of the hours. Production in the Swiss control block averaged 7,111 MW while total consumption averaged 6,763 MW, a surplus of 348 MW. Net imports came from Germany (1,463 MW), France (408 MW), Austria (11 MW). Net exports went to Italy (2,227 MW). Answer: net exporter

## 2022-W24 (train) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 13 June 2022 to Sunday 19 June 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Thursday 16 June 2022: Corpus Christi (public holiday for 28.7% of the population). Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: The expected consumption follows from the weekday profile, the temperature and the solar radiation. Temperatures averaged 23.0 °C, 4.0 °C above normal for the season; this raises the expected load by roughly 154 MW. No day leaves the normal range: the largest deviation is 4.6% above expectation on Tuesday 14 June 2022 (z = 1.5). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 13 June 2022 to Sunday 19 June 2022 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Thursday 16 June 2022: Corpus Christi (public holiday for 28.7% of the population). Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Every day of the window stays within the normal range of the weather- and calendar-adjusted expectation. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 13 June 2022 to Sunday 19 June 2022 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net importer: net imports averaged 66 MW, with net imports in 53.6% of the hours. Domestic production averaged 6,578 MW against a total consumption of 6,645 MW, a shortfall of 66 MW. Net imports came from Germany (2,117 MW), Austria (270 MW). Net exports went to Italy (2,154 MW), France (166 MW). Answer: net importer

## 2023-W26 (train) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 26 June 2023 to Sunday 2 July 2023 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: I compare each day with the consumption expected from its weekday, temperature and solar radiation. Temperatures averaged 20.0 °C, 0.1 °C above normal for the season; this raises the expected load by roughly 36 MW. No day leaves the normal range: the largest deviation is 2.6% above expectation on Sunday 2 July 2023 (z = 0.9). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 26 June 2023 to Sunday 2 July 2023 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Every day of the window stays within the normal range of the weather- and calendar-adjusted expectation. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 26 June 2023 to Sunday 2 July 2023 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net exporter: net exports averaged 1,939 MW, with net imports in 26.8% of the hours. Domestic production averaged 8,716 MW against a total consumption of 6,777 MW, a surplus of 1,939 MW. Net imports came from France (625 MW), Austria (148 MW). Net exports went to Italy (1,944 MW), Germany (768 MW). Answer: net exporter

## 2023-W40 (train) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 2 October 2023 to Sunday 8 October 2023 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: Each day is compared with what its weekday, weather and season predict. The week averaged 15.4 °C, 2.7 °C above the seasonal normal, which lowers expected consumption by about 202 MW. Every day stays within the normal range; the largest gap is 3.9% below expectation, on Friday 6 October 2023 (z = -1.4). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 2 October 2023 to Sunday 8 October 2023 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Every day of the window stays within the normal range of the weather- and calendar-adjusted expectation. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 2 October 2023 to Sunday 8 October 2023 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net exporter: net exports averaged 1,181 MW, with net imports in 41.7% of the hours. Domestic production averaged 7,453 MW against a total consumption of 6,270 MW, a surplus of 1,183 MW. Net imports came from Germany (946 MW), France (922 MW), Austria (19 MW). Net exports went to Italy (3,068 MW). Answer: net exporter

## 2024-W13 (validation) label `public_holiday`, anomalous days ['2024-03-29']

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 25 March 2024 to Sunday 31 March 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Friday 29 March 2024: Good Friday (public holiday for 89.6% of the population). Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: Each day is compared with what its weekday, weather and season predict. Temperatures averaged 9.4 °C, 1.5 °C above normal for the season; this lowers the expected load by roughly 122 MW. Friday 29 March 2024: 5,351 MW against an expected 6,638 MW, 19.4% below (z = -6.8). Friday 29 March 2024 was Good Friday, a public holiday for 89.6% of the population. The largest deviation, on Friday 29 March 2024, is explained by a public holiday. Answer: public_holiday

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 25 March 2024 to Sunday 31 March 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Friday 29 March 2024: Good Friday (public holiday for 89.6% of the population). Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Anomalous days: Friday 29 March 2024 (19.4% below expectation, z = -6.8). Answer: 2024-03-29

**exchange**

> Q: Hourly data for Switzerland from Monday 25 March 2024 to Sunday 31 March 2024 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net exporter this window, with average net exports of 1,239 MW; 18.0% of the hours were net importing. Domestic production averaged 7,908 MW against a total consumption of 6,662 MW, a surplus of 1,246 MW. Net imports came from France (1,313 MW), Austria (153 MW). Net exports went to Italy (1,864 MW), Germany (842 MW). Answer: net exporter

## 2024-W15 (validation) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 8 April 2024 to Sunday 14 April 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: Each day is compared with what its weekday, weather and season predict. Temperatures averaged 13.4 °C, 4.0 °C above normal for the season; this lowers the expected load by roughly 321 MW. Every day stays within the normal range; the largest gap is 5.8% below expectation, on Friday 12 April 2024 (z = -2.0). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 8 April 2024 to Sunday 14 April 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: No day of this window deviates enough from its expected consumption to count as anomalous. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 8 April 2024 to Sunday 14 April 2024 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net exporter this window, with average net exports of 1,605 MW; 14.9% of the hours were net importing. Production in the Swiss control block averaged 8,333 MW while total consumption averaged 6,724 MW, a surplus of 1,609 MW. Net imports came from France (1,126 MW), Austria (223 MW). Net exports went to Italy (2,109 MW), Germany (846 MW). Answer: net exporter

## 2024-W16 (validation) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 15 April 2024 to Sunday 21 April 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: I compare each day with the consumption expected from its weekday, temperature and solar radiation. The week averaged 6.6 °C, 3.6 °C below the seasonal normal, which raises expected consumption by about 287 MW. Every day stays within the normal range; the largest gap is 4.2% below expectation, on Thursday 18 April 2024 (z = -1.5). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 15 April 2024 to Sunday 21 April 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: No day of this window deviates enough from its expected consumption to count as anomalous. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 15 April 2024 to Sunday 21 April 2024 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net exporter this window, with average net exports of 1,179 MW; 35.7% of the hours were net importing. Production in the Swiss control block averaged 8,427 MW while total consumption averaged 7,245 MW, a surplus of 1,181 MW. Net imports came from France (1,633 MW). Net exports went to Italy (1,628 MW), Germany (1,037 MW), Austria (147 MW). Answer: net exporter

## 2024-W35 (validation) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 26 August 2024 to Sunday 1 September 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: The expected consumption follows from the weekday profile, the temperature and the solar radiation. The week averaged 21.2 °C, 2.1 °C above the seasonal normal, which raises expected consumption by about 94 MW. Every day stays within the normal range; the largest gap is 1.9% above expectation, on Friday 30 August 2024 (z = 0.6). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 26 August 2024 to Sunday 1 September 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: No day of this window deviates enough from its expected consumption to count as anomalous. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 26 August 2024 to Sunday 1 September 2024 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net exporter: net exports averaged 3,279 MW, with net imports in 0.0% of the hours. Domestic production averaged 9,596 MW against a total consumption of 6,316 MW, a surplus of 3,279 MW. Net imports came from Austria (50 MW). Net exports went to Italy (2,711 MW), Germany (473 MW), France (145 MW). Answer: net exporter

## 2024-W45 (validation) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 4 November 2024 to Sunday 10 November 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: Each day is compared with what its weekday, weather and season predict. Temperatures averaged 8.0 °C, 0.1 °C below normal for the season; this raises the expected load by roughly 7 MW. Every day stays within the normal range; the largest gap is 4.3% below expectation, on Monday 4 November 2024 (z = -1.5). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 4 November 2024 to Sunday 10 November 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: No day of this window deviates enough from its expected consumption to count as anomalous. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 4 November 2024 to Sunday 10 November 2024 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net exporter this window, with average net exports of 1,237 MW; 31.0% of the hours were net importing. Production in the Swiss control block averaged 8,476 MW while total consumption averaged 7,235 MW, a surplus of 1,241 MW. Net imports came from France (1,361 MW). Net exports went to Italy (1,592 MW), Germany (800 MW), Austria (206 MW). Answer: net exporter

## 2024-W51 (validation) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 16 December 2024 to Sunday 22 December 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: I compare each day with the consumption expected from its weekday, temperature and solar radiation. Temperatures averaged 3.5 °C, 0.1 °C above normal for the season; this lowers the expected load by roughly 11 MW. Every day stays within the normal range; the largest gap is 3.8% below expectation, on Saturday 21 December 2024 (z = -1.4). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 16 December 2024 to Sunday 22 December 2024 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Every day of the window stays within the normal range of the weather- and calendar-adjusted expectation. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 16 December 2024 to Sunday 22 December 2024 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net importer: net imports averaged 1,055 MW, with net imports in 78.0% of the hours. Domestic production averaged 6,963 MW against a total consumption of 8,014 MW, a shortfall of 1,051 MW. Net imports came from Germany (2,748 MW), France (1,452 MW), Austria (476 MW). Net exports went to Italy (3,621 MW). Answer: net importer

## 2025-W07 (test) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 10 February 2025 to Sunday 16 February 2025 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: The expected consumption follows from the weekday profile, the temperature and the solar radiation. Temperatures averaged 3.1 °C, 1.5 °C below normal for the season; this raises the expected load by roughly 128 MW. No day leaves the normal range: the largest deviation is 5.7% above expectation on Friday 14 February 2025 (z = 2.0). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 10 February 2025 to Sunday 16 February 2025 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: none. Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: No day of this window deviates enough from its expected consumption to count as anomalous. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 10 February 2025 to Sunday 16 February 2025 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Switzerland was a net importer this window, with average net imports of 457 MW; 61.9% of the hours were net importing. Production in the Swiss control block averaged 7,644 MW while total consumption averaged 8,098 MW, a shortfall of 454 MW. Net imports came from France (1,617 MW), Germany (568 MW), Austria (5 MW). Net exports went to Italy (1,733 MW). Answer: net importer

## 2025-W18 (test) label `public_holiday`, anomalous days ['2025-05-01']

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 28 April 2025 to Sunday 4 May 2025 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Thursday 1 May 2025: Labor Day (public holiday for 42.7% of the population). Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: I compare each day with the consumption expected from its weekday, temperature and solar radiation. The week averaged 16.5 °C, 4.3 °C above the seasonal normal, which lowers expected consumption by about 316 MW. On Thursday 1 May 2025, consumption averaged 5,074 MW, 8.5% below the expected 5,547 MW (z = -3.0). Thursday 1 May 2025 was Labor Day, a public holiday for 42.7% of the population. The largest deviation, on Thursday 1 May 2025, is explained by a public holiday. Answer: public_holiday

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 28 April 2025 to Sunday 4 May 2025 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Thursday 1 May 2025: Labor Day (public holiday for 42.7% of the population). Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Anomalous days: Thursday 1 May 2025 (8.5% below expectation, z = -3.0). Answer: 2025-05-01

**exchange**

> Q: Hourly data for Switzerland from Monday 28 April 2025 to Sunday 4 May 2025 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net exporter: net exports averaged 772 MW, with net imports in 32.1% of the hours. Domestic production averaged 6,950 MW against a total consumption of 6,177 MW, a surplus of 774 MW. Net imports came from France (1,105 MW). Net exports went to Germany (1,100 MW), Italy (568 MW), Austria (210 MW). Answer: net exporter

## 2025-W50 (test) label `none`, anomalous days none

**anomaly_cause**

> Q: Hourly data for Switzerland from Monday 8 December 2025 to Sunday 14 December 2025 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Monday 8 December 2025: Immaculate Conception (public holiday for 25.9% of the population). Did consumption deviate from what the weekday, weather and season predict? Explain, then name the cause of the largest deviation.

> A: I compare each day with the consumption expected from its weekday, temperature and solar radiation. Temperatures averaged 5.7 °C, 3.0 °C above normal for the season; this lowers the expected load by roughly 310 MW. Every day stays within the normal range; the largest gap is 1.5% below expectation, on Monday 8 December 2025 (z = -0.5). No anomaly. Answer: none

**anomaly_days**

> Q: Hourly data for Switzerland from Monday 8 December 2025 to Sunday 14 December 2025 (Swiss local time). The series are end-user electricity consumption (MW), population-weighted air temperature (°C) and global solar radiation (W/m²). Public holidays this week: Monday 8 December 2025: Immaculate Conception (public holiday for 25.9% of the population). Which days of this week had abnormal consumption, given the weekday, weather and season?

> A: Every day of the window stays within the normal range of the weather- and calendar-adjusted expectation. Answer: none

**exchange**

> Q: Hourly data for Switzerland from Monday 8 December 2025 to Sunday 14 December 2025 (Swiss local time). The series are net imports from Austria, Germany, France and Italy (MW, positive means import into Switzerland), Swiss production and total consumption (MW). Was Switzerland a net importer or exporter of electricity this week, and through which borders?

> A: Over the window, Switzerland was a net importer: net imports averaged 1,498 MW, with net imports in 78.6% of the hours. Production in the Swiss control block averaged 6,364 MW while total consumption averaged 7,864 MW, a shortfall of 1,500 MW. Net imports came from France (2,498 MW), Germany (850 MW). Net exports went to Italy (1,529 MW), Austria (321 MW). Answer: net importer

