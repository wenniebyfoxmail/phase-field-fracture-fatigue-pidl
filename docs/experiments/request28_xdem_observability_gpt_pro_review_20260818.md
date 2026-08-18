# Independent GPT Pro review — Request 28 XDEM observability gate

Date: 2026-08-18

Thread: `State-Conditioned Transition` (`6a832f5d-f740-83ed-b14e-340dd46da2ff`)

Verdict: **FREEZE only as a two-latent retrospective observability diagnostic.**

The independent review permits exactly three Hard-5 trajectory units and
rejects treating mesh cells or nodes as independent samples.  It freezes:

- hidden targets from the prior `c-1/s5` post-commit state:
  `z_H = sum(A*w*alpha_bar)/sum(A*w)` and
  `z_F = sum(A*w*x_forward)/(L*sum(A*w))`, where `w=4*d*(1-d)`;
- PLAIN event-displacement observables: forward-ligament Q4 strain RMS and
  its squared-strain centroid;
- ENRICHED event-displacement observables: crack-axis antisymmetric normal
  opening-density RMS and its squared-opening centroid;
- one scalar predictor per scalar target, using only the unique two-point
  affine calibration in each leave-one-Umax-out fold;
- training-mean and Umax-only null controls;
- fail-closed monotonicity, matching, and 3/3 per-target comparisons.

The displacement representations may use only the event `s4` `u_node`, native
mesh, and declared initial crack.  They may not inspect prior damage/history,
FEM crack tips, target fields, error maps, target percentiles, or tuned ROIs.

A pass would establish only that event-peak crack-oriented kinematics retain
more retrospective information about the immediately preceding two physical
coordinates than plain gradients and load amplitude.  It would authorize a
sparse earlier-origin FEM observability diagnostic, not early-warning, RUL,
full-state inversion, KAN training, or cross-geometry generalization.
