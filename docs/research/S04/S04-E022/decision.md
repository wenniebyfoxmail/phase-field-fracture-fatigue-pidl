# E022 completed: last-hidden leak does not restore three-state accuracy

## Decision

Execution completed: original exact-source producer aggregate admits all3 rows, no missing/integrityerrors. Original verdict **LAST_HIDDEN_LEAK_THREE_STATE_UV_SCREEN_FAIL**; onlyc20 fullUV<=.001. c60 is not restored to E019 or E021 accuracy; c83 improves slightly over E021 but still misses. c20 remains below the absolute threshold while losing precision relative to both historical controls. Do not adopt fixedleak.01 as the repaired three-state method, discard useful coordinate preconditioning, or stitch state winners.

## Same-state comparison

Mass-weighted two-component savedUV error /abs(Us); damage>.1, regional RMS normalized by own regional mass. Frozen damage/history/fatigue, seed7,alpha.7,10000newupdates; final10000only, not best checkpoint. Lowerisbetter. A whole-field threshold of.001 does not impose a.001 damage-region threshold; regional RMSs do not add.

| State | Arm | Full | Damage | Background |
|---|---|---|---|---|
| c20s4 | backbone | 0.00307912162404 | 0.0242348624521 | 0.000240242648448 |
| c20s4 | E019 | 0.000703914452973 | 0.00523732957986 | 0.000237204922011 |
| c20s4 | E021 | 0.000660679469207 | 0.00487492910867 | 0.00023678662424 |
| c20s4 | E022 | 0.000708697178091 | 0.00527672138213 | 0.00023744142766 |
| c60s4 | backbone | 0.00348781439124 | 0.0231539132273 | 0.000267799554042 |
| c60s4 | E019 | 0.000688588230158 | 0.00424277319804 | 0.000263837816752 |
| c60s4 | E021 | 0.000786449686755 | 0.00493005776301 | 0.00026791736343 |
| c60s4 | E022 | 0.00115421898763 | 0.00748206820262 | 0.000266185318189 |
| c83s4 | backbone | 0.00330468638849 | 0.0195607639007 | 0.000166778694661 |
| c83s4 | E019 | 0.00323823830793 | 0.0191674428252 | 0.00016345393029 |
| c83s4 | E021 | 0.00116781897374 | 0.0068530245778 | 0.000165651876292 |
| c83s4 | E022 | 0.00114613474117 | 0.00672457076213 | 0.000164031357526 |

| State | Comparator | Full change | Damage change | Background change |
|---|---|---|---|---|
| c20s4 | E019 | +0.679447% | +0.752135% | +0.099705% |
| c20s4 | E021 | +7.267928% | +8.242013% | +0.276537% |
| c20s4 | backbone | -76.983787% | -78.226733% | -1.165996% |
| c60s4 | E019 | +67.621074% | +76.348531% | +0.889752% |
| c60s4 | E021 | +46.763233% | +51.764311% | -0.646485% |
| c60s4 | backbone | -66.907098% | -67.685513% | -0.602778% |
| c83s4 | E019 | -64.606226% | -64.916704% | +0.353266% |
| c83s4 | E021 | -1.856815% | -1.874411% | -0.978268% |
| c83s4 | backbone | -65.317897% | -65.622146% | -1.647295% |

## Background preservation and locality

Relative to inherited backbone, allthree improve damage and background. Against E021, c60/c83 background improves but c20 background worsens. Against E019, allthree background errors are worse, including c83; hence no universal background-preservation claim against the common control. The same distinction holds for window-inside background. Saved UV outside the compact window is exactly unchanged (maximum absolute difference 0 for all nine pair comparisons against backbone/E019/E021), recorded in exterior_pair_drift.json; localized support must not be inferred from full-background averages alone.

| State | Arm | Inside-background conditional RMS | Outside-background conditional RMS |
|---|---|---|---|
| c20s4 | backbone | 0.000542510846283 | 0.00022693578597 |
| c20s4 | E019 | 0.000487512450446 | 0.00022693578597 |
| c20s4 | E021 | 0.000479504064832 | 0.00022693578597 |
| c20s4 | E022 | 0.000491988855372 | 0.00022693578597 |
| c60s4 | backbone | 0.000508114373223 | 0.000254131565043 |
| c60s4 | E019 | 0.000448354163362 | 0.000254131565043 |
| c60s4 | E021 | 0.000509796996624 | 0.000254131565043 |
| c60s4 | E022 | 0.000484548930542 | 0.000254131565043 |
| c83s4 | backbone | 0.000372604944382 | 0.000150350128806 |
| c83s4 | E019 | 0.000338142528829 | 0.000150350128806 |
| c83s4 | E021 | 0.000361217025778 | 0.000150350128806 |
| c83s4 | E022 | 0.000344323944213 | 0.000150350128806 |

