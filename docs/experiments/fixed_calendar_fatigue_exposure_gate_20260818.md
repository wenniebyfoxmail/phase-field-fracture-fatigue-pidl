# Fixed-calendar fatigue-exposure gate

Date: 2026-08-18

Status: **frozen; blocked on nine exact FEM peak states**

## Five-question gate

1. **Mechanism question**: can peak displacement define a load-normalized
   deformation-exposure coordinate that explains hidden fatigue state and
   remaining life better than a simple load-times-clock null?
2. **Success claim**: the frozen observable carries transferable fixed-calendar
   fatigue/timing information within this three-Umax Hard-5 family.
3. **Failure claim**: close the fatigue-exposure coordinate; do not rescue it
   with fitted powers, another ROI/norm, a later cycle, or a neural model.
4. **Cheaper diagnostic**: audit retained assets, validate the c1 reference
   plumbing, and describe c10/c20/c40 hidden-state ordering before any replay.
5. **Minimum asset**: nine indexed s4 peak states, one deterministic analysis,
   fold-level CSV, manifest, decision, and attempt ledger.

Claim class: `field-mechanism` plus narrow `trajectory-sufficiency` diagnostic.
No PIDL training or FEM-to-reality claim is authorized.

## Frozen FEM observations

| Umax | fixed cycles | required state | first detect, descriptive only |
|---:|---|---|---:|
| 0.11 | c10, c20, c40 | s4 peak post-commit | c122 |
| 0.12 | c10, c20, c40 | s4 peak post-commit | c83 |
| 0.13 | c10, c20, c40 | s4 peak post-commit | c59 |

c0/state0 is initialization. c1/s4 is the empirical reference. c50 is
forbidden in this gate. Confirmation cycles are forbidden.

## Frozen observable

For each Umax and cycle N:

```text
u_res(N) = u_s4(N)/Umax - u_s4(c1)/Umax
ell = 0.01
h_e = median sqrt(native Q4 area)
h_ROI = max(4*ell, 2*h_e) = 0.04
Omega_L = {cell centre x >= 0 and |y| <= h_ROI}
A_u(N) = sqrt(sum_Omega A_i ||sym(grad u_res)_i||_F^2 / sum_Omega A_i)
```

Each trajectory uses its own c1 reference. It must be called
`within-trajectory c1 normalized reference`, not healthy elastic ground truth.
The unsubtracted `u_s4(N)/Umax` amplitude is a mandatory null. No hidden FEM
field, event tip, percentile, fitted mask, or event peak enters the observable.

## Frozen exposure candidates

Only two candidates exist:

```text
z_E_inst(N) = N * A_u(N)
z_E_cum(c10) = 0
z_E_cum(c20) = 0.5 * [A_u(c10)+A_u(c20)] * 10
z_E_cum(c40) = z_E_cum(c20) + 0.5 * [A_u(c20)+A_u(c40)] * 20
```

`z_E_cum` is a sparse-calendar trapezoidal approximation, not true per-cycle
integration. Powers `Umax^p` and `A_u^q`, parameter searches, alternative
quadrature, ROI changes, and architecture fitting are forbidden.

## Frozen hidden descriptive target

At each same-cycle c10/c20/c40 state:

```text
H(N) = sum_Omega A_i * alpha_bar_elem_i / sum_Omega A_i
```

This target is used only for observability scoring. Damage, fatigue degradation
and psi may be reported descriptively but cannot replace H after results open.

## Evaluation and stop rule

Use three leave-one-Umax-out folds. Two development trajectories define only a
two-point affine transfer; the held-out trajectory is untouched until scoring.
Report same-cycle hidden-state prediction and remaining life
`R(N)=N_f-N` at c10/c20/c40.

Mandatory controls:

- cycle N only;
- `N*Umax` load-clock;
- raw normalized displacement amplitude without c1 subtraction.

The gate fails if any of the following occurs:

- nonfinite/mesh-unstable A_u;
- A_u-to-H slope sign reverses across fixed cycles;
- either exposure candidate is worse than `N*Umax` on any held-out Umax;
- fewer than 3/3 held-out timing predictions beat `N*Umax`;
- at least two fixed cycles do not improve over the raw normalized-displacement
  null;
- U0.13 c40 A_u reaches at least 95% of its isolated event-peak value;
- the result needs a deleted trajectory, changed ROI/norm/formula, or c50.

A pass authorizes only a fixed-calendar confirmation export, such as c15/c30.
It does not authorize KAN/RBF/PIDL, a universal threshold, or publication-level
early warning.

## Current data decision

The formal gate cannot run. Existing c10/c20/c40 VTK files are s5 unloaded
states and existing `psi_fields` contain only `alpha_bar_elem`, `d_elem`,
`f_alpha_elem`, and `psi_elem`. Exact s4 `u_node` is absent. Request 29 is the
only authorized producer action.

## Completed pre-gate result

Verdict: **`FORMAL_GATE_BLOCKED_MISSING_S4_PEAK_DISPLACEMENT`**.

The asset audit verified all three c1/s4 references on the common
86,756-node mesh. Every retained c10/c20/c40 VTK is s5 unload: maximum
displacement norm is zero except U0.11/c40 numerical roundoff `1e-15`.
Therefore none can enter `A_u`.

The geometry-only calculation gives median `sqrt(Q4 area)=0.00199284`, hence
the frozen `h_ROI=max(4*ell,2*h_e)=0.04`, containing 10,133 Q4 cells and area
`0.0400632`.

The allowed hidden-state descriptive audit shows strict Umax ordering at every
fixed cycle:

| cycle | H(U0.11) | H(U0.12) | H(U0.13) | Spearman(Umax,H) |
|---:|---:|---:|---:|---:|
| 10 | 0.095626 | 0.116591 | 0.138398 | 1.0 |
| 20 | 0.194610 | 0.232941 | 0.271285 | 1.0 |
| 40 | 0.383454 | 0.445134 | 0.496063 | 1.0 |

This establishes only that the fixed-calendar hidden fatigue state already
separates the three trajectories, making the displacement-observability
request informative. It does not establish that displacement observes H or
predicts first detect.

Evidence root:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/fixed_calendar_fatigue_exposure_pregate_20260818/`
