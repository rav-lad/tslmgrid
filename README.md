# Swiss Load Alert Review

Review Swiss electricity demand alerts at hourly resolution. A daily detector flags a day whose load
leaves the weather- and calendar-adjusted expectation; the review compares the day's 24 local hours
with earlier comparable days and answers: **anomaly** (a deviation remains, in which hours),
**normal** (the weather and calendar explain it), or **not sure** (too few comparable days). A
fine-tuned time-series language model (OpenTSLM) writes the review of each day.

The project also contributes the dataset `scooby-team/swiss-grid-anomaly-cot` to TimeNet (TimeNet
hackathon, Round 1). Every label is computed by transparent rules from real public data. No label
comes from an LLM.

- **User:** an electricity demand analyst reviewing yesterday's Swiss load deviations.
- **Decision:** close the alert as consistent with the weather and calendar evidence, or investigate
  a specific period.
- **Scope:** Swiss national end-user load (the repo has no verified regional load), Swiss local time
  for hours and calendar, UTC for alignment.

## Pipeline

```bash
uv sync
uv run sgcot-download                 # 19 source files, verified against sources.lock.json (sha256)
uv run sgcot-download --holdout       # the 2026 files (Swissgrid to 31 Oct, MeteoSwiss to yesterday)
uv run sgcot-ingest                   # data/processed/ch_hourly.parquet: 52,608 aligned UTC hours, 2020-2025
uv run sgcot-ingest-holdout           # data/processed/ch_hourly_holdout.parquet: 2026
uv run sgcot-annotate                 # daily baseline, anomalies, causes, weekly Q/A -> data/processed/annotations/
uv run sgcot-review                   # hourly review of every day -> data/processed/review/, reports/review/summary.md
uv run sgcot-review-export            # OpenTSLM review samples -> data/processed/opentslm_review/
uv run sgcot-review-score [--predictions <test_predictions.jsonl> --name <system>]   # -> reports/review_eval/
uv run python demo/build_demo.py --predictions <test predictions> [<all-days predictions>] --name <system>
uv run pytest                         # 41 tests
```

`demo/index.html` is a self-contained page: a 2020-2026 week grid coloured anomaly / normal / not
sure; each week opens its 7 days of load against the comparable days, each day its review and the
model's written review (2025-2026). It is not committed: it embeds Swissgrid data whose license is
unknown. For the model on every 2025-2026 day, run `sgcot-review-export --all-days 2025 2026` and
`train/predict.py` on `data/processed/opentslm_review_days/`.

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
  corrected for the baseline's slow drift (the baseline, fitted on 2020-2023, runs 6 % low over
  January 2026).
- **Verdict** (`src/swissgrid_cot/review/assess.py`): anomaly when the day-level residual reaches 3
  spreads or a run of 3+ hours lies beyond 3 hourly spreads (spreads measured on 2021-2023, per
  context group); not sure when fewer than 3 (5 for ordinary days) comparable earlier days exist;
  normal otherwise. Only a flagged day can be an anomaly or not sure; in the demo every other day is
  normal.
- Each review reports the hours, the residual, the MWh, the comparison used and one next check
  (metering completeness and incident logs for a short window, a closure or event missing from the
  calendar for a broad one, refitting the baseline when it drifts). No incident is presented as
  confirmed: the repo has no incident source.

## Results

**Splits.** Train 2020-2023, validation 2024 (epoch selection), test 2025 (exploratory: its alerts
were inspected while the review was designed), holdout 2026 (January-October, never inspected).
TimeNet and the weekly tasks stay on 2020-2025, and the modules copied into the TimeNet connector are
unchanged.

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

**Model.** OpenTSLM stage 6 (Llama 3.2 1B, SP) trained on 1,402 review samples of 2020-2023: real days
and simulated deviations (a real normal day with a deviation added to some hours, labelled by the same
rules and marked simulated). Epoch selected on 2024 (validation score 0.776, epoch 6). Scores
(`reports/review_eval/opentslm-review-1b_test.md`):

