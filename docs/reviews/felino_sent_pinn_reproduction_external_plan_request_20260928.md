# External planning request: Felino SENT PINN reproduction

Review the preregistration in
`docs/experiments/felino_sent_pinn_reproduction_track.md`, the frozen contract
in `SENS_tensile/felino_sent/contract.json`, and the implementation diff before
authorizing any producer run.

Please answer:

1. Is a small-strain plane-strain PINN an acceptable first diagnostic against
   the finite-strain Felino deck at `umax=0.0005 mm`, or must finite-strain
   kinematics be implemented before training?
2. Are the implemented spectral split, AT2 normalization, residual stiffness,
   ICLA drive, cycle jump, fatigue degradation, initial notch, and essential
   boundary conditions equation-consistent with the locked Felino inputs?
3. What single primary scalar gate and single primary field gate should be
   frozen before the run? Propose thresholds with a numerical or scientific
   basis rather than choosing them after observing PIDL results.
4. Which checkpoints are sufficient? The current proposal is cycles 100,
   10k, 15k, 25k, 37k, and 38k.
5. Is one seed acceptable for code-path diagnosis, and if so what evidence is
   required before any claim-bearing multi-seed extension?
6. Identify any implementation defect or missing observable that should block
   Taobo execution.

Requested verdict: `APPROVE_TOOLING_SMOKE`, `REVISE_BEFORE_SMOKE`, or
`REJECT_ROUTE`. This request does not ask for teacher/corpus authorization.
