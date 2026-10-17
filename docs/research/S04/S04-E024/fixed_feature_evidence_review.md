# E024-D002 independent bounded result Evidence review

**PASS_WITH_RETAINED_NUMERICAL_WARNINGS** for the reported numerical fixed8000-feature comparison. No blocking numerical mismatch found. Bound diagnostic source `1f460aa41929ebb6f41a8311718b699225a8877f`. This does not pass strict Mac production admission, establish physical/application accuracy or authorize checkpoint replacement/training.

## Independent computations

Reconstructed all three original step8000 hidden features in different511-node chunks from raw checkpoint tensors, independent BC/quintic window, producerD including bias and independently integrated Q4 mass. Used direct SciPy **gesvd**, contrasting original **gesdd**, and **BLAS dgemm** for products. No optimizer or neural update was used. Recomputed all three fixed cutoffs for each state; ranks match exactly and full RMS differs at most9.76e-17. Alternate path raised **zero warnings**. Separate actual layer-order forward with external saved coefficients in509-node chunks reproduces saved oracle UV within1.39e-17. Recomputed all12 primary saved-field region scores agree within1e-14; support-exterior saved correction is exactly0.

|State|Ranks0.1/1/10|Primary full RMS/absUs|Full vsE023|Damage vsE023|Background vsE023|Inside background vsE023|
|---|---|---:|---:|---:|---:|---:|
|c20|279/279/278|.000613962619|−12.6237%|−14.3983%|+.3973%|+3.7762%|
|c60|284/284/284|.000909979102|+2.1819%|+2.1563%|+2.4484%|+18.1970%|
|c83|254/254/254|.001150331690|−.7240%|−.8563%|+5.7264%|+26.3275%|

Positive means larger error. c20's10× cutoff removes one more direction; primary/10× fullRMS differ only about1.02e-8. c60 andc83 metrics/ranks are stable across all prescribed cutoffs. Original direct-coefficient/projection weighted discrepancies are at most6.05e-12 (c20); alternate driver remains about5.76e-12. These are far smaller than the reported full-score differences, and actual saved UV realization gaps are smaller still. c20/c83 retained condition numbers about1.05e10/2.32e9 and sizable coefficient norms remain material to practical stability/generalization, despite reliable current-state score reproduction. Stability of scores is not proof that every coefficient or small singular direction is uniquely determined.

## Warning review

Original NumPy matmul divide/overflow/invalid RuntimeWarnings are retained, not ignored or relabelled as proven false alarms. Independently reproduced numerical results with a different SVD/product route and zero warnings. Root's separately retained fixed-c20-array replay (`matmul_warning_replay.json`) records repeated NumPy warnings while the same input products via dgemm and nonoptimized einsum are finite and agree exactly. The finite-input product-sum bound is about7.90e7 versus float64max1.80e308. This supports accepting the independently cross-validated reported products/scores; it **does not identify the backend/floating-point-status root cause**, does not excuse unrelated future warnings, and does not retroactively erase the original run warning status. A warning-free repeat of the original implementation was not established.

## Supported interpretation and next-action boundary

c20 andc83 have demonstrably realizable output-head coefficients on their fixed8000 features with smaller full/damage error than E023; hence these retained feature spans do not alone prevent those measured improvements. Their2000-step head tails did not attain these coefficients. This does not establish that a particular practical LR/solver can attain them under the neural training budget, that the benefit transfers to unobserved states, or that the background cost is acceptable. c83's gain is modest and its inside-background cost substantial.

c60 is full284-column rank across cutoffs, condition about3.43e7, with independently reproduced full-mass optimum above E023 by2.1819%. Within this numerical design and residual/precision evidence, retaining that fixed8000 span cannot reproduce the better E023 full-field score; feature evolution can matter here. This is not a universal network-capacity limitation or proof that one specific joint optimizer is necessary. The numerical distinction differs by state, so a universal head-only repair is not justified from these three endpoint results.

Full-field least squares is not a damage-optimal or background-preserving constrained solution. None of the primary oracle fields improves every E023 region. Application/background tolerance remains undefined; .001 is historical diagnostic only. Original frozen E019–E024 verdicts, damage/history/fatigue frozen scope and MacLR/mass/D/rho portability exceptions remain unchanged. These diagnostic NPZ/NPY coefficients are not trained model checkpoints, qualified FEM teachers or completed coupled-history models. No new repair was implemented or launched by this review; any next proposal should explicitly constrain background comparison and preserve state-specific feature reachability limits, rather than merely retune a uniform head tail.

All three decision plots were visually inspected. Comparison and rank plots match reported ordering/ranks. Initial full-field difference panels were largely white because a few extremes set the signed scale; the final display was subsequently changed to explicit symlog with a physical-window zoom, as recorded in the final addendum. Regional tables remain the quantitative basis. Reviewer wrote only local independent audit/review files, with no SSH, remote action, original checkpoint write or neural training.

## Final prose and revised visualization review

Reviewed `fixed_feature_decision.md`, `README_analysis.md`, and `results/interpretation.json`. Numerical ranks, primary regional changes, sensitivity bounds, realized projection differences and warning limitations agree with the reviewed outputs. c60'sMSE decomposition is the arithmetic identity (E024−oracle)+(oracle−E023), with2.5260983e-8 and3.4985848e-8 of total6.0246831e-8, or41.9291% and58.0709%. It correctly reports coexistence of remaining head optimization gap and the fixed8000 span deficit, without asserting a general causal percentage or an RMS-linear decomposition. c20/c83 truncated results are not described as exact full-space minima. Background acceptability is undefined; large coefficient norms are not proposed as deployable or direct AdamW initialization.

The sole next proposal—repeat a bounded head diagnostic on the existing E023 joint10000 states before any stable small correction—is supported as an unexecuted discriminator. It retains the feature-evolution path suggested byc60 and does not presume head improvement, background safety or a practical schedule. No additional solve, diagnostic, model change or run was authorized or performed by this wording review.

Inspected revised local-field PNG and its caption: three states, same scored fields, explicit physical-window plus.02 crop, shared per-state E023/oracle log limits, symmetric-log signed difference without outlier truncation, and vertical display stretch explicitly declared. Coordinates remain labelled. This addresses the initial near-white difference display without changing scores. Full-domain table/crop distinction and display log-floor are explicit. No blocking finding in final prose.
