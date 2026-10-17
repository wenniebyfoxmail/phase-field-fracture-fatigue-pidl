# E023 completed: c60 partly recovers; c83 does not improve over E022

## Decision

Original reviewed-source producer aggregate admits **3/3** final rows with no missing or integrity errors, but retains **FIXED_INITIAL_HEAD_RMS_THREE_STATE_UV_SCREEN_FAIL**. c20 and c60 full RMS are below .001; c83 remains above. Execution completion, component improvement and scientific target are distinct.

c60 full error decreases22.8441% and damage error24.3072% versus E022: this is a meaningful partial recovery and restores the absolute .001 full-field threshold. It does not restore earlier E021/E019 accuracy: full error is13.2365%/29.3296% higher, respectively. c83 is1.0981% worse full/1.1200% worse damage than E022, although it retains a0.7791% full improvement over E021 and64.2176% over E019. c20 passes the threshold and is slightly better than E022/E019 but still6.3549% worse full than E021. No state-winner stitching or universal adoption of the D repair is justified.

## Metric and exact comparison

Same-state synthetic fixed-damage two-component UV mass RMS divided by abs(Us); damage>.1, background its complement. Conditional regions divide by their own mass and do not add. Lower is better; negative percentage means improvement. Same exposed trajectory/seed7, alpha.7, final10000only; not a predictive/transfer validation. No best-checkpoint selection.

| State | Method | Full | Damage | Background |
|---|---|---|---|---|
| c20s4 | backbone | 0.00307912162404 | 0.0242348624521 | 0.000240242648448 |
| c20s4 | E019 | 0.000703914452973 | 0.00523732957986 | 0.000237204922011 |
| c20s4 | E021 | 0.000660679469207 | 0.00487492910867 | 0.00023678662424 |
| c20s4 | E022 | 0.000708697178091 | 0.00527672138213 | 0.00023744142766 |
| c20s4 | E023 | 0.000702664700291 | 0.00522858163723 | 0.000236585444254 |
| c60s4 | backbone | 0.00348781439124 | 0.0231539132273 | 0.000267799554042 |
| c60s4 | E019 | 0.000688588230158 | 0.00424277319804 | 0.000263837816752 |
| c60s4 | E021 | 0.000786449686755 | 0.00493005776301 | 0.00026791736343 |
| c60s4 | E022 | 0.00115421898763 | 0.00748206820262 | 0.000266185318189 |
| c60s4 | E023 | 0.000890548211628 | 0.0056633882207 | 0.000266600676095 |
| c83s4 | backbone | 0.00330468638849 | 0.0195607639007 | 0.000166778694661 |
| c83s4 | E019 | 0.00323823830793 | 0.0191674428252 | 0.00016345393029 |
| c83s4 | E021 | 0.00116781897374 | 0.0068530245778 | 0.000165651876292 |
| c83s4 | E022 | 0.00114613474117 | 0.00672457076213 | 0.000164031357526 |
| c83s4 | E023 | 0.00115872029226 | 0.00679988708809 | 0.000164051041951 |

| State | Comparator | Full change | Damage change | Background change |
|---|---|---|---|---|
| c20s4 | E022 | -0.851207% | -0.912304% | -0.360503% |
| c20s4 | E021 | +6.354856% | +7.254516% | -0.084963% |
| c20s4 | E019 | -0.177543% | -0.167031% | -0.261157% |
| c20s4 | backbone | -77.179703% | -78.425371% | -1.522296% |
| c60s4 | E022 | -22.844086% | -24.307183% | +0.156041% |
| c60s4 | E021 | +13.236514% | +14.874683% | -0.491453% |
| c60s4 | E019 | +29.329572% | +33.483171% | +1.047181% |
| c60s4 | backbone | -74.466869% | -75.540255% | -0.447677% |
| c83s4 | E022 | +1.098087% | +1.120017% | +0.012000% |
| c83s4 | E021 | -0.779117% | -0.775387% | -0.966385% |
| c83s4 | E019 | -64.217572% | -64.523765% | +0.365309% |
| c83s4 | backbone | -64.937057% | -65.237109% | -1.635492% |

## Background preservation and locality

Against inherited backbone all three damage/background errors improve. Against E022, c20 background improves0.3605%, but c60 increases0.1560% and c83 increases0.0120%. These latter increases are small measured regressions, not a universal background-preservation result or an equivalence claim. c60's large damage gain is accompanied by a small background cost. c83 loses both damage and background accuracy versus E022, so its result cannot be described as a damage gain transferred to background.

Against E021 allthree full-background errors decrease; against E019 c20 improves but c60/c83 worsen1.0472%/.3653%. Window-inside background vs E022 changes by −3.3292% (c20), +1.2709% (c60), +0.06074% (c83); the small full-background cost is concentrated inside the correction window. These are measured changes, not a statistical equivalence claim. Window-inside background is listed separately below. Saved UV outside compact support is unchanged exactly across the compared arrays (see exterior_pair_drift.json); the producer's roughly1e-16 correction relative to recomputed backbone is floating point evaluation and differs from direct saved-array comparison.

