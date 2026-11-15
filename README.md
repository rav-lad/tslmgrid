# Swiss Grid Anomaly-CoT

Explain anomalies in Swiss electricity consumption in natural language with a fine-tuned
time-series language model (OpenTSLM). The project also contributes the dataset
`aionic/swiss-grid-anomaly-cot` to TimeNet (TimeNet hackathon, Round 1).

Every label is computed by transparent rules from real public data. No label comes from an LLM.

## Pipeline (one command per step)

```bash
uv sync
uv run sgcot-download      # 19 source files, verified against sources.lock.json (sha256)
uv run sgcot-ingest        # data/processed/ch_hourly.parquet: 52,608 aligned UTC hours, 2020-2025
uv run sgcot-annotate      # baseline, anomalies, causes, weekly Q/A -> data/processed/annotations/
uv run sgcot-export        # OpenTSLM samples -> data/processed/opentslm/{train,validation,test}.jsonl
uv run sgcot-baselines     # non-learned baselines on validation and test
uv run sgcot-score --predictions <OpenTSLM test_predictions.jsonl> --name <system>   # score a model
uv run python demo/build_demo.py [--predictions <OpenTSLM test predictions>]   # demo/index.html
uv run pytest              # 28 tests: parsing, DST, alignment, leakage, number check, scoring
```

`uv sync` needs nothing but this repository. The TimeNet dataset is a separate step, run from a
clone of TimeNet in `ext/TimeNet` (branch `feature/swiss-grid-anomaly-cot`, or apply
`connector/timenet-swiss-grid-anomaly-cot.patch`):

```bash
uv run python scripts/sync_connector.py            # copy the pipeline into the TimeNet connector
# from ext/TimeNet:
PYTHONUTF8=1 uv run --no-sync timenet-build build aionic/swiss-grid-anomaly-cot --local-registry ../../scratch/registry
# from this repository, to export the samples as TimeNet publishes them instead of from windows.jsonl:
uv run --with-editable ext/TimeNet/packages/timenet sgcot-export --registry scratch/registry
```

`PYTHONUTF8=1` works around a Windows-only decoding bug in `timenet-build`'s isolated build.

## Fine-tuning and scoring

1. Clone OpenTSLM and apply `train/opentslm-stage6-swissgrid-cot.patch` (checked against OpenTSLM
   commit `2968f4b`). It adds the `stage6_swissgrid_cot` stage and `SwissGridCoTQADataset`.
2. Point `SWISSGRID_COT_DIR` at `data/processed/opentslm/`.
3. **Stage 6 starts from the stage 5 checkpoint.** OpenTSLM refuses to run it unless
   `results/<llm>/<model type>/stage5_ecg_cot/checkpoints/best_model.pt` and its `metrics.json`
   exist: train stages 1-5 first, or put a pretrained OpenTSLM checkpoint of the same base model and
   model type there. Early stopping is on validation loss (patience 5).
4. `uv run sgcot-score --predictions <results/.../stage6_swissgrid_cot/results/test_predictions.jsonl>`
   prints the model next to the baselines and writes `reports/eval/<name>_<split>.{json,md}`. Samples
   without a prediction count as wrong; an unknown or repeated `sample_id` is an error.

Caveats when reading the scores:

- The rationales quote numbers the inputs cannot give exactly (the expected load, z-scores, the
  weather effect, which come from the baseline). The model can only approximate them, so
  `hallucinated_number_rate` (exact match) is a ceiling. `ungrounded_number_rate_tol` accepts values
  within 2 % of a fact. Read both, and judge faithfulness on the cause and the days.
- The rolling train windows overlap by 6 days of 7: 4,365 train samples are worth about 208
  independent weeks. Watch the validation loss.
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

## Status (2026-11-12)

| Phase | State |
| --- | --- |
| 1 Explore | done |
| 2 Ingest | done, tested (DST, both label conventions, column mapping) |
| 3 Annotate | done, tested (leakage, rules, number check) |
| 4 TimeNet connector | builds in isolation and round-trips through the client; ruff, ty (3.13 and 3.11) and connector tests pass. Not yet committed or opened as a PR. |
| Training prep | export (4,365 train / 156 val / 156 test samples, no TimeNet needed), OpenTSLM stage 6 and dataset class, smoke-tested on CPU |
| Evaluation | metrics, non-learned baselines and `sgcot-score` for model predictions done; zero-shot LLM baseline and LLM judge need an API key |
| 5 Fine-tune | not started: needs a GPU, Hugging Face access to the base model and a stage 5 checkpoint (see above) |
| 6 Demo | `demo/index.html`, a self-contained page: week map, hourly charts with the expected daily mean and the anomalous days, the three explanations. It shows the model's answers once `--predictions` is passed. Not committed: it embeds Swissgrid data whose license is unknown. |

Baselines on the test year (2025), from `reports/eval/baselines.md`:

| system | cause acc. | cause macro-F1 | day F1 | exchange acc. |
| --- | --- | --- | --- | --- |
| majority | 0.846 | 0.306 | 0.000 | 0.462 |
| calendar rules (no load data) | 0.981 | 0.966 | 0.812 | 0.885 |

The causes are calendar rules and the prompt lists the holidays, so cause accuracy is nearly solved
by the calendar alone. The model has to add value in two places:

- **detecting the anomalous days**: the calendar baseline's day recall is 0.68;
- **quantifying them faithfully**: the share of outputs with hallucinated numbers.

The test year has only 8 weeks with an anomaly (20 days), so per-week metrics are noisy.

## Layout

```
src/swissgrid_cot/ingest/    parsing, alignment, weather, holidays (single source of truth)
src/swissgrid_cot/annotate/  baseline, anomalies, causes, rationales, weekly windows
src/swissgrid_cot/train/     OpenTSLM export
src/swissgrid_cot/eval/      metrics, baselines, scoring of model predictions
scripts/                     verification, connector sync, TimeNet build check
connector/                   patch of the TimeNet connector (also on ext/TimeNet branch)
train/                       patch of OpenTSLM stage 6 (also on ext/OpenTSLM branch)
reports/                     phase plots, samples, verification, baselines
```
