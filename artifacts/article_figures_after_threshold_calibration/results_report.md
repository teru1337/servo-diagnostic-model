# Results Report After Threshold Calibration

## 1. Configuration

- `anomaly_warning = 0.62`
- Source config: `servo_diagnostic_model/config/thresholds.json`
- These figures reflect the current production threshold configuration.

## 2. Generated figures

- `fig1_group_anomaly_with_normal.png`: Group anomaly comparison including normal operation.
- `fig2_group_health_with_normal.png`: Group Health Score comparison including normal operation.
- `fig3_e2_r02_scores_over_time.png`: E2 R02 Anomaly Score and Health Score over time.
- `fig4_e2_r02_risks_over_time.png`: E2 R02 statistical and physical risks over time.
- `fig5_statistical_vs_physical_risks.png`: Group-level statistical versus physical risk comparison.
- `fig6_e2_r02_current_torque.png`: E2 R02 current and torque features over time.

## 3. Holdout validation summary

- Validation type: same-campaign holdout validation, not independent validation.
- Train files: 9
- Validation files: 8
- Validation windows: 1161
- Mean Anomaly Score: 0.539
- Maximum Anomaly Score: 0.789
- Mean Health Score: 94.796
- Minimum Health Score: 92.802
- Warning-or-higher false-positive rate after threshold calibration: 7.924%
- Critical false-positive rate: 0.086%

## 4. Group separation summary

| Group | Windows | Mean Anomaly Score | Max Anomaly Score | Mean Health Score | Min Health Score | Mean Max Physical Risk |
| ----- | ------: | -----------------: | ----------------: | ----------------: | ---------------: | ---------------------: |
| normal_validation | 1161 | 0.539 | 0.789 | 94.796 | 92.802 | 0.089 |
| transition | 2347 | 0.574 | 0.835 | 94.256 | 88.503 | 0.137 |
| elevated_load | 1594 | 0.632 | 0.772 | 93.840 | 92.490 | 0.171 |
| pre_emergency_proxy | 232 | 0.790 | 0.858 | 92.346 | 90.861 | 0.102 |

## 5. E2 R02 summary

- Maximum Anomaly Score: 0.858
- Mean Anomaly Score: 0.801
- Detection rate above 0.62: 100.000%
- Rank by maximum anomaly: 1
- Rank by mean anomaly: 1
- E2 R02 is a pre-emergency proxy, not a confirmed fault.

## 6. Interpretation

The diagnostic model preserved the mean Anomaly Score ordering from normal holdout operation through transition and elevated-load operation to the pre-emergency proxy group. After threshold calibration, normal holdout warning-or-higher false positives were reduced to approximately 7.9%, while E2 R02 remained fully detected above the calibrated threshold.

These results do not establish confirmed fault prediction, validated industrial deployment, independent validation, or causal proof of degradation.

## 7. Limitations

- Same-campaign holdout validation, not independent validation.
- E2 is a pre-emergency proxy, not a confirmed fault.
- Thermal diversity is limited.
- Remaining false positives are influenced by position and voltage-level features.
- The threshold should be validated on new independent normal data before production use.
- Feature weights should be reviewed only after new-data validation.
