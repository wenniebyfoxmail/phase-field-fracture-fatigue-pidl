# S09-E011 result-evidence review request

Review the completed frozen run `S09-E011-R001-objective-only-ranking`.

## Identity to verify

- Reviewed producer commit:
  `ee9d62d5604c35ee66a4838b8c7333b4f9b41359`
- Run-config SHA256:
  `41dd49aa5a713c93e1bc5d2997c50f54102b3f84215f65d492e3b6db3540ab25`
- Protocol SHA256:
  `9ade1eb0034c28af29641a0bb4ef457878d802442d8d467c28bff40cc2775e3c`
- Source B25 checkpoint SHA256:
  `24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05`
- Packet manifest SHA256:
  `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`
- Producer: `GPUServer8`, `CUDA_VISIBLE_DEVICES=5`, physical UUID
  `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`.

Verify the package and manifest before reviewing the result. The package
contains the complete 23-file producer output except that the two small
checkpoint binaries may be represented by their signed hashes if a focused
package is used. It also contains the remote run manifest/size record, analysis
script, derived figures and this request.

## Required review

1. Recompute the completion status from both arm receipts, log/evaluation
   coverage, artifact hashes, total update count, deadline and absence of a
   failure receipt.
2. Recompute update-500 pair score/AUC from per-cycle amplitudes and verify the
   prespecified classifier, protected ratios and status
   `NO_REALISED_RANKING_REPAIR`.
3. Check the realised-pair accounting: control repairs/losses and candidate
   repairs/losses relative to the common update-0 state.
4. Check the metric trajectory statement that candidate pair score remains 34
   at every frozen evaluation while control reaches 40 only at 496/500.
5. Verify that the raw field archive reconstructs the reported weighted
   amplitudes and that all producer figures use the declared shared scale.
6. Audit the interpretation that total fields are dominated by supplied
   pre-state damage, whereas increment fields show a localised FEM event and
   diffuse learned damage. Recompute the cycle-73 support fractions in the
   analysis if possible.
7. Review the proposed no-training pair-contrast audit. Distinguish evidence
   supported conclusions from hypotheses; do not treat a low-rank Jacobian by
   itself as proof that the head must change.

## Claim boundary

This is an objective-only continuation on the same exposed 16-cycle synthetic
development trajectory. It is not a fresh holdout, rollout, transfer,
FEM-teacher validation, real-road result, or full fracture-evolution PINO
claim. No retry, additional training or holdout access is requested.

The first line must be `RESULT_EVIDENCE_READY_PASS` or
`REVISE_AND_REREVIEW`. If revising, separate blocking evidence defects from
optional next-study improvements and provide file/field plus expected/observed.
