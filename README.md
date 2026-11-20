# Swiss Load Alert Review

When Swiss electricity demand leaves its expected level, an analyst has to decide whether the day
deserves an investigation. This project flags those days, reviews each alert at hourly resolution,
and has a fine-tuned time-series language model (OpenTSLM) read the day's curve and write the
review.

- **User:** an electricity demand analyst reviewing yesterday's Swiss load.
- **Decision:** close the alert as consistent with the weather and calendar, or investigate a
  specific period.
- **Flow:** a daily detector flags the day → the hourly review compares its 24 hours with earlier
  comparable days and gives the verdict → the model reads the curve and writes the review, with the
  hours and the size of the gap → the demo shows it on a 3D map of the country.

The project also contributes the dataset `scooby-team/swiss-grid-anomaly-cot` to TimeNet (TimeNet
hackathon, Round 1). Every label is computed by transparent rules from real public data. No label
comes from an LLM.

## Demo

`demo/index.html` is a 3D relief map of Switzerland, one day at a time (2025-2026), hour by hour.
Columns stand where people live (H3 cells of about 5 km², Kontur population). Their height and colour
show how far the consumption of their Swissgrid canton zone sits from a normal day at the same hour:
a national holiday lowers the whole country, a cantonal one lowers only the cantons that observe it
(Assumption, 15 August 2025: Lucerne −22 %, Ticino −17 %, Bern +9 %). A calendar picks the day; the
right panel says whether the detector flagged it, gives the review's verdict, and shows the model's
written review of a flagged day.

```bash
uv run sgcot-ingest-zones
uv run python demo/build_demo.py --predictions <test predictions> <all-days predictions>
```

The page is not committed: it embeds Swissgrid data, whose license is unknown. For the model's
review of every 2025-2026 day, run `sgcot-review-export --all-days 2025 2026` and `train/predict.py`
on `data/processed/opentslm_review_days/`.

## Pipeline

```bash
uv sync
uv run sgcot-download                 # 19 source files, verified against sources.lock.json (sha256)
uv run sgcot-download --holdout       # the 2026 files (Swissgrid to 31 Oct, MeteoSwiss to yesterday)
uv run sgcot-ingest                   # data/processed/ch_hourly.parquet: 52,608 aligned UTC hours, 2020-2025
uv run sgcot-ingest-holdout           # data/processed/ch_hourly_holdout.parquet: 2026
uv run sgcot-annotate                 # daily baseline, detector, causes -> data/processed/annotations/
uv run sgcot-review                   # hourly review of every day -> data/processed/review/, reports/review/summary.md
uv run sgcot-review-export            # OpenTSLM review samples -> data/processed/opentslm_review/
uv run sgcot-review-score [--predictions <test_predictions.jsonl> --name <system>]   # -> reports/review_eval/
uv run pytest
```

## How an alert is reviewed

The daily detector flags a day when its robust z-score against the daily baseline is at least 3
(see Annotation). The daily baseline already holds weekday, month, weather and trend. The hourly
review adds what a daily total cannot show: the shape of the day (does a partial holiday move the
morning toward a Sunday profile?), whether the day matches earlier days of comparable weather, and
whether a residual stays in a few hours after that comparison.

- **References come from earlier days only** (`src/swissgrid_cot/review/references.py`): same
  weekday type, within 28 days of the date in earlier years or the previous 42 days, daily mean
  temperature within 3 °C; earlier Christmas or summer holidays for days inside them; earlier full
  holidays, bridge days. A partial holiday blends the ordinary and the full-holiday reference by the
  share of the population on holiday. Each reference is scaled by the day's baseline expectation and
  corrected for the baseline's slow drift.
- **Verdict** (`src/swissgrid_cot/review/assess.py`): anomaly when the day-level residual reaches 3
  spreads or a run of 3+ hours lies beyond 3 hourly spreads (spreads measured on 2021-2023, per
  context group); not sure when fewer than 3 (5 for ordinary days) comparable earlier days exist;
  normal otherwise.
- Each review reports the hours, the residual, the MWh, the comparison used and one next check
  (metering completeness and incident logs for a short window, a closure or event missing from the
  calendar for a broad one, refitting the baseline when it drifts).

## Results

**Splits.** Train 2020-2023, validation 2024 (epoch selection), test 2025, holdout 2026
(January-October, never inspected while the review was designed).

Flagged days (|z| >= 3) by verdict (`reports/review/summary.md`):

