# Laboratory Diagnostic Pipeline Analysis

## Scope

This report analyzes the completed physical-statistical laboratory pipeline using:

- `data/lab/manifests/normal_profile_files.csv`
- `data/lab/manifests/test_files.csv`
- `artifacts/profiles/normal_profile_lab.json`
- `artifacts/diagnostics/lab_diagnostic_summary.csv`
- `artifacts/diagnostics/lab_diagnostic_results.json`
- `data/lab/metadata/stand_passport.csv`
- `data/lab/metadata/lab_notes.md`

No model logic, tests, configurations, or profile statistics were changed.

## Profile Summary

`artifacts/profiles/normal_profile_lab.json` exists, loads successfully, and is a
valid JSON object containing `meta`, `global`, and `by_motion_phase`.

| Item | Value |
|---|---:|
| Source normal files | 17 |
| Normal feature rows/windows | 2,406 |
| Global profile features | 41 |
| Minimum count | 5 |
| Profile reliability | `true` |
| Profile version | `0.2` |

Available phase profiles:

| Motion phase | Profile features |
|---|---:|
| acceleration | 39 |
| braking | 39 |
| mixed | 41 |
| moving | 39 |
| stopped | 41 |

There is no phase-specific `holding` profile because only two holding windows
were detected during the profile audit, below `min_count=5`. Holding windows
therefore use the global profile.

## Diagnostic Contract Verification

The results artifact contains 20 test files and 4,173 diagnostic windows.

- `anomaly_score` is populated and is not always zero.
- `risks.statistical_anomaly` is populated in every window.
- Recommendations are present in every window.
- Every window contains all required JSON-contract fields.
- The complete results artifact is JSON-serializable.

## Diagnostic Summary

| Session | Expected label | Windows | Mean health | Min health | Mean anomaly | Max anomaly | Most frequent state |
|---|---|---:|---:|---:|---:|---:|---|
| B2_ACC_DEC_MEDIUM R01 | transition | 85 | 95.230 | 94.254 | 0.522 | 0.605 | warning |
| B2_ACC_DEC_MEDIUM R02 | transition | 85 | 94.599 | 93.612 | 0.572 | 0.655 | warning |
| B3_ACC_DEC_SHARP R01 | elevated_load | 85 | 94.394 | 93.451 | 0.671 | 0.741 | warning |
| B3_ACC_DEC_SHARP R02 | elevated_load | 85 | 93.685 | 93.087 | 0.706 | 0.768 | warning |
| B4_REVERSAL R01 | transition | 85 | 95.267 | 93.630 | 0.436 | 0.634 | observation |
| B4_REVERSAL R02 | transition | 86 | 93.545 | 80.234 | 0.437 | 0.676 | observation |
| B5_CYCLIC R01 | transition | 295 | 95.445 | 93.256 | 0.404 | 0.645 | observation |
| B5_CYCLIC R02 | transition | 296 | 95.594 | 94.009 | 0.405 | 0.622 | observation |
| C4_SPEED_1200 R01 | transition | 56 | 94.166 | 93.425 | 0.532 | 0.658 | warning |
| C4_SPEED_1200 R02 | transition | 55 | 94.192 | 93.516 | 0.567 | 0.701 | warning |
| C5_SPEED_1500 R01 | transition | 56 | 93.740 | 93.198 | 0.629 | 0.648 | warning |
| C5_SPEED_1500 R02 | transition | 56 | 93.174 | 92.517 | 0.669 | 0.779 | warning |
| D2_LONG_CYCLE_MED R01 | transition | 596 | 94.204 | 92.977 | 0.588 | 0.732 | warning |
| D2_LONG_CYCLE_MED R02 | transition | 596 | 94.174 | 93.221 | 0.584 | 0.713 | warning |
| D3_LONG_CYCLE_HARD R01 | elevated_load | 596 | 94.090 | 92.930 | 0.584 | 0.704 | warning |
| D3_LONG_CYCLE_HARD R02 | elevated_load | 596 | 94.043 | 92.855 | 0.582 | 0.715 | warning |
| E1_LOAD_LOW_INERTIA R01 | elevated_load | 116 | 95.761 | 93.732 | 0.355 | 0.621 | observation |
| E1_LOAD_LOW_INERTIA R02 | elevated_load | 116 | 94.354 | 93.384 | 0.602 | 0.683 | warning |
| E2_LOAD_MED_INERTIA R01 | pre_emergency_proxy | 116 | 93.055 | 92.472 | 0.718 | 0.761 | warning |
| E2_LOAD_MED_INERTIA R02 | pre_emergency_proxy | 116 | 92.377 | 91.106 | 0.756 | 0.858 | warning |

