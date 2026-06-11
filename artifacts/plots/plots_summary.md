# Laboratory Diagnostic Plots

## Inputs
- `artifacts/diagnostics/lab_diagnostic_summary.csv`
- `artifacts/diagnostics/lab_diagnostic_results.json`

## Generated plots
- `group_anomaly_comparison.png`
- `group_health_comparison.png`
- `e2_r02_scores_over_time.png`
- `e2_r02_risks_over_time.png`
- `e2_r02_current_torque_over_time.png`
- `statistical_vs_physical_risks.png`
- `data_quality_cases.png`

## Interpretation
- `group_anomaly_comparison.png`: compares mean and maximum Anomaly Score across available experiment groups.
- The expected group ordering is normal < transition < elevated_load < pre_emergency_proxy.
- The diagnostic summary does not contain normal-group rows, so the generated group charts show only the available diagnostic-test groups.
- `group_health_comparison.png`: shows moderate Health Score differences; scores remain high because the measured physical risks are low.
- The E2 R02 case study uses session `E2_LOAD_MED_INERTIA_R02_20260611_165930`.
- E2 R02 stands out as a statistical deviation: maximum Anomaly Score 0.858 and maximum statistical anomaly risk 0.858.
- E2 R02 maximum plotted physical risk is 0.112; this supports interpreting statistical anomaly as an early-deviation indicator, not a hard-limit event.
- Data-quality risk is nonzero in 3 session(s).

## Limitations
- These figures describe the completed laboratory artifacts and do not establish fault prediction.
- The pre-emergency proxy label is an experimental proxy, not a validated emergency prediction.
- Group comparisons depend on the sessions included in the diagnostic summary.

## Recommended article figures
- Use `group_anomaly_comparison.png` for the group-level statistical-deviation result.
- Use `e2_r02_risks_over_time.png` and `statistical_vs_physical_risks.png` to contrast statistical and physical risks.
- Use `e2_r02_current_torque_over_time.png` as supporting context for the E2 R02 case study.