| split | normal | anomaly | not sure |
| --- | --- | --- | --- |
| train 2020-2023 | 41 | 3 | 55 (the 2020 lockdown and early 2020 lack history) |
| validation 2024 | 20 | 3 | 0 |
| test 2025 | 17 | 3 | 0 |
| holdout 2026 | 6 | 5 | 0 |

The five 2026 anomalies lie above expectation, which no day of 2020-2025 did: 10-11 January (+11 %
and +9 % over comparable weekend days), Good Friday (+7 %), 1 July (+7 %, 04:00-13:59) and
25 October (+8 %, a Sunday shaped like a Saturday).

**Model.** OpenTSLM stage 6 (Llama 3.2 1B, SP) fine-tuned on 1,402 review samples of 2020-2023: real
days and simulated deviations (a real normal day with a deviation added to some hours, labelled by
the same rules). It receives the day's curve, the comparable days and the calendar, and writes the
review. Epoch selected on 2024 (validation score 0.776). On the 2026 holdout
(`reports/review_eval/opentslm-review-1b_test.md`):

| cases (n) | hours under review, F1 | day-level residual, MAE (pp) |
| --- | --- | --- |
| flagged days (11) | 0.762 | 0.78 |
| near-alerts, \|z\| between 2 and 3 (36) | 0.529 | 0.58 |
| simulated deviations (71) | 0.722 | 0.98 |

- The model reads from the curve the hours that warrant review: the calendar and the daily z-score
  in its prompt never name hours.
- It measures the day-level residual against the comparable days to within one percentage point.
- On near-alerts, days just below the detector's threshold, its verdict is right in 89 % of cases,
  against 31 % for a system that reads only the context in the prompt.

## To improve

- **Recall on deviations:** the model finds half of the simulated deviations (precision 0.97). More
  simulated days, and a loss weighted toward the verdict, are the next levers.
- **Following the curve:** when an alert receives the curve of another alert in the same calendar
  context, the review should change with the curve; it does in about half of the cases. Training
  pairs that differ only by their curve target this directly.
- **Short windows:** a deviation confined to 2-3 hours is harder to localize than a day-level gap.
- **Labels from analysts:** the reviews are rule-made; days judged by analysts would let the model
  learn what the rules cannot write down.
- **Regional review:** the map already shows the 18 Swissgrid canton zones; the review could run per
  zone, with cantonal holidays as context.

## Fine-tuning

1. Clone OpenTSLM and apply `train/opentslm-stage6-swissgrid-cot.patch` (checked against OpenTSLM
   commit `2968f4b`). It adds the `stage6_swissgrid_cot` stage and `SwissGridCoTQADataset`, which
   reads any `{train,validation,test}.jsonl` of `pre_prompt, series, post_prompt, answer` samples
   from `SWISSGRID_COT_DIR`. It also changes OpenTSLM in four places:
   - LoRA is enabled before the previous stage is loaded. Upstream enables it after, so the stage 5
     LoRA adapters are silently dropped (`Failed to load LoRA state from previous stage`).
   - Padding no longer counts in the loss.
   - The loss can be weighted (`SWISSGRID_COT_DECISION_WEIGHT`, `SWISSGRID_COT_ANOMALY_WEIGHT`, both 1
     by default).
   - `OPENTSLM_SAVE_EVERY_EPOCH=1` keeps `epoch_N.pt` for every epoch, `OPENTSLM_SKIP_TEST_EVAL=1`
     skips the test evaluation after training, `SWISSGRID_COT_SEED` seeds the run.
2. **Stage 6 starts from the stage 5 checkpoint.** For Llama 3.2 1B with OpenTSLMSP, put
   `model_checkpoint.pt` from `OpenTSLM/llama-3.2-1b-ecg-sp` at
   `results/Llama_3_2_1B/OpenTSLMSP/stage5_ecg_cot/checkpoints/best_model.pt`, with a
   `results/metrics.json` holding `{}` next to it.
3. Point `SWISSGRID_COT_DIR` at `data/processed/opentslm_review/` and train with
   `OPENTSLM_SAVE_EVERY_EPOCH=1 OPENTSLM_SKIP_TEST_EVAL=1`
   (`curriculum_learning.py --model OpenTSLMSP --llm_id meta-llama/Llama-3.2-1B --stages stage6_swissgrid_cot`).
   About 20 minutes on one L40S.
4. Select the epoch on validation and write the test predictions with `train/select_epoch.py
   --max-new-tokens 400` (run from the OpenTSLM checkout). `train/predict.py` generates the
   predictions of one checkpoint on any sample folder, on GPU or CPU (about 15 s per sample on 16
   cores).
5. `uv run sgcot-review-score --predictions <test_predictions.jsonl> --name <system>`.

## Data

