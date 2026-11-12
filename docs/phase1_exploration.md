# Phase 1 — exploration findings (2026-11-12)

All facts below were checked against the real files, not docs.

## Swissgrid "Energy Statistic Switzerland"

Download page: https://www.swissgrid.ch/en/home/customers/topics/energy-data-ch.html

| Year | URL (`https://www.swissgrid.ch/dam/jcr:` + …) | sha256 | Last-Modified |
| --- | --- | --- | --- |
| 2020 | `a6deeecb-74e8-4d67-a8ad-8c53c9dfbdd3/EnergieUebersichtCH-2020.xlsx` | `9ccbe5bf…d7bc` | 2021-04-28 |
| 2021 | `26fa6b22-5e81-44eb-abbd-4280c59c3697/EnergieUebersichtCH-2021.xlsx` | `ef940de1…ec9b6` | 2022-07-18 |
| 2022 | `e3af783a-6c00-40d9-bb3e-a630fb492dfb/EnergieUebersichtCH-2022.xlsx` | `0922fbf4…7368267` | 2023-07-18 |
| 2023 | `32576046-3686-4a62-bc32-9b55a89a2142/EnergieUebersichtCH-2023.xlsx` | `b86e0fab…0e7` | **2026-03-27** |
| 2024 | `4d4ca899-395d-4d3d-9958-5ace16ecbfbf/EnergieUebersichtCH-2024.xlsx` | `3944594e…8605` | 2026-03-24 |
| 2025 | `bbbbadc6-3656-4dfe-b81e-bbb9ad01be79/EnergieUebersichtCH-2025.xlsx` | `48ba9c57…44de` | 2026-05-19 |

Full digests: `sha256sum data/raw/swissgrid/*.xlsx`.

- Sheets: `Einstellungen`, `Datetime`, `Uebersicht`, `Zeitreihen0h15` (+ `Zeitreihen1h00` in 2020–2022).
- `Zeitreihen0h15`: row 1 = bilingual header (`"German\nEnglish"`), row 2 = units, then data.
  65 columns identical (names and order) for 2020–2025. Energy columns in **kWh per 15 min**;
  4 control-energy price columns in EUR/MWh.
- Columns used: `Total energy consumed by end users in the Swiss controlblock`,
  `Total energy consumption Swiss controlblock`, `Total energy production Swiss controlblock`,
  `Cross Border Exchange {CH->X, X->CH}` for X in AT, DE, FR, IT, plus `Transit`, `Import`, `Export`.
  Cantonal production/consumption columns are available too.
- No nulls (2024, 2025 checked).
- **Time zone: Swiss local time (Europe/Zurich).** Spring forward skips the 02:xx labels; fall
  back repeats 02:00–02:45 in order (first CEST, then CET).
- **Labelling convention changes:**
  - 2020: Excel datetimes; 2021–2024: strings `dd.mm.yyyy HH:MM`. Both period **end**
    (`… 00:15` … next year `00:00`).
  - 2025: strings, period **start** (`01.01.2025 00:00` … `31.12.2025 23:45`, 35,040 rows).
- 2023 was re-published in March 2026, so files can be revised years later.

## MeteoSwiss SwissMetNet (STAC `ch.meteoschweiz.ogd-smn`, CC BY 4.0)

- Hourly file per station: `https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/<sta>/ogd-smn_<sta>_h_historical_2020-2029.csv`
  (`;`-separated, ASCII). The file is rewritten yearly (last update 2026-02-18) and now covers
  2020-01-01 → 2025-12-31 23:00 (52,608 rows for SMA: no gaps in timestamps).
- `reference_timestamp` is `dd.mm.yyyy HH:MM` **UTC**, labelled at **interval end**. Evidence:
  the radiation-weighted mean label hour is 11.99 UTC, against 11.93 expected for end labels at
  Zurich's solar noon (~11:26 UTC).
- `tre200h0` = air temperature 2 m, hourly mean, °C (33 nulls at SMA 2020–2025).
  `gre000h0` = global radiation, hourly mean, W/m².
- Station metadata `ogd-smn_meta_stations.csv` (latin-1): abbr, canton, coordinates.
  Candidates: SMA (ZH), BAS (BL/BS), BER (BE), GVE (GE), PUY (VD), LUG (TI), LUZ (LU),
  STG (SG), SIO (VS), CHU (GR).

## TimeNet

- Connector = package folder `packages/timenet-connectors/src/timenet_connectors/datasets/<org>/<name>/`
  with `connector.py`, `dataset.yaml`, `__init__.py`, optional `requirements.txt`, and
  `tests/` (fixture-based, no network).
- `download` = I/O only; source files are pinned by URL **and sha256** (`Artifact`). `convert` = CPU only.
- Every source file must be pinned. AGENTS.md: never fill or repair missing data; raise instead.
  Gaps go on the spec with `missing=MissingValues(...)`.
- `opentslm/sleep-cot` pattern: one `Record` per window, one `ClassificationTask` with
  `label_set`, `targets`, `rationale` and `split`. A rationale is the CoT text.
- Records can carry an absolute `start_time` (Unix µs), with `RegularAxis.from_rate_hz`.
- Valid card values exist: `domains: [energy, environment]` and `license: NONE`, meaning
  "terms unknown, not unrestricted". The docs say to check with the publisher before use.

## OpenTSLM

- Training repo: https://github.com/StanfordBDHG/OpenTSLM (`curriculum_learning.py`, stages 1–5).
- Smallest base models: `google/gemma-3-270m`, then `meta-llama/Llama-3.2-1B` (gated).
- Models: `OpenTSLMSP` (soft prompt, less VRAM) and `OpenTSLMFlamingo`.
- A dataset is a `QADataset` subclass: pre-prompt, a list of `TextTimeSeriesPrompt` (text plus
  z-normalised series, with mean/std stated in the text), post-prompt, and the answer (the rationale).
- OpenTSLM has no TimeNet reader, so we write one.
