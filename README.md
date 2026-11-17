# Swiss Grid Anomaly-CoT

Explain anomalies in Swiss electricity consumption in natural language with a fine-tuned
time-series language model (OpenTSLM). The project also contributes the dataset
`scooby-team/swiss-grid-anomaly-cot` to TimeNet (TimeNet hackathon, Round 1).

Every label is computed by transparent rules from real public data. No label comes from an LLM.

## Pipeline (one command per step)

```bash
uv sync
uv run sgcot-download      # 19 source files, verified against sources.lock.json (sha256)
uv run sgcot-ingest        # data/processed/ch_hourly.parquet: 52,608 aligned UTC hours, 2020-2025
uv run sgcot-annotate      # baseline, anomalies, causes, weekly Q/A -> data/processed/annotations/
uv run sgcot-export --normal-stride 4   # OpenTSLM samples -> data/processed/opentslm/{train,validation,test}.jsonl
uv run sgcot-baselines     # non-learned baselines on validation and test
uv run sgcot-score --predictions <OpenTSLM test_predictions.jsonl> --name <system>   # score a model
uv run python demo/build_demo.py [--predictions <OpenTSLM test predictions>]   # demo/index.html
uv run pytest              # 31 tests: parsing, DST, alignment, leakage, number check, scoring, export
```

