# c87 Observation Ladder for Hidden Fracture State

## Decision

On the locked, single eta0 SENS trajectory, the lowest-cost predeclared
observation tier that passes all sealed c89 mechanism gates is **10% adaptive
raw tensile-energy probes at c87**, reconstructed by a fixed graph-Laplacian
latent-state analysis and then forecast by the unchanged frozen c87->c89
multiscale operator.  At zero synthetic noise it gives active log-MAE `0.0727`,
correlation `0.9266`, FEM-p99 IoU `0.9356`, support-area ratio `0.9402`, and
own-p99 IoU `0.9593`.  With the fixed 10% log-domain sensor-noise stress it
still passes: `0.0825`, `0.9239`, `0.8964`, `0.9477`, and `0.9185`.

This is a conditional **state-estimation / two-cycle forecast** result, not
material-parameter identification or a laboratory DIC result.  The raw probe
is an oracle/synthetic channel here.  A real implementation must infer it from
registered DIC displacement/strain using a declared strain reconstruction and
tensile constitutive split; raw tensile energy is not a directly measured DIC
quantity.

## Important negative results

- Reaction force plus a crack image/mask fails despite good support overlap:
  c89 active correlation is `0.8714 < 0.90`.  Therefore event or geometry
  agreement does not identify near-core raw/degradation amplitude.
- Process-zone raw coverage at 10% fails (`correlation=0.8948`), while 25%
  passes (`0.9713`).
- Uniform DIC/strain-derived raw grid at 25% narrowly fails (`0.8994`), so a
  low raw residual or near-threshold IoU is insufficient for promotion.
- Adaptive sparse probes at 5% fail (`0.8968`); the observed transition lies
  between the predeclared 5% and 10% tiers for this mesh and prior.

## Identifiability boundary

The ladder reconstructs only the c87 raw channel from observations.  Damage,
history, fatigue degradation, and derived `g(d)` remain conditional on the
graph-informed c86 transition prior.  Hence it demonstrates that this prior
plus sparse energetic information can distinguish a mechanically wrong
event-aligned state from a FEM-like c89 energetic support state in this one
trajectory.  It does **not** prove that the full hidden state or
`(Gc, ell, fatigue parameters)` is uniquely identified.

The synthetic 90% c89 raw coverage is `0.983` for noisy full field, but only
`0.241` for 25% process-zone raw and `0.094` for 10% adaptive sparse probes.
The sparse ensemble is under-dispersed and is not calibrated uncertainty.

## Sealing and scope

All placements, fractions, methods, and noise levels were predeclared.  Each
c87 analysis uses only c87 observations plus the earlier transition prior; the
c89 state is indexed only after per-configuration forecast artifacts and
`PRE_EVALUATION_LOCK.json` are written.  The full result is a single-trajectory
synthetic diagnostic and remains quarantined from cross-trajectory or clinical
claims.

Artifacts are local under
`local_archive/.../analysis/inverse_fracture_state_assimilation_20260718/`:
the manifest, metric table, uncertainty table, Pareto curve, sparse field, and
FEM-p99 support-overlap figure.
