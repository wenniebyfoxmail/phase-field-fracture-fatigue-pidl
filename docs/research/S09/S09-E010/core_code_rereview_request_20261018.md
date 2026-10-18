# S09-E010 focused core rereview request

Please perform a focused rereview of the attached S09-E010 core revision.

Identity:

- exact commit: `45d8ec5f158d6fbdc608437f02da4fa43501157f`
- ZIP: `S09-E010-core-rereview-45d8ec5f158d-20261018.zip`
- bytes: `65,403`
- SHA256: `6a74c285ae2a5938dea33f67f3d9db5990bf01cd5838361988b29b7d3e36905f`
- manifest content files: `14`

First verify the ZIP identity and every manifest file hash and byte count.
Review only whether the two Round-1 blockers are closed without regression:

1. F1: `_validated_auc` now returns the canonical value reconstructed from
   validated integer `2W+T` counts. The consistency tolerance remains only an
   input validation rule. A regression compares `0.8` and
   `math.nextafter(0.8, 0.0)` for identical `20/0/5` counts.
2. F2: the frozen 16-cycle no-step loop independently recomputes `L_S/L_A`
   with separate NumPy float64 expressions, checks each against a fixed
   `1e-12` absolute tolerance, and records per-cycle and maximum differences.
   It reuses the existing forward output and performs no additional forward,
   optimiser construction or step.

Local evidence to verify rather than assume:

- selected E010 plus inherited E009 suite: `62 passed`;
- `NO_STEP_PREFLIGHT_PASS` on all 16 frozen cycles;
- maximum independent-reference absolute difference:
  `L_S=2.842170943040401e-14`, `L_A=3.469446951953614e-17`;
- A25 exact direction maximum difference: `0`;
- B25/B0 preclip physics residual:
  `1.3704315460216776e-16`;
- model hash unchanged; optimizer steps: `0`.

The optional standalone nonzero-`L_A`-gradient suggestion was also added. The
separate suggestion to intercept the real clip input remains optional unless
you can provide a new blocking counterexample; do not turn an optional
improvement into a blocker without one.

Return `CORE_CODE_READY_PASS` on the first line if F1/F2 are closed. State the
exact commit and what you independently reproduced. A pass allows only
runner/config/evidence integration and further no-training verification. It
does not authorise training, holdout access or producer launch.

Otherwise return `REVISE_AND_REREVIEW` and provide the blocking file/function,
minimal reproduction, expected and observed behaviour. Keep optional
improvements separate.