| State | Method | Inside background | Outside background |
|---|---|---|---|
| c20s4 | backbone | 0.000542510846283 | 0.00022693578597 |
| c20s4 | E019 | 0.000487512450446 | 0.00022693578597 |
| c20s4 | E021 | 0.000479504064832 | 0.00022693578597 |
| c20s4 | E022 | 0.000491988855372 | 0.00022693578597 |
| c20s4 | E023 | 0.000475609534456 | 0.00022693578597 |
| c60s4 | backbone | 0.000508114373223 | 0.000254131565043 |
| c60s4 | E019 | 0.000448354163362 | 0.000254131565043 |
| c60s4 | E021 | 0.000509796996624 | 0.000254131565043 |
| c60s4 | E022 | 0.000484548930542 | 0.000254131565043 |
| c60s4 | E023 | 0.000490706911582 | 0.000254131565043 |
| c83s4 | backbone | 0.000372604944382 | 0.000150350128806 |
| c83s4 | E019 | 0.000338142528829 | 0.000150350128806 |
| c83s4 | E021 | 0.000361217025778 | 0.000150350128806 |
| c83s4 | E022 | 0.000344323944213 | 0.000150350128806 |
| c83s4 | E023 | 0.000344533093679 | 0.000150350128806 |

## Integrity, D and portability

Reviewed scientific source c4ceb5d27fa8d408be1b9f02dcd6b10308f301a2, clean producer checkout; deployment28f6aa8801ad0d24660c08a6711d97383936b752. Exact approved two-file transport, one dispatcher1104872 launched2026-10-17T14:50:41Z. Allthree formal preflights finished14:53:44Z; allthree final rows strictly verified, original matrix completed15:39:27Z. All80files/45808770bytes and all33actualproducerarchivecopies verified. All87copied reference/backbone/control files match immutable local originals. No producer retry/source/GPU/budget changes.

Actual10000LR equals expected, all-state formal preflight and each state's original E022/E021 vectors exactly; first.001,last1.0000024427270673e-5,postfinal1e-5,no10001. Three-state own controls/initialization and sampler digests checked. Archived initialD/gradient files match producer all-state preflight; actual finalCP buffers match recorded D/s and original fixed-floor formula exactly.

Original strictMac checker remains **INADMISSIBLE** from native actual-used LR mismatch. It fails before later numerical tests, so it is not a full Mac re-admission. Separate supplementary analysis initially stopped on exactcalibration and then derivedmassdigest mismatches; those failed attempts/logs/commands are retained. The independently reviewed revised supplementary decoder explicitly reports those differences and uses only SHA-bound producer D to decode the actual trained class. This is not substituted Mac D, a strict-check relaxation or a declaration of bit-exact initial calibration. Mass is derived from the unchanged SHA-matched reference; a platform-dependent mass effect on D is plausible but not causally isolated here. Original-tolerance reference-rho numerical exceptions remain in numerical_reload_audit.json and cannot be hidden by UV agreement.

| State | Mass digest equal | Max RMS abs delta | Max D relative delta | Initial calibration bit exact |
|---|---|---|---|---|
| c20s4 | False | 5.55112e-17 | 8.04317e-16 | False |
| c60s4 | False | 1.11022e-16 | 7.12797e-16 | False |
| c83s4 | False | 1.11022e-16 | 1.0835e-15 | False |

## Smallest next step (proposal; no new training)

Retain the measured c60 component gain without promoting E023 as the completed repair. Compare frozen-feature/output-head optimality and damage versus inside-background gradients on **E022/E023 × c20/c60/c83** using both original unscaled physical features and the scaled parameterization: Phi_new=Phi_physical diag(D), B_physical=diag(D)B_new, g_new=diag(D)g_physical (including bias). A reused unscaled manual forward must not omit D or count parameter-gradient rescaling as physical improvement. Read-only Gram/residual/autodiff reductions, no head solve/fitting, no optimizer or additional updates. Ask whether c60's partial gain reduces head nonstationarity and whether c83 retains an optimization bottleneck or instead worsens physical feature quality. Use the existing diagnostic protocol/review route; don't automatically scan D floors, extend training or change LR.

Minimum next repair depends on that discriminator; current data do not identify a single causal AdamW path or prove a reachable .001 c83 ceiling. No new experiment or external submission started. Full FEM teacher remains NOT_QUALIFIED; no damage/history rollout, physical/forecast qualification follows.

## Evidence assets

Exact saved arrays, raw original aggregate and receipts: local_archive/experiments/S04-E023/producer_execution_v1/raw. Recomputations and figures: analysis/; full logs, manifests, command receipts and failedattempts in parent. Independent bounded result review **BOUNDED_EVIDENCE_AUDIT_PASS**, no blockers:45headline/30supportRMS and3manualscaleddecodes independentlyagree. See evidence_review.md; this is not strictMac or scientific-primary PASS. Regional comparison, passive trajectories and all-three-state saved-field maps share this evidence scope; intermediate trajectory points are not checkpoint-replayed. StrictMac result is retained independently.
