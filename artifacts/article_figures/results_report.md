# Laboratory Results Report

## 1. Purpose

This report summarizes article-ready results from the physical-statistical diagnostic pipeline for preliminary laboratory validation.

## 2. Data and profile

- The existing `artifacts/profiles/normal_profile_lab.json` profile was used without retraining.
- Normal profile source files: 17.
- Normal profile feature rows/windows: 2406.
- Diagnostic test groups: transition, elevated_load, and pre_emergency_proxy.
- E2 R02 is the main pre-emergency proxy case.
- Group anomaly and mean-health values were obtained from the verified Group Comparison table in `artifacts/diagnostics/lab_pipeline_analysis.md`.
- Normal minimum Health Score and mean maximum physical risk were computed from 17 normal manifest files and 2406 windows using the existing normal profile without retraining.

## 3. Main quantitative result

| Group | Mean Anomaly Score | Max Anomaly Score | Mean Health Score | Min Health Score |
| ----- | -----------------: | ----------------: | ----------------: | ---------------: |
| normal | 0.442 | 0.751 | 95.472 | 50.000 |
| transition | 0.529 | 0.779 | 94.444 | 80.234 |
| elevated_load | 0.583 | 0.768 | 94.388 | 92.855 |
| pre_emergency_proxy | 0.737 | 0.858 | 92.716 | 91.106 |

## 4. Interpretation

- Anomaly Score increases from normal operation to the pre-emergency proxy group.
- E2 R02 has the strongest statistical deviation among the evaluated test sessions.
- Physical risks remain low compared with statistical anomaly risk.
- Normal-group mean maximum physical risk is 0.092.
- Figure 6 includes normal-profile median references for current_rms (0.080 A) and torque_rms (0.045 N·m).
- This supports a physical-statistical approach as an early-deviation indicator while retaining physically meaningful limit context.

## 5. Figure list

- `fig1_group_anomaly_with_normal.png`: Group anomaly comparison including normal operation.
- `fig2_group_health_with_normal.png`: Group Health Score comparison including normal operation.
- `fig3_e2_r02_scores_over_time.png`: E2 R02 Anomaly Score and Health Score over time.
- `fig4_e2_r02_risks_over_time.png`: E2 R02 statistical and physical risks over time.
- `fig5_statistical_vs_physical_risks.png`: Group-level statistical versus physical risk comparison.
- `fig6_e2_r02_current_torque.png`: E2 R02 current and torque features over time.

## 6. Article-ready wording

The pre-emergency proxy group demonstrated the highest mean Anomaly Score.
The E2 R02 session reached a maximum Anomaly Score of approximately 0.858.
The maximum plotted E2 R02 physical risk was approximately 0.112, indicating that the detected deviation was statistical rather than a hard-limit violation.
The group-level ordering supports the use of the statistical layer as an early-deviation indicator in preliminary laboratory validation.

## 7. Limitations

- E2 is a pre-emergency proxy, not a validated fault.
- Normal false positives require further calibration.
- The normal profile should be validated on independent normal data.
- Physical limits should not be tuned only to increase anomaly contrast.

## 8. Recommended next steps

1. Inspect false positives in normal sessions.
2. Create an independent normal-validation manifest.
3. Tune statistical thresholds and feature weights if needed.
4. Keep physical limits physically meaningful.
5. Prepare article tables and captions.
