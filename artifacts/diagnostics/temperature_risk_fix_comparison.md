# Temperature Risk Fix Comparison

## 1. Purpose

This report compares diagnostics before and after improving the robustness of
temperature slope risk for quantized laboratory telemetry. The existing
`artifacts/profiles/normal_profile_lab.json` profile was used without
retraining. The statistical anomaly model, feature extraction, Health Score
formula, classifier, and hard-cap rules were not changed.

## 2. Changed model behavior

Absolute temperature risk remains the existing linear risk from `temp_max`
between `temp_safe` and `temp_critical`.

Temperature slope risk remains the existing ratio of positive `temp_slope` to
`temp_slope_limit`, with these deterministic config-driven gates:

- While `temp_max < temp_safe`, slope-only risk is capped by
  `temp_slope_safe_risk_cap=0.5`.
- While `temp_max < temp_safe` and `temp_max - temp_min <=
  temp_quantized_range_C=1.0`, slope-only risk is capped more strictly by
  `temp_slope_quantized_risk_cap=0.3`.
- At or above `temp_safe`, slope risk is unrestricted.
- At or above `temp_critical`, absolute temperature risk remains `1.0`.

Every returned risk remains clamped to `0..1`.

## 3. Reproduced false outlier after fix

Source:
`data/lab/exports/telemetry_A1_HOLDING_SERVO_ON_R01_20260611_141919.csv`

| Window | Old temperature risk | New temperature risk | Old Health Score | New Health Score | Old state | New state |
| ------ | -------------------: | -------------------: | ---------------: | ---------------: | --------- | --------- |
| 94-99 s | 1.000 | 0.300 | 50.000 | 91.283 | critical | observation |
| 95-100 s | 1.000 | 0.300 | 50.000 | 91.301 | critical | observation |

The false critical state and the temperature-driven Health Score hard cap are
removed. The remaining `observation` state is caused by Anomaly Scores of
approximately `0.420` and `0.418`, not by a critical physical risk.

## 4. Normal-group metrics after fix

These values are computed directly across all normal diagnostic windows.

| Metric | Value |
| ------ | ----: |
| files | 17 |
| windows | 2406 |
| mean Health Score | 95.603 |
| minimum Health Score | 91.085 |
| mean Anomaly Score | 0.419 |
| maximum Anomaly Score | 0.751 |
| mean maximum physical risk | 0.090 |

The normal minimum Health Score is no longer `50.000`.

## 5. Group comparison after fix

Group mean values are means of file-level means, matching the established
article comparison method.

| Group | Mean Anomaly Score | Max Anomaly Score | Mean Health Score | Min Health Score |
| ----- | -----------------: | ----------------: | ----------------: | ---------------: |
| normal | 0.442 | 0.751 | 95.536 | 91.085 |
| transition | 0.529 | 0.779 | 94.497 | 88.796 |
| elevated_load | 0.583 | 0.768 | 94.388 | 92.855 |
| pre_emergency_proxy | 0.737 | 0.858 | 92.716 | 91.106 |

The anomaly ordering remains:

```text
normal < transition < elevated_load < pre_emergency_proxy
```

## 6. Main-result preservation

- E2 remains the strongest pre-emergency proxy case.
- E2 R02 remains the strongest individual case by maximum Anomaly Score at
  `0.858`.
- E2 R02 maximum physical risk remains low at `0.112`.
- Statistical anomaly remains the dominant early-deviation signal.
- The maximum physical risk across the re-diagnosed test manifest is `0.333`,
  below hard-limit interpretation.

## 7. Publication impact

Article figures should be updated to use:

`artifacts/article_figures_after_temperature_fix/`

instead of:

`artifacts/article_figures/`

The after-fix figures preserve the main anomaly result while removing the
misleading isolated normal-group Health Score minimum of `50.000`.

## 8. Remaining limitations

- E2 remains a pre-emergency proxy, not a validated fault.
- Independent normal validation is still required.
- Physical limits should remain physically meaningful and require hardware
  documentation or stand validation.
- Temperature slope robustness is heuristic and should be validated with more
  thermal data, sensor resolutions, sampling rates, and window lengths.

## Figure-generation group input

This verified table includes file and window counts for the article-figure
generator.

| Expected group | Files | Windows | Mean file anomaly | Maximum anomaly | Mean file health |
|---|---:|---:|---:|---:|---:|
| normal | 17 | 2406 | 0.442 | 0.751 | 95.536 |
| transition | 12 | 2347 | 0.529 | 0.779 | 94.497 |
| elevated_load | 6 | 1594 | 0.583 | 0.768 | 94.388 |
| pre_emergency_proxy | 2 | 232 | 0.737 | 0.858 | 92.716 |