## Activation component versus successful fitting

Actual final trained LeakyReLU checkpoints were decoded from their real class/behavior manifests. Nonzero last-hidden pathways are descriptive only; restoring a pathway does not establish its utility, stationarity, causal gradient trajectory or full-network capacity. Endpoint evidence cannot uniquely explain why AdamW reaches a worse c60 field. In particular, nonzero coefficients need not provide independent useful feature directions. The passive trace shows c60 E022 remains near .0012 after its early decrease, whereas E021 makes a further decrease around updates 6000–8000; c83 E022 begins its main decrease later than E021 and then reaches a similar platform. These sampled traces support a change in optimization path but cannot locate its causal event or qualify a best intermediate checkpoint.

| State | Arm | Region | Mass-weighted nonzero fraction | Ever-nonzero units /283 |
|---|---|---|---|---|
| c20s4 | E021 | damage | 0.0512306294 | 182 |
| c20s4 | E021 | background_inside | 0.0509514803 | 52 |
| c20s4 | E022 | damage | 1 | 283 |
| c20s4 | E022 | background_inside | 1 | 283 |
| c60s4 | E021 | damage | 0.000310039682 | 72 |
| c60s4 | E021 | background_inside | 0 | 0 |
| c60s4 | E022 | damage | 0.999430412 | 283 |
| c60s4 | E022 | background_inside | 1 | 283 |
| c83s4 | E021 | damage | 0.0105512153 | 141 |
| c83s4 | E021 | background_inside | 0.00955035075 | 10 |
| c83s4 | E022 | damage | 0.999270924 | 283 |
| c83s4 | E022 | background_inside | 1 | 283 |

## Integrity, portability and claim boundary

Exact sciencea540888497d1838a6aa202f59a884e6930e50fb4; deployment84a6cdaea5a2c7f99d87a133ad7fa38ec858acdb. Exactlyapproved twofiles transferred unchanged; one dispatcher3412386 at14:06:32Z, allthree formalruntime/CUDA/nativeLRpreflights passed, matrix aggregate completed14:49:42Z on2026-10-16. No restart/retry/budget/GPU/source changes. All65remote files45604015bytes and27actualproducer archivecopies verified; all60copied historical assetidentities compared with immutable local originals. Inbound retrieval resumed afterVPNdisconnect; this was not producer retry.

Actual10000usedLR arrays equal expected/preflight/ownE021 arrays exactly; usedfirst.001,last1.0000024427270673e-5, postfinal1e-5/no10001. Original strictMac aggregate is retained separately, with no tolerance or nativevector substitution: strict INADMISSIBLE from nativeLR bit portability is not overwritten by supplementary UV reduction. Read numerical_reload_audit.json for original-tolerance reference-rho checks; strict nativeLR failure can occur before rho is evaluated. Producer3valid is distinct from strictMac full re-admission and supplementary savedUV reproduction. No fullFEMteacher, jointdamage/UV, autonomouscycle, forecast or physical qualification is conferred.

Exact tables/figures and reproduction details: local_archive/experiments/S04-E022/producer_execution_v1/analysis/; manifest/receipt/auditcommands in its parent. Independent bounded evidence review completed: [BOUNDED_EVIDENCE_AUDIT_PASS](evidence_review.md), with no blocking mismatch. Independent Q4 mass reductions reproduce all 36 headline and 24 support values within 1e-14, and a manual raw-tensor leaky forward agrees within 1.39e-16. This is saved-field evidence acceptance; original scientific FAIL and strict Mac INADMISSIBLE remain unchanged.

## One minimum next discriminator (proposal only)

Reuse the already reviewed frozen-feature/output-head/region-gradient diagnostic on **E021/E022 × c20/c60/c83**, preserving mass weights, effective physicalBC/window features and pair identities. Ask whether c60's now-nonzero features still leave a large output-head normal-equation residual and whether damage/inside-background gradients compete; use c20 as the early-state sentinel and c83 as the remaining-damage sentinel. Accumulate Gram/residuals and autodiff gradients only; no least-squares/ridge solve, optimizer, parameter updates or new teacher solve. Compare with existing E021 six-endpoint evidence and use the same near-zero-denominator rules/RSS guard. Review the diagnostic before execution.

If c60/c83 retained useful directions but head optimality remains poor, prepare one output-head scaling/preconditioning control preserving original objective, coordinates, support, LR and total10000update budget. If that condition is absent, do not launch this repair; revisit the representation hypothesis from the measured diagnostics. No activation/LR/width sweep, extra10000steps or automatic newproducer launch. Current evidence supports this discriminator, not a proven next repair.