| cases (n) | system | verdict acc. | anomaly precision / recall | hours F1 | residual MAE (pp) |
| --- | --- | --- | --- | --- | --- |
| 2026 flagged (11) | context only | **0.909** | 1.00 / 0.80 | 0 | - |
| | model | 0.818 | 0.80 / 0.80 | **0.762** | 0.78 |
| 2026 near-alerts (36) | context only | 0.306 | 0.22 / 1.00 | 0 | - |
| | model | **0.889** | 0.64 / 1.00 | **0.529** | 0.58 |
| 2026 simulated (71) | context only | 0.521 | 0.93 / 0.45 | 0 | - |
| | model | 0.577 | 0.97 / 0.50 | **0.722** | 0.98 |
| 2026 curve swap (30) | context only | 0.867 | 1.00 / 0.71 | 0 | - |
| | model | 0.833 | 0.91 / 0.71 | 0.689 | 0.70 |
| 2025 flagged (20, exploratory) | context only | 0.800 | 0.00 / 0.00 | 0 | - |
| | model | 0.800 | 0.00 / 0.00 | 0 | 0.56 |

- **Hourly rules** score 1.000 everywhere by construction: the reference answers are their output.
  They are the product baseline.
- **Context only** sees what the prompt states (calendar, daily z-score) and never the curve; it
  answers the train majority of its context cell and never names hours.
- **Curve swap**: an alert keeps its text and references and receives the curve of another alert in
  the same calendar context. An answer that follows the curve changes with it.
- **What the model adds:** it reads from the curve the hours that warrant review, which the context
  alone cannot give, and the day-level residual to within about 1 point; it beats the context on
  near-alerts.
- **Where it falls short:** it is conservative (it finds 50 % of the 2026 and 39 % of the 2025
  simulated deviations, with few false alarms), misses the 3 anomalies among the 2025 flagged days,
  rarely gets the part of the day right, and in the curve swap its verdict follows the new curve in
  56 % (2026) and 45 % (2025) of the changed cases. The rules decide; the model writes the review.

## Why not the weekly model

The project first asked the model to find the anomalous days of a week from its curve and a prompt
listing the holidays. Six stage 6 runs never beat the calendar alone on day F1 (best 0.737 against
0.812, test 2025; `reports/eval/`). An input ablation on the selected model (run 6, seed 1, 52 test
weeks; `reports/eval/ablation_run6_seed1.md`, `scripts/weekly_input_ablation.py`) shows why:

| Variant | Day F1 |
| --- | --- |
| original prompt and curve | 0.732 |
| prompt says no holiday, true curve | **0.000** (none of the 19 days found) |
| true prompt, curve of another week, scored on the prompt's week | 0.737 |
| same, scored on the curve's week | **0.053** |

The weekly model read the holiday list, not the curve. Hence the split: the detector flags, the
review reads the hours, and the questions have answers that only the curve holds.

Weekly results on 2025 (baselines `reports/eval/baselines.md`, models `reports/eval/opentslm-sp-1b-run*_test.md`):

| system | changes | cause acc. | cause macro-F1 | day F1 | exchange acc. |
| --- | --- | --- | --- | --- | --- |
| calendar rules (no load data) | | **0.981** | **0.966** | **0.812** | 0.885 |
| run 2 | LoRA fix, stride 4, halved rates | **0.981** | 0.929 | 0.737 | 0.846 |
| run 3 | + weighted loss (5, 2) | **0.981** | **0.971** | 0.682 | 0.769 |
| run 6, seed 1 | plain, halved rates, epoch selected on validation | 0.942 | 0.881 | 0.703 | **1.000** |

The exchange task (net importer or exporter) is solved once the net import over all borders is an
input. Selecting the epoch on the validation loss is unreliable: the loss is dominated by template
tokens, and the epoch it picked ranged from test day F1 0.18 to 0.74.

## Fine-tuning

