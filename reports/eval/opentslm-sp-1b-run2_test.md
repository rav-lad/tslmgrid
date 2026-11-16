| split | system | cause_accuracy | cause_macro_f1 | window_anomaly_f1 | day_precision | day_recall | day_f1 | exchange_accuracy | parsable_rate | hallucinated_number_rate | ungrounded_number_rate_tol |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | oracle (gold rationale) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| test | majority | 0.846 | 0.306 | 0.000 | 0.000 | 0.000 | 0.000 | 0.462 | 1.000 | 0.000 | 0.000 |
| test | calendar rules (no load data) | 0.981 | 0.966 | 0.933 | 1.000 | 0.684 | 0.812 | 0.885 | 1.000 | 0.000 | 0.000 |
| test | opentslm-sp-1b-run2 | 0.981 | 0.929 | 0.941 | 0.737 | 0.737 | 0.737 | 0.846 | 1.000 | 0.712 | 0.679 |