`uv sync` needs nothing but this repository. The TimeNet dataset is a separate step, run from a
clone of TimeNet in `ext/TimeNet` (branch `feature/swiss-grid-anomaly-cot` of
`rav-lad/TimeNet`, proposed upstream as [OpenTSLM/TimeNet#795](https://github.com/OpenTSLM/TimeNet/pull/795),
or apply `connector/timenet-swiss-grid-anomaly-cot.patch`):

```bash
uv run python scripts/sync_connector.py            # copy the pipeline into the TimeNet connector
# from ext/TimeNet:
PYTHONUTF8=1 uv run --no-sync timenet-build build scooby-team/swiss-grid-anomaly-cot --local-registry ../../scratch/registry
# from this repository, to export the samples as TimeNet publishes them instead of from windows.jsonl:
uv run --with-editable ext/TimeNet/packages/timenet sgcot-export --registry scratch/registry
```

`PYTHONUTF8=1` works around a Windows-only decoding bug in `timenet-build`'s isolated build.

## Fine-tuning and scoring

1. Clone OpenTSLM and apply `train/opentslm-stage6-swissgrid-cot.patch` (checked against OpenTSLM
   commit `2968f4b`). It adds the `stage6_swissgrid_cot` stage (half the CoT learning rates, 6
   epochs) and `SwissGridCoTQADataset`, and changes OpenTSLM in four places:
   - LoRA is enabled before the previous stage is loaded. Upstream enables it after, so the stage 5
     LoRA adapters are silently dropped (`Failed to load LoRA state from previous stage`).
   - Padding no longer counts in the loss.
   - The loss can be weighted: the answer tokens of the dates and of the final answer count
     `SWISSGRID_COT_DECISION_WEIGHT` times, the samples of windows with an anomaly
     `SWISSGRID_COT_ANOMALY_WEIGHT` times (both 1 by default; the validation loss is weighted the
     same way).
   - `OPENTSLM_SAVE_EVERY_EPOCH=1` keeps `epoch_N.pt` for every epoch, `OPENTSLM_SKIP_TEST_EVAL=1`
     skips the test evaluation after training, `SWISSGRID_COT_SEED` seeds the run.
2. Export with `uv run sgcot-export --normal-stride 4` and point `SWISSGRID_COT_DIR` at
   `data/processed/opentslm/`. The stride keeps the anomaly tasks of one in 4 rolling windows without
   an anomalous day, and the exchange task of all of them (2,823 train samples; 37 % of the anomaly
   samples have an anomaly, instead of 18 %). The exchange task also gets the net import over all
   borders, the hourly sum of the four borders.
3. **Stage 6 starts from the stage 5 checkpoint.** OpenTSLM refuses to run it unless
   `results/<llm>/<model type>/stage5_ecg_cot/checkpoints/best_model.pt` and its `metrics.json`
   exist: train stages 1-5 first, or put a pretrained OpenTSLM checkpoint of the same base model and
   model type there. For Llama 3.2 1B with OpenTSLMSP, the folder is
   `results/Llama_3_2_1B/OpenTSLMSP/`, and `model_checkpoint.pt` from `OpenTSLM/llama-3.2-1b-ecg-sp`
   works as `best_model.pt` (a `metrics.json` holding `{}` is enough).
4. Train with `OPENTSLM_SAVE_EVERY_EPOCH=1 OPENTSLM_SKIP_TEST_EVAL=1`, then select the epoch on the
   validation day F1 and write its test predictions with `train/select_epoch.py` (run from the
   OpenTSLM checkout; its docstring has the command). **Do not select on the validation loss**: it is
   dominated by the template tokens, and the epoch it picks ranged from test day F1 0.18 to 0.74.
5. `uv run sgcot-score --predictions <test_predictions.jsonl> --name <system>` prints the model next
   to the baselines and writes `reports/eval/<name>_<split>.{json,md}`. Samples without a prediction
   count as wrong; an unknown or repeated `sample_id` is an error.

Caveats when reading the scores:

- The rationales quote numbers the inputs cannot give exactly (the expected load, z-scores, the
  weather effect, which come from the baseline). The model can only approximate them, so
  `hallucinated_number_rate` (exact match) is a ceiling. `ungrounded_number_rate_tol` accepts values
  within 2 % of a fact. Read both, and judge faithfulness on the cause and the days.
- The rolling train windows overlap by 6 days of 7: the train samples are worth about 208
  independent weeks. The validation loss is lowest after 2 to 4 epochs.
- The test year holds 3 of the 9 causes (`none`, `public_holiday`, `christmas_newyear`), and no
  ISO week has `bridge_day` as its label in any split.

## Data

| Source | What | License |
| --- | --- | --- |
| Swissgrid, Energy Statistic Switzerland 2020-2025 | Quarter-hourly consumption, production, cross-border exchange (kWh) | **None stated**: the card says `NONE`. Terms are being confirmed with Swissgrid. |
| MeteoSwiss SwissMetNet (12 stations) | Hourly temperature and global radiation | CC BY 4.0 |
| BFS STATPOP 2023 | Population per canton (weights) | Open data |
| `holidays` 0.108 | Cantonal public holidays | MIT |

Time handling, checked on the real files (see `docs/phase1_exploration.md`):

- Swissgrid writes Swiss civil time. In 2020-2024 each label is the **end** of its quarter hour; in
  2025 it is the **start**. 2020 writes the fall-back instant as 03:00 CEST; 2021-2024 write it as
  02:00 CET.
- MeteoSwiss writes UTC, labelled at the end of each hour.
- Everything is stored as UTC hour starts. Every label is checked, so a missing row fails the build.

The data's authenticity is verified against independent references in `reports/data_verification.md`:

- Swissgrid's own annual totals match to 1e-15 for 2021-2025.
- Energy-Charts / ENTSO-E: net import r = 0.99; load r = 1.000 in 2020 and 2022.
- MeteoSwiss's own daily means match to 0.03 °C on average.

## Annotation

- **Baseline:** a daily linear model (weekday type × month, heating and cooling degree days, lagged
  heating degree days, radiation, trend), fitted on the ordinary days of 2020-2023 only. MAPE on
  ordinary days is 2.3 % in train and 2.3 % in the 2025 test year.
- **Anomaly:** a day is anomalous when its robust z-score is at least 3 in absolute value, with the
  scale taken from the train fit days. This flags 91 % of holidays and 0.6 % of ordinary train days.
- **Causes**, by ordered rules: `covid_lockdown`, `christmas_newyear` (22 Dec - 6 Jan),
  `public_holiday` (holiday for at least 20 % of the population), `bridge_day`, `summer_holidays`
  (14 Jul - 15 Aug).
  - No day in 2020-2025 lies above expectation, so `cold_snap`, `heatwave` and `unexplained` never
    occur. The weather effect is stated in every rationale instead.
  - The two holiday-period rules were motivated by unexplained train days (3 Jan 2020, 3-4 Jan 2023,
    late July 2023). They were written after all years had been inspected.
- **Q/A:** ISO weeks with 3 tasks each: cause (classification), anomalous days (localization), and
  net importer or exporter (answer). Rationales come from templates and are number-checked against
  the facts.
- **Splits:** 208 train weeks (2020-2023), 52 validation (2024), 52 test (2025). The train split is
  augmented with 7-day windows starting on every day (1,455 windows, all inside 2020-2023).

## Status (2026-11-17)

| Phase | State |
| --- | --- |
| 1 Explore | done |
| 2 Ingest | done, tested (DST, both label conventions, column mapping) |
| 3 Annotate | done, tested (leakage, rules, number check) |
| 4 TimeNet connector | `scooby-team/swiss-grid-anomaly-cot`, opened as [OpenTSLM/TimeNet#795](https://github.com/OpenTSLM/TimeNet/pull/795) (awaiting review). ruff, ty (3.13 and 3.11), pre-commit, `make test`, `make test-connectors` and `make license-check` pass. A full `timenet-build build` from the PR commit downloads the sources, builds in about a minute and reads back 312 records (9 signals each) and 936 tasks. |
| Training prep | export (2,823 train with `--normal-stride 4`, 4,365 without / 156 val / 156 test samples, no TimeNet needed), OpenTSLM stage 6, dataset class and epoch selection |
| Evaluation | metrics, non-learned baselines and `sgcot-score` for model predictions done; zero-shot LLM baseline and LLM judge need an API key |
| 5 Fine-tune | Llama 3.2 1B, OpenTSLMSP, 1 L40S, 6 runs (below). The model beats the baselines on the exchange task, not on the anomalous days |
| 6 Demo | `demo/index.html`, a self-contained page: week map, hourly charts with the expected daily mean and the anomalous days, the three explanations. It shows the model's answers once `--predictions` is passed. Not committed: it embeds Swissgrid data whose license is unknown. |

### Results on the test year (2025)

Baselines from `reports/eval/baselines.md`, models from `reports/eval/opentslm-sp-1b-run*_test.md`.
Runs 1 to 5 kept the epoch of lowest validation loss; run 6 selected it on the validation day F1.

| system | changes | cause acc. | cause macro-F1 | day F1 | day recall | exchange acc. |
| --- | --- | --- | --- | --- | --- | --- |
| majority | | 0.846 | 0.306 | 0.000 | 0.000 | 0.462 |
| calendar rules (no load data) | | **0.981** | **0.966** | **0.812** | 0.684 | 0.885 |
| run 1 | plain, stage 5 learning rates | 0.962 | 0.619 | 0.400 | 0.263 | **1.000** |
| run 2 | LoRA fix, stride 4, halved rates | **0.981** | 0.929 | 0.737 | 0.737 | 0.846 |
| run 3 | + weighted loss (5, 2), exchange on every window | **0.981** | **0.971** | 0.682 | **0.789** | 0.769 |
| run 4 | weights (2, 2), stage 5 rates, total net import | 0.577 | 0.734 | 0.375 | 0.316 | **1.000** |
| run 5 | weights (2, 2), halved rates, total net import | 0.865 | 0.512 | 0.178 | 0.737 | **1.000** |
| **run 6, seed 1** | plain, halved rates, epoch selected on validation | 0.942 | 0.881 | 0.703 | 0.684 | **1.000** |
| run 6, seed 2 | same, other seed (validation day F1 0.714 < 0.732) | 0.962 | 0.937 | 0.414 | 0.316 | **1.000** |

Run 6 seed 1 is the model chosen without looking at the test (best validation day F1 of the two
seeds). What the runs show:

- **Exchange is solved** once the net import over all borders is an input (1.000 in four models,
  against 0.885 for the rules).
- **The anomalous days are not.** No run beats the calendar's day F1. The anomalies of 2020-2025
  are all calendar effects and the prompt lists the holidays, so the calendar starts with most of
  the answers: it misses 6 of the 19 test days and names no wrong one. The models find some of those
  6 (30-31 Dec, 2-3 Jan, the days after Christmas) but add false ones: the weekend after a holiday,
  and cantonal holidays observed by under 20 % of the population (Corpus Christi, 15 Aug, 1 Nov,
  8 Dec), which do not lower the national load enough.
- **The metric is noisy.** The test year has 8 weeks with an anomaly (19 days). The two run 6 seeds
  score 0.73 and 0.71 on validation and 0.70 and 0.41 on test.
- Halving the learning rates is what keeps the cause and days tasks stable; with the stage 5 rates
  and a weighted loss the cause task collapsed (run 4). Weighting the decision tokens by 5 raised the
  recall and the false positives together.
- Numbers are approximated, not copied: `ungrounded_number_rate_tol` stays at 0.6-0.9.

## Layout

```
src/swissgrid_cot/ingest/    parsing, alignment, weather, holidays (single source of truth)
src/swissgrid_cot/annotate/  baseline, anomalies, causes, rationales, weekly windows
src/swissgrid_cot/train/     OpenTSLM export
src/swissgrid_cot/eval/      metrics, baselines, scoring of model predictions
scripts/                     verification, connector sync, TimeNet build check
connector/                   patch of the TimeNet connector (also on ext/TimeNet branch)
train/                       patch of OpenTSLM stage 6 (also on ext/OpenTSLM branch), epoch selection
reports/                     phase plots, samples, verification, baselines
```
