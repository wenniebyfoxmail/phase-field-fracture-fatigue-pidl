# S04-E010 — six-cycle native-Q4 reconstructed residual screen

Status: numerical COMPLETE; Evidence PASS on supplied records. Condor67.0 exit0, numerical0e675b9,33remote tests PASS. All18 identity/strict-feasibility/independent-operator gates pass. Five archived MATLAB bridges pass before13new reconstructed points. Solves0/historycommits0/trainingfalse. Archive-array recomputation of all three reported norms matches JSON. See metrics.csv, rows.json, validation.json and run_receipt.json.

| cycle | s2加载 UV | s4峰值 UV | s5卸载 UV | box s2 / s4 / s5 |
|---|---:|---:|---:|---|
| c20 | 0.02490654 | 0.71749586 | 4.900e-14 | 0.053055 / 0.048461 / 0.054312 |
| c40 | 0.0027167422 | 1.1879471 | 4.829e-14 | 0.059203 / 0.051162 / 0.059866 |
| c60 | 0.022071773 | 1.2857767 | 5.758e-14 | 0.065885 / 0.053405 / 0.065841 |
| c76 | 0.0027743067 | 1.0137327 | 7.998e-14 | 0.070696 / 0.056613 / 0.072654 |
| c82 | 0.0028250565 | 1.3533453 | 2.703e-14 | 0.073272 / 0.057037 / 0.074784 |
| c83 | 0.02016392 | 0.04133148 | 5.218e-14 | 0.073751 / 0.058073 / 0.074488 |

UV/box fixed threshold1e-3; all18 hard-KKT raw L2 pass4e-4 migration screen (range9.396e-6..6.786e-5). All18boxFAIL; all12loading/peakUVFAIL;6unloadedUVPASS. Own previous accepted FEM state used in each case. Us=.11999988 even when s5 actual displacement is0.

Interpretation: sampled c20 already fails loaded UV equilibrium; onset is not localized. At every sampled cycle peakUV exceeds its s2loadingUV. PeakUV is nonmonotonic across cycles, including a sharp c82→c83 decrease. This does not support generic critical amplification. s2/s4box rises across these six sampled cycles; s5 generally rises but falls slightly atc83. Box[0,1] is not hard irreversible[dprev,1] KKT; their differing verdicts are not a contradiction. UnloadUV near zero is limited evidence under zero imposed displacement, not full teacher validation.

Five original-reference points: c20/40/76/82/83s4. All remaining13 points includingc60s4 are reconstructed_not_archived_MATLAB, archived_oracle_gate NOT_AVAILABLE. They do not acquire archived-oracle qualification from the bridges. All full_teacher NOT_QUALIFIED. These are original fields in one sealed Stage0b trajectory, not re-equilibrated fields. No true-solution error, mesh convergence, full-trajectory monotonicity, or early cross-PIDL-history claim.

Next gate: read-only audit of final UV solve -> damage update -> staggered acceptance and residual provenance. Treat that ordering as a candidate explanation until exact stopping rule and final endpoint residual roles are verified. No long rerun/training authorized by this result alone.

Review qualifications: unloaded UV is numerical-zero level in this scale. Peak versus s2 has different actual loads; the common-scale ordering does not prove load-independent worsening. c83 peak remains41.33times threshold. Operator difference is mass-dual normalized, not Euclidean relative error. See evidence_review.md for exact scope and next single-state discriminant.
