# Article Figures After Threshold Calibration

This folder contains the final article-ready figures and results report generated from the post-threshold holdout-validation and calibration artifacts.

## Generation command

```powershell
.\.venv\Scripts\python.exe -m servo_diagnostic_model.evaluation.article_plots --validation-dir artifacts/validation_after_threshold_calibration --calibration-dir artifacts/calibration_after_threshold_application --thresholds servo_diagnostic_model/config/thresholds.json --output-dir artifacts/article_figures_after_threshold_calibration
```

## Sources

- `artifacts/validation_after_threshold_calibration/normal_holdout_diagnostic_results.json`
- `artifacts/validation_after_threshold_calibration/test_with_holdout_profile_results.json`
- `artifacts/validation_after_threshold_calibration/normal_profile_holdout_train.json`
- `artifacts/validation_after_threshold_calibration/holdout_validation_report.md`
- `artifacts/calibration_after_threshold_application/calibration_recommendation.json`
- `artifacts/calibration_after_threshold_application/group_separation_summary.csv`
- `servo_diagnostic_model/config/thresholds.json`

All preferred post-threshold sources were available; no fallback artifacts were used.

## Configuration confirmation

- `anomaly_warning = 0.62`
- No diagnostic formulas, feature extraction, statistical anomaly scoring, physical risks, Health Score logic, limits, weights, or normal profiles were changed.

## Remaining limitations

- This is same-campaign holdout validation, not independent validation.
- E2 R02 is a pre-emergency proxy, not a confirmed fault.
- Thermal diversity remains limited.
- Remaining normal false positives are influenced by position and voltage-level features.
- Validate the threshold on new independent normal data before production use.