| Source | What | License |
| --- | --- | --- |
| Swissgrid, Energy Statistic Switzerland 2020-2026 | Quarter-hourly national consumption, cross-border exchange and the consumption of 18 canton zones (kWh) | **None stated**: the card says `NONE`. Swissgrid publishes the files openly without license terms; the raw data is not redistributed here (the build downloads it). |
| MeteoSwiss SwissMetNet (12 stations) | Hourly temperature and global radiation | CC BY 4.0 |
| BFS STATPOP 2023 | Population per canton (weights) | Open data |
| `holidays` 0.108 | Cantonal public holidays | MIT |
| Kontur Population 2023 (demo) | Population per H3 cell (resolution 8) | CC BY 4.0 |
| FSO generalized boundaries 2021, via `swiss-maps` 4.5.0 (demo) | Country, canton and lake outlines | FSO open data, with attribution |

Time handling, checked on the real files (see `docs/phase1_exploration.md`):

- Swissgrid writes Swiss civil time. In 2020-2024 each label is the **end** of its quarter hour; in
  2025 and 2026 it is the **start**. 2020 writes the fall-back instant as 03:00 CEST; 2021-2024 write
  it as 02:00 CET. 2026 is published up to the end of a month; its rows are checked like a complete
  year up to their last whole local day.
- MeteoSwiss writes UTC, labelled at the end of each hour. The current year sits in a separate
  `recent` file, with fewer quality checks than the historical one.
- Everything is stored as UTC hour starts. Every label is checked, so a missing row fails the build.
  The review reads each day as 24 local hours (the spring-forward 02:00 is interpolated, the two
  fall-back 02:00 hours are averaged).

The data's authenticity is verified against independent references in `reports/data_verification.md`:
Swissgrid's own annual totals match to 1e-15 for 2021-2025; Energy-Charts / ENTSO-E net import
r = 0.99 and load r = 1.000 in 2020 and 2022; MeteoSwiss's own daily means match to 0.03 °C on average.

## Annotation

- **Baseline:** a daily linear model (weekday type × month, heating and cooling degree days, lagged
  heating degree days, radiation, trend), fitted on the ordinary days of 2020-2023 only. MAPE on
  ordinary days is 2.3 % in train and 2.3 % in the 2025 test year.
- **Detector:** a day is flagged when its robust z-score is at least 3 in absolute value, with the
  scale taken from the train fit days. This flags 91 % of holidays and 0.6 % of ordinary train days.
- **Causes**, by ordered rules: `covid_lockdown`, `christmas_newyear` (22 Dec - 6 Jan),
  `public_holiday` (holiday for at least 20 % of the population), `bridge_day`, `summer_holidays`
  (14 Jul - 15 Aug).
- **Weekly Q/A (the TimeNet dataset):** ISO weeks with 3 tasks each: cause, anomalous days, and net
  importer or exporter. Rationales come from templates and are number-checked against the facts.
  208 train weeks (2020-2023), 52 validation (2024), 52 test (2025).

## TimeNet dataset

Built from a clone of TimeNet in `ext/TimeNet` (branch `feature/swiss-grid-anomaly-cot` of
`rav-lad/TimeNet`, proposed upstream as [OpenTSLM/TimeNet#795](https://github.com/OpenTSLM/TimeNet/pull/795),
or apply `connector/timenet-swiss-grid-anomaly-cot.patch`):

```bash
uv run python scripts/sync_connector.py            # copy the pipeline into the TimeNet connector
# from ext/TimeNet:
PYTHONUTF8=1 uv run --no-sync timenet-build build scooby-team/swiss-grid-anomaly-cot --local-registry ../../scratch/registry
```

`PYTHONUTF8=1` works around a Windows-only decoding bug in `timenet-build`'s isolated build. ruff,
ty (3.13 and 3.11), pre-commit, `make test`, `make test-connectors` and `make license-check` pass on
the PR; a full build reads back 312 records (9 signals each) and 936 tasks.

## Layout

```
src/swissgrid_cot/ingest/    parsing, alignment, weather, holidays, 2026 holdout, canton zones
src/swissgrid_cot/annotate/  daily baseline, detector, causes, rationales, weekly windows (TimeNet)
src/swissgrid_cot/review/    hourly alert review: references, verdicts, OpenTSLM samples, scoring
demo/                        build_demo.py + template.html -> index.html (not committed)
train/                       OpenTSLM stage 6 patch, epoch selection, prediction
scripts/                     data verification, connector sync, TimeNet build check
connector/                   patch of the TimeNet connector
reports/                     review summary and scores, data verification
```
