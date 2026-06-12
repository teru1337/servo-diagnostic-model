# Normal Holdout Validation Report

## 1. Purpose

This workflow validates a profile fitted on a held-out split of the same laboratory campaign. It is **holdout normal validation**, not truly independent validation.

## 2. Data split

- Source manifest: `data/lab/manifests/normal_profile_files.csv`
- Train manifest: `data\lab\manifests\normal_train_files.csv`
- Validation manifest: `data\lab\manifests\normal_validation_files.csv`
- Train files: 9
- Validation files: 8
- Split strategy: `by_repeat`
- Train/validation path overlap: none

## 3. Validation profile

- Output profile: `artifacts/validation/normal_profile_holdout_train.json`
- Training feature rows/windows: 1245
- Global feature count: 41
- Motion-phase profiles: acceleration, braking, mixed, moving, stopped

## 4. Normal holdout metrics

| Metric | Value |
| ------ | ----: |
| files | 8.000 |
| windows | 1161.000 |
| mean_health_score | 94.796 |
| min_health_score | 92.802 |
| mean_anomaly_score | 0.539 |
| max_anomaly_score | 0.789 |
| mean_statistical_anomaly_risk | 0.539 |
| max_statistical_anomaly_risk | 0.789 |
| mean_max_physical_risk | 0.089 |
| max_max_physical_risk | 0.150 |
| false_positive_windows_warning_or_higher | 92.000 |
| false_positive_rate_warning_or_higher | 7.924% |
| false_positive_windows_critical | 1.000 |
| false_positive_rate_critical | 0.086% |
| anomaly_threshold_exceedance_rate | 7.924% |
| data_quality_nonzero_windows | 0.000 |

State counts: `{"critical": 1, "observation": 1069, "warning": 91}`  
Risk-level counts: `{"critical": 1, "high": 91, "medium": 1069}`

## 5. Test group metrics with holdout-trained profile

| Group | Files | Windows | Mean Anomaly Score | Max Anomaly Score | Mean Health Score | Min Health Score | Mean Max Physical Risk |
| ----- | ----: | ------: | -----------------: | ----------------: | ----------------: | ---------------: | ---------------------: |
| transition | 12 | 2347 | 0.574 | 0.835 | 94.256 | 88.503 | 0.137 |
| elevated_load | 6 | 1594 | 0.632 | 0.772 | 93.840 | 92.490 | 0.171 |
| pre_emergency_proxy | 2 | 232 | 0.790 | 0.858 | 92.346 | 90.861 | 0.102 |

## 6. Group ordering check

The desired mean-anomaly ordering holds for this holdout split.

Observed mean anomaly scores: `{"elevated_load": 0.6318154364098832, "normal_validation": 0.5387863650900402, "pre_emergency_proxy": 0.7902670912503377, "transition": 0.5744498900027208}`

## 7. E2 case check

E2 R02 ranks 1 among diagnosed test sessions by maximum Anomaly Score. It remains a pre-emergency proxy rather than a confirmed fault.

## 8. Interpretation for article

Describe this result as **holdout validation**, not independent validation, because both subsets come from the same laboratory campaign. Do not claim proven fault prediction. E2 remains a pre-emergency proxy.

## 9. Limitations

- This is not a truly independent data collection.
- Thermal diversity remains limited.
- E2 is a proxy, not a confirmed fault.
- False positives may still require threshold or feature-weight calibration after review.
- Profile coverage may depend on the motion-phase distribution.

## 10. Recommended next actions

1. Collect a new independent normal session if possible.
2. Use the new normal session as external validation.
3. Compare holdout and external-validation metrics.
4. Tune thresholds or feature weights only after validation results are reviewed.
5. Keep physical limits physically meaningful.
