# Calibration Report

## 1. Purpose

This report is evaluation-only. It simulates anomaly-warning thresholds and does not modify model behavior, formulas, profiles, or production configuration.

## 2. Current holdout validation problem

- Normal-validation windows: 1161
- Mean anomaly: 0.539
- Maximum anomaly: 0.789
- Warning-or-higher false-positive rate: 7.924%
- Critical false-positive rate: 0.086%
- Current group ordering holds: True

## 3. Threshold sweep methodology

Inputs were the existing normal-holdout and test diagnostic JSON files. Thresholds from 0.45 to 0.90 were simulated without rerunning diagnosis or invoking the production classifier. This is analysis, not automatic calibration.

## 4. Threshold sweep summary

| Threshold | Normal FPR warning+ | Normal critical FPR | Transition detection | Elevated-load detection | Pre-emergency detection | E2 R02 detection | Ordering holds |
| --------: | ------------------: | ------------------: | -------------------: | ----------------------: | ----------------------: | ---------------: | -------------- |
| 0.55 | 47.028% | 0.086% | 64.082% | 87.641% | 100.000% | 100.000% | True |
| 0.60 | 15.418% | 0.086% | 39.795% | 74.028% | 100.000% | 100.000% | True |
| 0.62 | 7.924% | 0.086% | 29.612% | 64.931% | 100.000% | 100.000% | True |
| 0.65 | 3.876% | 0.086% | 17.427% | 42.158% | 100.000% | 100.000% | True |
| 0.70 | 0.345% | 0.086% | 8.692% | 10.790% | 100.000% | 100.000% | True |
| 0.75 | 0.086% | 0.086% | 0.341% | 0.816% | 96.983% | 100.000% | True |
| 0.80 | 0.000% | 0.086% | 0.043% | 0.000% | 19.828% | 32.759% | True |

## 5. Candidate threshold

- Selected candidate: **0.62**
- Normal warning false-positive rate: 7.924%
- Reaches 5-10% target: True
- E2 R02 remains detected: True
- Group ordering holds: True

A threshold reaches the 5-10% normal warning false-positive target.

## 6. Group separation at candidate threshold

| Group | Mean Anomaly | Max Anomaly | Windows | Detection Rate Above Candidate |
| ----- | -----------: | ----------: | ------: | -----------------------------: |
| normal_validation | 0.539 | 0.789 | 1161 | 7.924% |
| transition | 0.574 | 0.835 | 2347 | 29.612% |
| elevated_load | 0.632 | 0.772 | 1594 | 64.931% |
| pre_emergency_proxy | 0.790 | 0.858 | 232 | 100.000% |

## 7. E2 R02 analysis

- Maximum anomaly: 0.858
- Mean anomaly: 0.801
- Detection rate above candidate: 100.000%
- Rank by session maximum: 1
- Rank by session mean: 1

E2 R02 remains one of the strongest anomaly cases. It remains a pre-emergency proxy, not a confirmed fault.

## 8. Normal false-positive feature analysis

| Feature | Mean FP Score | Max FP Score | Windows |
| ------- | ------------: | -----------: | ------: |
| position_max | 1.000 | 1.000 | 92 |
| position_min | 1.000 | 1.000 | 92 |
| voltage_max | 1.000 | 1.000 | 92 |
| voltage_mean | 1.000 | 1.000 | 92 |
| voltage_min | 1.000 | 1.000 | 92 |
| accel_min | 0.880 | 1.000 | 92 |
| velocity_rms | 0.835 | 1.000 | 92 |
| accel_max | 0.804 | 1.000 | 92 |
| abs_velocity_max | 0.791 | 1.000 | 92 |
| position_delta | 0.783 | 1.000 | 92 |

Top contributors are position_max, position_min, voltage_max, voltage_mean, voltage_min. Position and voltage-level features dominate the remaining normal false positives; current and torque features do not dominate them. All selected false-positive windows used phase-specific profiles, so the result does not indicate global-profile fallback, although motion-phase coverage still requires validation. Data-quality and physical risks are not the cause. The concentration of saturated feature scores means feature weighting should still be reviewed after threshold validation.

## 9. Calibration strategy comparison

| Strategy | Recommendation | Reason |
| -------- | -------------- | ------ |
| Change thresholds.json | Primary candidate | Test the selected warning threshold first because separation and ordering remain measurable. |
| Change statistical anomaly weight in weights.json | Defer | Health Score remains high; changing this weight does not directly solve anomaly-driven warning classification. |
| Change feature weights inside anomaly score | Investigate next | Review the concentrated false-positive features before any tuning. |
| Change state-classifier mapping | Investigate if threshold validation fails | Warnings are primarily anomaly-threshold driven while Health Score remains high. |

Do not change physical limits; physical risks are low. Do not revisit temperature slope gating unless thermal false positives reappear.

## 10. Recommended next step

A. Threshold-only calibration is sufficient for this holdout dataset, but must be validated on new data. Do not apply the recommendation automatically.

## 11. Article wording

Holdout validation on a same-campaign normal subset preserved the mean Anomaly Score ordering from normal validation through transition and elevated-load operation to the pre-emergency proxy group. The initial warning threshold produced a high normal false-positive rate, so an evaluation-only calibration sweep was performed. E2 R02 remained a strong pre-emergency proxy case; these results do not establish proven fault prediction.

## 12. Limitations

- Same-campaign holdout, not independent validation.
- Limited normal-validation diversity.
- E2 is a proxy rather than a confirmed fault.
- Thresholds require validation on new data before production use.
- Feature weights should not be tuned aggressively on this small dataset.
