# S09-E010 update-500 field visualisation

These are read-only reconstructions from the three verified update-500
checkpoints and the frozen 16-cycle packet. The script performs zero optimiser
steps and reproduces the archived weighted amplitudes to a maximum absolute
difference of `4.0657581468206416e-20`.

`cycle69-three-arm-increments` uses one physical colour scale across FEM,
`A25`, `B25`, and `B0`, then per-panel normalisation for shape only. FEM places
the event at the crack tip. `A25/B25` are much smaller and concentrate toward
the right boundary; `B0` is larger and diffuse.

`cycle73-final-fields` explains why the total fields look good: each prediction
inherits the supplied pre-state crack. The lower row isolates the newly
predicted damage and exposes the remaining magnitude and location errors.

The GIF covers stored selected-cycle transitions. Every frame is an independent
mapping from that cycle's `s00` state to its `s04` peak. No model predictions
exist here for within-cycle states `s01/s02/s03/s05`.

