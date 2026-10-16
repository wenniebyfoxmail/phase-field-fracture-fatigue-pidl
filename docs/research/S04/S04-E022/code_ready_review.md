# Independent Code Ready review: S04-E022

Verdict: CODE_READY_PASS, bounded to source a540888497d1838a6aa202f59a884e6930e50fb4 and protocol 20261016-r1-last-hidden-leak001. This is implementation readiness only; no producer preflight, execution authorisation or scientific success is established. No blocking findings remain.

## Scope and implementation

Reviewed the new helper, runner, strict aggregator, three-state pairing/control locks, experiment/implementation records and nontraining checks against unchanged E021 originals. The sole learned-model behavior change is residual.activations[7]: F.leaky_relu(coeff*pre, negative_slope=.01); original trainable coeff Parameter is retained. First seven actual classes, tensor names/initial values, parameter counts, backbone, physical window/BC and E021 coordinate maps are unchanged. A fixed slope has no tensor-state identity, so explicit eight-layer activation manifests are correctly required in all four envelopes and actual leaky reconstruction is checked during decoding.

Same-state c20s4/c60s4/c83s4 each use their own E017 backbone, original zero-output residual initialization, E021 localized direct control and E019 localized common comparator. Nine-file direct locks preserve exact historical source/run/files. Historical-byte/UV admission does not assert full strict Mac replay. Direct original native LR vector equality and formal runtime identity are enforced before candidate optimizer construction; strict aggregate also compares candidate actual rates against admitted direct-file rates. Formal runtime mismatch is not waived by local checks.

Runner retains original unbiased full-mass objective, alpha .7, seed7, fixed 10000 new updates, PRE_UPDATE before updates, optimizer then scheduler, no resume or best-step selection, and final10000 scoring. Last used LR exceeds 1e-5 slightly; only post-final scheduler is 1e-5. No update10001. Existing input/backbone/physical/BC/stream/archive checks remain. Primary all-three full UV <=.001 is separate from damage/background component flags and secondary strain/rho.

## Corrected issue

Initial commit5c2b30f derived the historical coordinate map from CPU-recomputed backbone UV. The residual-moment rule is backend-sensitive, so this could reject correct frozen maps. Root found it with real assets; fix488e887 requires the exact saved E017 UV argument in all three callers. Reviewed the fix and final a540888 check script. Original E021 rule, map locks and tolerances are unchanged. The initial failure log is preserved. This is resolved, not a relaxed comparison.

## Independent checks actually run

- Final exact a540888 unit activation/LR/manifest/scoring/step-order suite: 11 passed in1.04s. No parameter optimizer.step.
- Independent real pinned-asset admissions for all three states: own control/reference/map/backbone admission, new-vs-original initialized tensor digest equality, exactlyzero output correction and exact initial saved field equality passed. All three Mac-native vectors differ from original formal profile, as expected; no producer admission claimed. Details independent_real_admission.json.
- Earlier 5c2b30f-import combined suite: 27 passed in104.67s (synthetic full-decoder c20 fixtures plus unit checks); this is supplemental, not labelled final exact-commit full-suite evidence.
- Reviewed strict-decoder tamper fixtures for maps, PRE_UPDATE counters/time, activation config, direct identity/rates, candidate UV and secondary numerical diagnostics. Their fabricated completion metadata and Mac-native expectation substitution are explicitly test-only. Actual production prepare_baseline reads formal original rates.
- Verified original E021 runner/helper/strict decoder, coordinate_maps.json and E019 common locks have no diff from98c6206. Final review began with clean a540888.

## Limits and next boundary

Read-only review; no SSH, transfer, external message, training or parameter update. Real three-state checks reload and evaluate existing assets; they do not establish candidate fit. Original E021 primary failure and strict Mac native-LR/reference-rho exceptions remain. Production plan/resource preflight and exact final package are separate work. Later material code/config/lock/protocol changes require renewed review; documentation-only status updates do not modify reviewed scientific behavior.
