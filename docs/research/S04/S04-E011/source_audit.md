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

E010 stores the accepted-pair UV gradient vector. At the five archived-MATLAB bridge peaks, the NumPy and Torch vectors pass the original MATLAB-vector gate. At the other 13 points, the vector remains a dual-implementation reconstruction and retains `archived_oracle_gate=NOT_AVAILABLE`.

For each point, E011 computes:

```text
native_stagger_sum = ||R_u(u_accepted,d_accepted)||_2,free + phase_residual
native pass        = native_stagger_sum <= 4e-4

teacher rho_u      = (Us/Es) * sqrt(sum_i R_i^2 / m_i)
teacher pass       = rho_u <= 1e-3
```

The two gates use different norms, scales, and tolerances. This is the main explanation for the apparent contradiction between `converged=true` and teacher-screen failure. It does not by itself explain which part of the remaining accepted-pair residual was created by the last damage change; genuine last-iteration fields would still be needed for that attribution.

