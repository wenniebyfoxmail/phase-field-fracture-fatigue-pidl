# Toy-to-Road Independent FEM Producer Design

Date: 2026-07-31

## Scope

This design seals three independent synthetic FEM trajectories derived from the
latest accepted 2026-07-29 Hard5 U0.12 baseline. The parent event identity is
`first_hit=83` and `confirmed=86`. The trajectories support a synthetic
whole-trajectory LOTO study only. They are not road validation and do not
authorize PIDL training.

Request 26/F1b remains separate. It uses the older c86/c89 reference as an
exact-Pi scaling diagnostic and is not a parent for T1, T2, or T3.

## Fixed Parent Contract

All three trajectories retain these parent values unless the case-specific
variation table explicitly changes one:

- hard-tip, zero-load hard recovery from a fresh state;
- five retained substeps with nominal factors `[0.25, 0.50, 0.75, 1.00, 0]`;
- `Umax=0.12`, `R=0`, `eta=0`;
- `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`;
- `alpha_T=0.5`, `p=2`, plane strain, AMOR, AT1 history fatigue;
- reverse top/bottom displacement boundary condition;
- displacement tolerance `1e-6`, phase tolerance `4e-4`, and staggered
  tolerance `4e-4`;
- no line search and no cycle jump;
- event evaluated at cycle peak using at least three connected or adjacent
  right-boundary nodes with `d>=0.95` and `x>=0.48`;
- `first_hit` is the first satisfying cycle; `confirmed` is recorded only after
  the three post-hit confirmation cycles also satisfy the rule;
- stop at `confirmed`, otherwise right-censor at the predeclared cap `150`.

No parameter may be changed after a trajectory starts or after its event timing
is observed.

## Independent Variation Axes

### T1: Initial-Defect Geometry

T1 changes only the physical initial-notch geometry:

| Quantity | Parent | T1 |
| --- | ---: | ---: |
| `a0/L` | 0.5 | 0.625 |
| notch start | `(-0.5, 0)` | `(-0.5, 0)` |
| notch tip | `(0, 0)` | `(0.125, 0)` |
| orientation | `0 rad` | `0 rad` |

The original mesh contains conforming notch-line nodes only through `x=0`.
T1 is therefore declared a geometry-transfer trajectory. It retains the parent
Q4 connectivity and ordering while creating candidate coordinates with the
piecewise-affine map

```text
x' = -0.5 + 1.25*(x + 0.5), x <= 0
x' =  0.125 + 0.75*x,       x > 0
y' = y
```

The map fixes both external x boundaries and maps the existing conforming notch
tip to `x=0.125`. Before sealing, a mesh audit must verify positive Jacobians,
unchanged node/element counts and connectivity, exact boundary coordinates,
and every mapped notch-tip incident-edge length divided by its corresponding
parent incident-edge length in `[0.75, 1.25]` with tolerance `1e-12`. Absolute
parent and mapped local `h/ell` ranges are audit evidence only and never drive
the gate. Edge correspondence is deterministic from Q4 connectivity, and a
zero-length parent edge fails before division. The input lock records the exact
affine factors and relative gate limits. Failure of any mesh audit blocks T1
before execution.

### T2: Fracture-Material State

T2 changes only `Gc`:

| Quantity | Parent | T2 |
| --- | ---: | ---: |
| `Gc` | 0.01 | 0.008 |
| `Gc/(E*ell)` | 1.0 | 0.8 |

`E`, `nu`, `ell`, fatigue-law parameters, geometry, mesh, boundary condition,
loading, cadence, eta, event rule, and all numerical tolerances remain fixed.
The lower toughness is predeclared to reduce expected producer time; it is an
intentional material holdout and not an exact-Pi control.

### T3: Physical Loading History

T3 changes only cycle-level physical amplitude:

| Cycles | `Umax_N` | Scale from parent |
| --- | ---: | ---: |
| 1-30 | 0.108 | 0.90 |
| 31-60 | 0.126 | 1.05 |
| 61-150 | 0.120 | 1.00 |

