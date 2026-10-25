# FN776-r8 deployment closure

This package is the r8 finite-precision repair following r7's terminal
actual-head/basis-gradient equivalence assertion. It preserves the five input
identities, continuous mechanics, rank-388 basis, 776 coordinates, tolerances,
seed, Armijo rule and full-rank TSQR tangent factorization.

The producer evaluates the UV objective from the frozen network's actual
three-output `nn.Linear` head, constructed differentiably from the fixed hidden
features and the `transform @ z` UV update. It applies the fixed legacy
boundary map in the same order as `FieldComputation.fieldCalculation`. The
ordinary materialized network head remains an independent check. Zero, probe
and final diagnostics are written before their strict field, branch and
materialized-force-VJP assertions.

The TSQR factor still represents the same 776-coordinate tangent operator.
For each Newton solve, its triangular right hand side is reconstructed from the
current canonical actual-head AD gradient. The augmented-basis projection is
recorded only as a finite-precision diagnostic; it is not used to decide the
accepted direction. The strict canonical triangular transport residual,
independent HVP control, linear residual, descent and Armijo checks remain in
place.

r7 consumed 7,787 of the task's 25,424 work units. r8 may consume only the
remaining 17,637: 17,072 curvature units (at most 11 complete slots), 45
controls, 507 trials and 13 final units. It has no self wall-time, RSS, CUDA or
output-size cap. Shared-machine protections remain the exact GPU7 three-service
identity set, 12 GiB admission and 4 GiB runtime free-GPU margins, 16 GiB host
RAM and 5 GiB `/mnt/data2` free space.

The package contains only code and text. It excludes the local synthetic
benchmark and all scientific payloads. The future producer hashes the five
approved inputs once and decodes only the contract-listed fields. One r8 guard
launch is permitted; any scientific or numerical terminal state stops without
automatic retry.

The full canonical JSON contract identifier is
`a79de9464c4057caa9ea6096785a17ab4601a43f5061a868d093be571f5aee17`.
The code package provenance, literal SSH preflight, deployed contract, guard,
launch receipt and retrieval verification must all bind this same identifier.
