# Source and state-semantics audit

The original Stage0b solver source is commit `53ce560b6d20b336d6ec92ccf56ed2b230e804ce`. The producer copy of `Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m` has SHA-256 `6313b4ad7b1bd7bbad6a1b793d6b54992bcf4d97089c82a81b360567e2c965b0`. It is byte-identical to the previously retrieved source-evidence copy in `local_archive/experiments/S04-E003/source_evidence/post_iter_update.m`. The current GRIPHFiTH checkout has a different hash and is not used as source evidence.

The actual accepted-state path is:

1. Solve UV at the current staggered damage.
2. Solve damage, then enforce the nodal lower and upper bounds.
3. Call `stag.post_iter_update` with the updated damage and current UV.
4. In `post_iter_update`, call `assembly_equilibrium_fh` again on that accepted pair, subtract traction, and compute the raw Euclidean norm on `active_dof`.
5. Accept when `raw_uv_l2 + phase_residual <= 4e-4`.
6. Export the state and commit history only after that acceptance.

Therefore Stage0b does not simply reuse the pre-damage UV Newton residual as its staggered acceptance test. The `producer_metadata.equilibrium_residual` stored by the Stage0b hook is nevertheless the scalar returned by the preceding UV Newton call, because the recomputed norm is not returned from `post_iter_update`. That metadata scalar must not be treated as the accepted-pair residual.

The four residual fields used in this audit have distinct roles:

- `accepted_pair_raw_uv_l2`: Euclidean L2 norm of the accepted-pair equilibrium residual after traction subtraction, restricted to `sys.DOFS.active_dof`; no mass weighting or `Us/Es` scale.
- `native_phase_residual`: archived scalar returned by the phase-field Newton solve and passed into `post_iter_update`. The producer then applies `p_field = max(p_field,p_field_old)` and the optional upper bound before the staggered check. The source evidence does not show a phase residual reassembly after those bounds, so this is not a projected accepted-pair phase residual and is not the E010 hard-KKT L2.
- `native_stagger_sum`: posterior reconstruction of the source expression `accepted_pair_raw_uv_l2 + native_phase_residual`; a final accepted sum was not separately archived.
- `rho_u/raw_uv_l2`: ratio of the later mass-dual scaled UV metric to `accepted_pair_raw_uv_l2`, not to `native_stagger_sum`. It depends on the vector's spatial distribution over nodal masses and is not a universal conversion.

E010 stores the accepted-pair UV gradient vector. At the five archived-MATLAB bridge peaks, the NumPy and Torch vectors pass the original MATLAB-vector gate. At the other 13 points, the vector remains a dual-implementation reconstruction and retains `archived_oracle_gate=NOT_AVAILABLE`.

For each point, E011 computes:

```text
native_stagger_sum = ||R_u(u_accepted,d_accepted)||_2,free + phase_residual
native pass        = native_stagger_sum <= 4e-4

teacher rho_u      = (Us/Es) * sqrt(sum_i R_i^2 / m_i)
teacher pass       = rho_u <= 1e-3
```

The two gates use different norms, scales, and tolerances. For the 18 sampled residual directions, the ratio `rho_u/raw_uv_l2` is about `4.17e3–4.44e3`, which maps the teacher threshold to a raw UV L2 of roughly `2.25e-7–2.40e-7`; this range must not be generalized beyond the sampled directions. This is the main explanation for the apparent contradiction between `converged=true` and teacher-screen failure. It does not by itself explain which part of the remaining accepted-pair residual was created by the last damage change; genuine last-iteration fields would still be needed for that attribution.
