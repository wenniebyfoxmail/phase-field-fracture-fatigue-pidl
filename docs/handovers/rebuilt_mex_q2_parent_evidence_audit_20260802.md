# Rebuilt-MEX Q2 parent evidence audit

Date: 2026-08-02

## Decision

Q1 is accepted. Q2 remains blocked, and the current historical U0.12 archive
cannot supply the two missing fields without changing the predeclared field
semantics or introducing a reconstruction assumption.

The current state remains:

```text
EvidenceLockUnsealed
T1 = not started
T2 = not started
T3 = not started
```

This is a parent-evidence limitation, not a new failure of the rebuilt MEX.

## Accepted Q1 evidence

- 8/8 index vectors are exact.
- Stiffness relative Frobenius error: `1.4374484646311128e-16`.
- Deterministic internal-force probe relative L2: `1.7835846492874314e-16`.
- Rebuilt `initial.mexw64` SHA-256:
  `ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db`.

Q1 establishes equivalence of the rebuilt initialization/assembly binary for
the locked independent MATLAB Q4 probe. It does not by itself establish
cycle-level fracture-field equivalence.

## Historical parent inventory

Parent identity:

```text
hard5_eta0_u012_5step_20260729
cycle 1
86408 Q4 elements
five retained substeps: 0.25, 0.50, 0.75, 1.00, 0.00
```

The locked cycle-1 MAT, SHA-256
`72925ac353f766475862858befcc611307e71faa392eb774d7ce5aa8a40d74d9`,
contains only four element arrays:

```text
d_elem
alpha_bar_elem
f_alpha_elem
psi_elem
```

It contains neither `g_elem` nor `psi_active_elem`, and it contains no GP
`g_gp`, `psi_raw_gp`, or `psi_active_gp` arrays. The terminal checkpoint has
GP history only for its terminal state, not cycle 1. Native-Q4 staging exists
only for cycles 76, 87 and 89. The U0.11 and U0.13 cycle-1 native packages are
different load-amplitude trajectories and cannot substitute for U0.12.

The original cycle-1 peak VTK, SHA-256
`acdc981269024cbb111f7d468c287f2d1ca09f3735131b56aca7fa2fbaec1615`,
contains nodal `u` and `d`. The cycle-end VTK, SHA-256
`f1a2fcf746cba4215f2d4ddc7078d9862bb1b4f863378161f5de4fecd45cb3fa`,
also contains nodal L2-projected `driver_degraded`. Neither is the required
four-GP element payload.

## Why peak-state reconstruction does not qualify

A read-only independent Q4/AMOR reconstruction was applied to the original
cycle-1 peak VTK as a feasibility check. Its element-mean raw driver was
compared with the locked historical `psi_elem`:

| diagnostic | value |
|---|---:|
| raw relative L2 | `1.0594087e-2` |
| raw MAE | `1.0873032e-2` |
| raw maximum absolute error | `2.5211498e2` |
| raw correlation | `0.99994374` |

The mismatch is structured rather than a file-reading error. Historical
`psi_elem` is the element mean of a per-GP maximum accumulated over the five
retained substeps. One peak nodal state cannot recover each GP's earlier
substep maximum. The other four substep nodal states were not archived.

As an additional non-authorizing check, reconstructed peak
`mean_GP(g_gp * psi_raw_gp)` was compared with `alpha_bar_elem`. The relative
L2 error was `0.18814` and maximum absolute difference was `0.11170`.
History therefore cannot be relabelled as the missing active field.

The cycle-end nodal `driver_degraded` field is an L2 projection from GP history
to nodes. Mapping four GP values per element to one shared nodal field is not
one-to-one, so it cannot be inverted into the locked active quantity.

Therefore all of these remain prohibited:

```text
f_alpha_elem as active
(1-d_elem)^2 as g_elem
(1-d_elem)^2 * psi_elem as active
mean(g_gp) * mean(psi_raw_gp) as active
inverse projection of nodal driver_degraded as exact GP active
```

## Permitted routes

### Route A: recover original parent bytes

Search the original Windows producer storage for an immutable U0.12 cycle-1
payload containing all five retained substeps and native arrays sufficient to
compute exactly:

```text
g_elem = mean_GP(g_gp)
psi_active_elem = mean_GP(g_gp * psi_raw_gp)
```

The payload must be bound to the locked parent mesh/order, cycle/state labels,
source/runtime identity and SHA-256 manifest. If found, add it only through a
new reviewed supplement lock and rerun Q2 from a fresh output root.

### Route B: version a new synthetic-family baseline

If Route A is unavailable, do not weaken Q2 after seeing the blocker. Close
historical Q2 as `historical_q2_parent_irrecoverable` and create a new protocol:

1. Run an unmodified U0.12 parent `P0` with the Q1-qualified rebuilt runtime.
2. Export native GP `d`, raw, `g` and active at every retained substep and
   coherent cycle peak from cycle 1 onward.
3. Repeat the identical parent as `P0R` from a fresh root and require the
   predeclared repeatability gates before any variant.
4. Run T1, T2 and T3 strictly against P0 with the same runtime and exporter.
5. Keep the historical U0.12 run as an external comparison only for fields and
   events it actually saved; do not call P0 backward-equivalent on active
   support.

Route B supports a new internally consistent synthetic transfer family. It
does not retroactively pass the original Q2 or prove real-road validity.

## Cross-machine source visibility

The earlier `invalid_repo_sync` arose because a producer checked a mutable
`origin/main` snapshot that did not yet contain the registry path. It is now
resolved on remote main at:

```text
remote commit: 389f618b7a042e0a4e4d11a3ab24a7164f6902cc
registry path: docs/pidl_experiment_inventory.md
registry blob: d0eeb933ddee3674bd72aa7e0c9e1c3b76241305
required case: hard5_c5_temporal_accumulation_gate_20260731
```

Every future producer handoff must record and recheck the exact remote commit,
path, blob SHA and exactly-one case row before creating a worktree or process.
`origin/main` by name alone is not a source lock.