1. Clone OpenTSLM and apply `train/opentslm-stage6-swissgrid-cot.patch` (checked against OpenTSLM
   commit `2968f4b`). It adds the `stage6_swissgrid_cot` stage (half the CoT learning rates, 6
   epochs) and `SwissGridCoTQADataset`, which reads any `{train,validation,test}.jsonl` of
   `pre_prompt, series, post_prompt, answer` samples from `SWISSGRID_COT_DIR`. It also changes
   OpenTSLM in four places:
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
4. Select the epoch on validation and write the test predictions:
   `train/select_epoch.py --task alert_review --max-new-tokens 400` (run from the OpenTSLM checkout).
   `train/predict.py` generates the predictions of one checkpoint on any sample folder, on GPU or CPU
   (about 15 s per sample on 16 cores).
5. `uv run sgcot-review-score --predictions <test_predictions.jsonl> --name <system>`.

The weekly task trains the same way from `sgcot-export --normal-stride 4` (`data/processed/opentslm/`),
selected with `select_epoch.py` (day F1) and scored with `sgcot-baselines` and `sgcot-score`.

## Data

| Source | What | License |
| --- | --- | --- |
| Swissgrid, Energy Statistic Switzerland 2020-2026 | Quarter-hourly consumption, production, cross-border exchange (kWh) | **None stated**: the card says `NONE`. Terms are being confirmed with Swissgrid. |
| MeteoSwiss SwissMetNet (12 stations) | Hourly temperature and global radiation | CC BY 4.0 |
| BFS STATPOP 2023 | Population per canton (weights) | Open data |
| `holidays` 0.108 | Cantonal public holidays | MIT |

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
- **Anomaly (the daily detector):** a day is flagged when its robust z-score is at least 3 in
  absolute value, with the scale taken from the train fit days. This flags 91 % of holidays and
  0.6 % of ordinary train days.
- **Causes**, by ordered rules: `covid_lockdown`, `christmas_newyear` (22 Dec - 6 Jan),
  `public_holiday` (holiday for at least 20 % of the population), `bridge_day`, `summer_holidays`
  (14 Jul - 15 Aug). The two holiday-period rules were written after all years had been inspected.
- **Weekly Q/A (the TimeNet dataset):** ISO weeks with 3 tasks each: cause, anomalous days, and net
  importer or exporter. Rationales come from templates and are number-checked against the facts.
  208 train weeks (2020-2023, augmented with 1,455 rolling windows), 52 validation (2024), 52 test (2025).

## TimeNet dataset

Built from a clone of TimeNet in `ext/TimeNet` (branch `feature/swiss-grid-anomaly-cot` of
`rav-lad/TimeNet`, proposed upstream as [OpenTSLM/TimeNet#795](https://github.com/OpenTSLM/TimeNet/pull/795),
or apply `connector/timenet-swiss-grid-anomaly-cot.patch`):

```bash
uv run python scripts/sync_connector.py            # copy the pipeline into the TimeNet connector
# from ext/TimeNet:
PYTHONUTF8=1 uv run --no-sync timenet-build build scooby-team/swiss-grid-anomaly-cot --local-registry ../../scratch/registry
# from this repository, to export the weekly samples as TimeNet publishes them:
uv run --with-editable ext/TimeNet/packages/timenet sgcot-export --registry scratch/registry
```

`PYTHONUTF8=1` works around a Windows-only decoding bug in `timenet-build`'s isolated build. ruff,
ty (3.13 and 3.11), pre-commit, `make test`, `make test-connectors` and `make license-check` pass on
the PR; a full build reads back 312 records (9 signals each) and 936 tasks.

## Layout

```
src/swissgrid_cot/ingest/    parsing, alignment, weather, holidays, 2026 holdout
src/swissgrid_cot/annotate/  daily baseline, detector, causes, rationales, weekly windows (TimeNet)
src/swissgrid_cot/review/    hourly alert review: references, verdicts, OpenTSLM samples, scoring
src/swissgrid_cot/train/     weekly OpenTSLM export
src/swissgrid_cot/eval/      weekly metrics, baselines, scoring
demo/                        build_demo.py + template.html -> index.html (not committed)
train/                       OpenTSLM stage 6 patch, epoch selection, prediction
scripts/                     data verification, connector sync, TimeNet build check, weekly ablation
connector/                   patch of the TimeNet connector
reports/                     review summary and scores, weekly scores and ablation, verification
```
