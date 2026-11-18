# Weekly model input ablation (run 6, seed 1)

Checkpoint: stage 6 run 6, seed 1, `epoch_5.pt`. Samples: the 52 `anomaly_days` samples of 2025
(19 anomalous days). Inference on CPU; the first 16 answers match the GPU predictions exactly, and
the CPU run scores 0.732 where the GPU run scored 0.703, so variants are compared with the CPU run.

| Variant | Inputs | Day F1 |
| --- | --- | --- |
| original | true prompt, true curve | 0.732 (tp 15, fp 7, fn 4) |
| holidays masked | prompt says no holiday, true curve | 0.000 (tp 0, fp 0, fn 19) |
| curve swapped, scored on the prompt's week | true prompt, curve of the week 4 weeks later | 0.737 (tp 14, fp 5, fn 5) |
| curve swapped, scored on the curve's week | same | 0.053 (tp 1, fp 18, fn 18) |

The model localizes anomalous days from the holiday list in its prompt. Without it, it finds none,
including the 20 % drop of New Year's Day. With another week's curve, it still answers the prompt's
week. A mismatched prompt and curve is itself an unusual input, so the swap alone would be weak
evidence; together with the masked variant, both point the same way.

Reproduce: `scripts/weekly_input_ablation.py variants`, `train/predict.py` per variant (from an
OpenTSLM checkout), `scripts/weekly_input_ablation.py score`.