## Group Comparison

Normal files were diagnosed against the existing profile for comparison only;
the profile was not retrained.

| Expected group | Files | Windows | Mean file anomaly | Maximum anomaly | Mean file health |
|---|---:|---:|---:|---:|---:|
| normal | 17 | 2,406 | 0.442 | 0.751 | 95.472 |
| transition | 12 | 2,347 | 0.529 | 0.779 | 94.444 |
| elevated_load | 6 | 1,594 | 0.583 | 0.768 | 94.388 |
| pre_emergency_proxy | 2 | 232 | 0.737 | 0.858 | 92.716 |

The group-level ordering is correct and useful:

```text
normal < transition < elevated_load < pre_emergency_proxy
```

E2 clearly stands out from the normal baseline. Its mean file anomaly is
approximately 67% higher than the normal mean (`0.737` versus `0.442`), and E2
R02 has both the highest maximum anomaly (`0.858`) and the lowest sustained
mean health score (`92.377`) among test files.

## Top Anomalous Files

| Rank | Session | Expected label | Mean anomaly | Max anomaly |
|---:|---|---|---:|---:|
| 1 | E2_LOAD_MED_INERTIA R02 | pre_emergency_proxy | 0.756 | 0.858 |
| 2 | C5_SPEED_1500 R02 | transition | 0.669 | 0.779 |
| 3 | B3_ACC_DEC_SHARP R02 | elevated_load | 0.706 | 0.768 |
| 4 | E2_LOAD_MED_INERTIA R01 | pre_emergency_proxy | 0.718 | 0.761 |
| 5 | B3_ACC_DEC_SHARP R01 | elevated_load | 0.671 | 0.741 |

Test files with the lowest minimum health scores:

| Rank | Session | Expected label | Minimum health |
|---:|---|---|---:|
| 1 | B4_REVERSAL R02 | transition | 80.234 |
| 2 | E2_LOAD_MED_INERTIA R02 | pre_emergency_proxy | 91.106 |
| 3 | E2_LOAD_MED_INERTIA R01 | pre_emergency_proxy | 92.472 |
| 4 | C5_SPEED_1500 R02 | transition | 92.517 |
| 5 | D3_LONG_CYCLE_HARD R02 | elevated_load | 92.855 |

B4 R02's isolated low health value is driven by temperature risk and should
not be interpreted as stronger overall anomaly separation than E2.

## Causes And Recommendations

Main-cause frequency across test windows:

| Main cause | Occurrences |
|---|---:|
| statistical_anomaly | 3,954 |
| temperature | 13 |
| data_quality | 9 |

Recommendations are present and consistent with model state:

- 3,317 windows recommend observing the anomaly trend.
- 798 windows recommend continued monitoring.
- 51 windows recommend checking features contributing to the anomaly score.
- Temperature-risk windows recommend observing temperature or checking
  cooling, ventilation, duty cycle, and load.

These recommendations are reasonable for the detected risks, but they remain
generic. For article materials, recommendations should be presented as
rule-based engineering guidance rather than proof of a specific failure mode.

## Physical Risks And Passport Limits

Physical risks remain low for most test windows because measured values stay
well below the configured passport-scale limits.

| Risk | Mean | Maximum | Interpretation |
|---|---:|---:|---|
| current | 0.021 | 0.086 | Far below rated/max current limits |
| torque | 0.021 | 0.075 | Far below rated/max torque limits |
| velocity | 0.142 | 0.250 | Highest tests reach about 25% of 6000 rpm |
| voltage | 0.069 | 0.152 | Within configured safe/critical range |
| temperature | 0.002 | 0.931 | Usually low; isolated transient requires review |
| statistical_anomaly | 0.559 | 0.858 | Dominant early-deviation signal |

