# Normal Health Score Outlier Investigation

## Scope

The 17 CSV files in `data/lab/manifests/normal_profile_files.csv` were
re-diagnosed with the existing `artifacts/profiles/normal_profile_lab.json`
profile and the current limits, weights, and thresholds. The profile was not
retrained, and model behavior and configuration were not changed.

Reproduced normal-group metrics:

- files: 17
- windows: 2406
- mean Health Score: 95.551
- minimum Health Score: 50.000
- mean Anomaly Score: 0.419
- maximum Anomaly Score: 0.751
- mean maximum physical risk: 0.092

The article report's normal mean Health Score of 95.472 comes from the verified
group-comparison analysis, while the values above are from this direct
re-diagnosis. Both calculations reproduce the isolated 50.000 minimum.

## Lowest Health Score Source

- source CSV: `data/lab/exports/telemetry_A1_HOLDING_SERVO_ON_R01_20260611_141919.csv`
- session_id: `A1_HOLDING_SERVO_ON_R01_20260611_141919`
- experiment: stationary servo-on holding, no load
- device_id: `delta-asda-b3-e`
- minimum-score windows: 2 overlapping windows

### Window 1

- window_start: 94.000 s
- window_end: 99.000 s
- sample_count: 49
- Health Score: 50.000
- uncapped weighted Health Score: 80.326
- state: critical
- anomaly_score: 0.420127
- motion_phase: stopped

Risks:

| Risk | Value |
| --- | ---: |
| current | 0.000892 |
| torque | 0.000959 |
| velocity | 0.000000 |
| voltage | 0.088299 |
| temperature | 1.000000 |
| statusword | 0.000000 |
| error | 0.000000 |
| data_quality | 0.000000 |
| statistical_anomaly | 0.420127 |

Key features:

| Feature | Value |
| --- | ---: |
| temp_min | 48.000 °C |
| temp_max | 49.000 °C |
| temp_mean | 48.448980 °C |
| temp_std | 0.497390 °C |
| temp_slope | 0.262103 °C/s |
| configured temp_slope_limit | 0.200000 °C/s |
| time_gap_count | 0 |
| missing_ratio | 0.000000 |
| invalid_ratio | 0.000000 |
| error_flag | false |
| fault_flag | false |
| warning_flag | false |
| operation_enabled_ratio | 1.000000 |

Main causes:

1. `temperature=1.000000`: Drive temperature or temperature growth is
   approaching an unsafe range.
2. `statistical_anomaly=0.420127`: Current behavior differs from the normal
   statistical profile.

Explanation:

- A critical drive condition was detected.
- Health Score is 50.0.
- Drive temperature or temperature growth is approaching an unsafe range.
- Current behavior differs from the normal statistical profile.
- Anomaly Score is 0.420.

Recommendation:

- High priority, thermal: check cooling, ventilation, duty cycle, and load.
  Review `temp_max` and `temp_slope`.

### Window 2

- window_start: 95.000 s
- window_end: 100.000 s
- sample_count: 49
- Health Score: 50.000
- uncapped weighted Health Score: 80.345
- state: critical
- anomaly_score: 0.417505
- motion_phase: stopped

Risks:

| Risk | Value |
| --- | ---: |
| current | 0.000869 |
| torque | 0.000959 |
| velocity | 0.000000 |
| voltage | 0.088299 |
| temperature | 1.000000 |
| statusword | 0.000000 |
| error | 0.000000 |
| data_quality | 0.000000 |
| statistical_anomaly | 0.417505 |

Key features:

| Feature | Value |
| --- | ---: |
| temp_min | 48.000 °C |
| temp_max | 49.000 °C |
| temp_mean | 48.632653 °C |
| temp_std | 0.482082 °C |
| temp_slope | 0.216368 °C/s |
| configured temp_slope_limit | 0.200000 °C/s |
| time_gap_count | 0 |
| missing_ratio | 0.000000 |
| invalid_ratio | 0.000000 |
| error_flag | false |
| fault_flag | false |
| warning_flag | false |
| operation_enabled_ratio | 1.000000 |

Main causes:

1. `temperature=1.000000`: Drive temperature or temperature growth is
   approaching an unsafe range.
2. `statistical_anomaly=0.417505`: Current behavior differs from the normal
   statistical profile.

Explanation:

- A critical drive condition was detected.
- Health Score is 50.0.
- Drive temperature or temperature growth is approaching an unsafe range.
- Current behavior differs from the normal statistical profile.
- Anomaly Score is 0.418.

Recommendation:

- High priority, thermal: check cooling, ventilation, duty cycle, and load.
  Review `temp_max` and `temp_slope`.

## Cause Determination

| Candidate cause | Finding |
| --- | --- |
| data quality | Not supported. Risk is 0.0; no missing, invalid, short, or gap condition exists. |
| timestamp/windowing issue | Timestamps are regular at approximately 9.956 Hz. Overlapping five-second windows expose the same temperature transition twice, but no timestamp defect was found. |
| statusword/error_code/fault flag | Not supported. Error, fault, and warning flags are false; statusword risk is 0.0. |
| physical risk | Primary direct cause. `temp_slope` exceeds the configured 0.2 °C/s limit, making temperature risk 1.0. |
| statistical anomaly | Secondary only. Scores near 0.42 contribute to the uncapped weighted score but do not cause the exact 50.000 value. |
| unknown cause | Not applicable. |

The temperature channel has integer-degree resolution and chatters between 47,
48, and 49 °C before settling at 49 °C. The two minimum windows contain the
48-to-49 °C transition. Linear slope extraction over these windows produces
0.262103 and 0.216368 °C/s even though `temp_max` is only 49 °C, below the
configured safe level of 55 °C. Temperature risk therefore clamps to 1.0, and
the documented critical-temperature hard limit caps Health Score at exactly
50.000. Without the hard cap, the weighted scores would be approximately
80.326 and 80.345.

Likely cause: a physical-temperature-risk false outlier caused by the
interaction of integer temperature quantization, a short overlapping window,
and slope-based risk. It is not evidence of a critical absolute temperature.

## Publication Impact

The existing figures need revision or explicit annotation before publication.
The plotted minimum of 50.000 is a reproducible model output, but presenting it
as an unqualified normal-group minimum implies a critical physical event that
the raw telemetry does not support. Figure 2 and related text should identify
the isolated quantization/slope outlier, or use a distribution/robust summary
that keeps the outlier visible without implying it is representative of normal
operation. No model or configuration change is made by this investigation.