Each physical cycle still uses the same five-substep cadence and `R=0`. The
runner records physical cycle, `Umax_N`, branch, retained substep, and raw step.
No block may be reordered or strengthened to accelerate the observed event.

## Producer Architecture

One sealed handoff directory contains a shared read-only export solver, three
case drivers, three independent input locks, a family lock, tests, a PowerShell
launcher, and a source manifest. The three cases may share one source commit,
but each execution receives a new immutable output root and its own input
snapshot, producer provenance, event metadata, cycle index, mesh package, and
state files.

The launcher must:

1. verify every sealed source/input hash;
2. require the declared clean source commit and a clean GRIPHFiTH producer;
3. verify the parent package and source hashes;
4. refuse an existing output root or any checkpoint/resume input;
5. run exactly one selected case;
6. write provenance only after the MATLAB process returns successfully;
7. leave failed roots labelled as failed producer attempts, never accepted
   trajectories.

The shared solver is a run-local derivative. It may export read-only state and
select the predeclared cycle amplitude, but it must not change constitutive
assembly, history evolution, Newton tolerances, or event thresholds.

## State and Mesh Payload

`mesh_geometry.mat` stores node coordinates, Q4 connectivity, element material
IDs, element centroids and areas, quadrature data, ordering declarations, and
the mesh hash. T1 additionally stores parent coordinates, candidate coordinates,
and the mapping contract.

Every cycle-peak `states/cycle_NNNN.mat` stores:

- nodal displacement components `u` and `v` and nodal damage `d_node`;
- element damage `d_elem`, `alpha_bar_elem`, `f_alpha_elem`;
- element `psi_raw_elem`, `g_elem`, and `psi_active_elem`;
- element strain summaries and strain-energy summaries;
- top and bottom reaction/resultant values;
- binary crack masks at thresholds `0.50`, `0.75`, `0.90`, and `0.95`;
- crack-tip and connected-right-boundary diagnostics;
- cycle, `Umax_N`, peak substep, raw step, branch, and mesh/state ordering IDs.

Native GP values are used to derive element means. The exported active driver
must satisfy `psi_active_elem = mean(g_gp .* psi_raw_gp, 2)`; it must not be
constructed as the product of two independently averaged element fields.
Latent FEM truth fields are labelled as latent and never as direct road sensors.

`cycle_index.csv` provides one row per exported peak and names the exact state
file. Dense VTK output is disabled because it is not part of the contract and
would add producer I/O time.

## Validation Gates

Before a case can be marked complete:

- all state files load and all numeric fields are finite;
- damage lies in `[0,1]` within the locked numerical tolerance;
- damage and `alpha_bar` satisfy their declared irreversibility semantics;
- `f_alpha` and `g` lie in their legal ranges;
- raw and active drivers are non-negative within tolerance;
- active-driver recomputation agrees with the exported field;
- cycle/state indexing is consecutive from c1 through the terminal cycle;
- all states use a stable mesh/order hash;
- event metadata points to an existing cycle-peak state;
- `first_hit` and `confirmed` remain separate;
- exactly one declared primary variation axis differs from the parent;
- a fresh-copy SHA-256 verification passes for the complete package.

The family root is `toy_to_road_independent_fem_20260731`. T1, T2, and T3 are
stored in separate child roots and are never merged with previous Umax,
hard/soft-tip, or five/eight-substep archives.

## Testing and Execution Order

Tests cover input-lock validation, single-axis diffs, T1 mesh mapping and
quality gates, T3 block boundaries, active-driver semantics, event state
transitions, immutable output refusal, and package hash verification. A
five-cycle non-production dry run may be used only before sealing to prove I/O
and event bookkeeping; it is not a trajectory result.

After all tests pass, source files and locks are hashed and committed. The
sealed commit is pulled into a fresh LF-preserving producer checkout. T1, T2,
and T3 then run sequentially, with a new clean-commit and no-existing-process
check immediately before each solve.