`stand_passport.csv` confirms:

| Limit | Passport | Config | Assessment |
|---|---:|---:|---|
| rated current | 4.270 A | 4.27 A | Exact match |
| rated torque | 2.391 N·m | 2.39 N·m | Match after rounding |
| maximum motor speed | 6000 rpm | 6000 rpm | Exact match |

The passport does not document maximum current, maximum torque, DC-bus
safe/critical ranges, or temperature limits. Therefore there is no clear
documented reason to modify `limits.json` now. Those values should be verified
against the drive/motor manuals and measured stand conditions before they are
described as calibrated limits.

The E2 result supports the intended physical-statistical design: E2 current and
torque behavior is statistically unusual while remaining far below hard
passport limits. Physical limits should not be lowered merely to increase E2
risk scores.

## Data Quality

Test diagnostics contain:

- 30 windows with nonzero data-quality risk;
- 25 windows with missing values;
- 9 windows with time gaps;
- no windows with invalid numeric values.

Affected files are primarily B5 CYCLIC R01, C4 SPEED 1200 R01, and D2 LONG
CYCLE MED R01. Their issues are limited and do not explain E2 separation.
Timestamp conversion also emits warnings about discarding nonzero nanoseconds;
this does not prevent diagnosis but should be documented.

## Interpretation For The Article

The strongest defensible result is:

> A median/MAD normal profile detects the E2 pre-emergency proxy as a stronger
> deviation than normal, transition, and elevated-load groups while measured
> values remain below passport-scale physical limits.

This supports the article's central argument that statistical telemetry
analysis can identify atypical servo behavior before hard engineering limits
are exceeded. The physical-risk layer provides safety-limit context, while the
statistical layer provides early-deviation sensitivity.

Useful article figures:

1. Group comparison of mean and maximum Anomaly Score.
2. E2 R02 Anomaly Score and Health Score over time.
3. E2 current/torque features versus the normal profile.
4. Statistical anomaly risk versus physical current/torque risks.
5. Data-quality risk over time for B5 R01 or D2 R01.

## Limitations

1. Normal-session anomaly scores are higher than desirable. The normal group
   mean is `0.442`, and C3 SPEED 900 R02 reaches `0.751`.
2. Several normal source sessions are most frequently classified as warning,
   indicating false-positive sensitivity or insufficient regime-specific
   profiles.
3. There is no phase-specific holding profile because detected holding coverage
   is below `min_count`.
4. The normal baseline contains the same rows used to fit the profile, so this
   is not an independent normal validation set.
5. The passport does not document maximum current/torque, DC-bus, or thermal
   limits.
6. E2 is a pre-emergency proxy, not a documented hardware fault or emergency.
7. Most recommendations are generic because statistical anomaly is the
   dominant main cause.
8. One normal holding session contains an isolated health score of `50.0`;
   this window should be inspected before publication.

## Recommended Next Actions

1. Create an independent normal-validation manifest and quantify false-positive
   rates without retraining on those files.
2. Inspect C3 SPEED 900 R02, A4 reversal sessions, and the isolated A1 holding
   health-score drop to understand normal-session alerts.
3. Review motion-phase detection and collect enough holding windows for a
   reliable phase-specific holding profile.
4. Verify maximum current, maximum torque, DC-bus, and temperature limits from
   manufacturer documentation and stand measurements.
5. Keep physical passport limits physically meaningful; calibrate statistical
   thresholds/profile coverage separately.
6. Generate article plots emphasizing E2 separation and the contrast between
   statistical anomaly and low physical-limit risk.
7. Describe E2 as a reproducible pre-emergency proxy and avoid claiming
   validated fault prediction until real fault data is available.

## Readiness

The pipeline is ready for plots and preliminary article materials. It has a
loadable normal profile, complete JSON diagnostic outputs, useful group-level
separation, and a clear E2 case study. Publication claims should include the
normal false-positive limitation and the incomplete passport calibration.
