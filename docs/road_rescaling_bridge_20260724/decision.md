# Toy-to-Road Rescaling Decision

## Verdict

**Dimensional rescaling is feasible and now testable, but direct toy-to-road
transfer is rejected.** The formal case is a dimensionless mechanism benchmark,
not a miniature road.

The code energy uses

\[
E_d=\frac{w_1}{c_w}\left[w(\alpha)+\ell^2|\nabla\alpha|^2\right],
\qquad w_1=\frac{G_c}{\ell}.
\]

With

\[
\psi_{ref}=\frac{G_c}{\ell},\quad
\sigma_{ref}=\sqrt{E\frac{G_c}{\ell}},\quad
u_{ref}=L\sqrt{\frac{G_c}{E\ell}},
\]

the normalized code parameters are `mat_E=1`, `w1=1`, and
`l0=ell/L`. The previous PCC utility multiplied `w1` by `c_w`; that was
inconsistent with both `config.py` and `compute_energy.py` and is corrected in
this branch.

## Required Similarity Vector

At minimum compare

\[
\left(
\nu,\frac{\ell}{L},\frac{H}{L},\frac{a_0}{L},
\frac{U}{u_{ref}},
\frac{\alpha_T}{G_c/\ell},
\frac{h}{\ell},\eta,R,
\text{AT model},\text{split},\text{plane state}
\right).
\]

For a layered pavement also require layer thickness ratios, stiffness and
fracture contrasts, interfaces, wheel-contact radius and pressure, temperature,
rate or reduced-time groups, moisture and ageing state. These variables do not
exist in the homogeneous brittle toy, so adding them is a model extension, not
unit conversion.

## Offline Result

The formal toy has

- `ell/L = 0.01`;
- `a0/L = 0.5`;
- normalized load `U/u_ref = 0.12`, hence load-energy ratio `0.0144`;
- `alpha_T/(G_c/ell) = 0.5`.

An exact physical realization recovers every declared group. The legacy PCC
illustration does not: `ell/L=0.02`, normalized load is `0.0581`, and the
fatigue threshold is `100`. Its pre-damage threshold/load proxy is therefore
about 854 times the toy value. It is a different fatigue regime, not the same
problem with physical units.

## Reality Observation Contract

| Hidden/model quantity | Required evidence | Boundary |
|---|---|---|
| Geometry and visible crack | registered 2D/3D imaging, cores, GPR | surface images do not identify depth |
| Structural stiffness | FWD deflection bowl, DIC/strain under known load | layer inversion is not unique |
| `G_c` | SCB or DC(T) on cores at declared temperature/rate | cannot be inferred from images alone |
| `ell` | process-zone/image/DIC calibration plus mesh study | model regularization parameter, not a direct sensor reading |
| `alpha_T` and fatigue law | cyclic material/section tests with repeated fields | not fixed by `E` and `G_c` |
| Traffic spectrum | WIM axle/weight/speed sequence | not automatically equal to model cycles |
| Temperature/rate/moisture | environmental sensors and material master curves | absent from current elastic toy |
| Maintenance | intervention records | must reset the state explicitly |

## Producer Gates

The three independent FEM trajectories currently in production remain the
trajectory-generalisation gate. They do not test dimensional similarity.

After those trajectories, the minimum rescaling FEM matrix is:

1. **F1 exact-Pi positive control**: change all physical units/scales while
   preserving the complete dimensionless vector. Normalized damage, history,
   raw driver, active driver, and event state must coincide within discretization
   tolerance.
2. **F2 one-factor negative controls**: perturb `ell/L`, normalized load,
   `alpha_T/(G_c/ell)`, and plane state separately. This measures which mismatch
   changes event timing versus mechanism support.
3. **F3 layered road anchor**: use measured layer thickness, temperature/rate
   dependent material response, wheel load/contact geometry, and at least one
   image plus FWD/DIC observable. It starts a new road model and is not expected
   to reproduce the toy trajectory.

## Claim Boundary

This package supports a corrected scaling contract and a falsification tool.
It does not support road calibration, asphalt validity, traffic-time mapping,
RUL, or real-road forecasting. A model cycle remains a numerical load block
until WIM, environment, and fatigue calibration define otherwise.
