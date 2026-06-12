# Threshold Calibration Application Report

## 1. Purpose

This report documents application of the previously evaluated anomaly warning threshold calibration.

## 2. Applied configuration change

| Config | Old value | New value |
| ------ | --------: | --------: |
| `anomaly_warning` | 0.50 | 0.62 |

## 3. Calibration basis

- Normal-validation warning-or-higher false-positive rate at 0.62: 7.924%
- Normal-validation critical false-positive rate at 0.62: 0.086%
- E2 R02 detection rate at 0.62: 100%
- E2 R02 rank by maximum Anomaly Score: 1
- E2 R02 rank by mean Anomaly Score: 1
- Group ordering preserved: yes

## 4. What was not changed

- No diagnostic formulas changed.
- No feature extraction changed.
- No physical risk logic changed.
- No Health Score formula changed.
- No normal profile was retrained or overwritten.
- `limits.json` is unchanged.
- `weights.json` is unchanged.

## 5. Remaining limitations

- Calibration is based on same-campaign holdout validation, not independent validation.
- E2 remains a pre-emergency proxy, not a confirmed fault.
- Feature weights, especially position and voltage-level features, should be reviewed only after validation on new data.
- The threshold should be validated on new independent normal data before production use.
