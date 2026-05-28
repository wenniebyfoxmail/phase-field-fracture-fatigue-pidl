# FEM/PIDL Strict Setting Alignment Audit

Date: 2026-05-28

Purpose: prevent a false FEM/PIDL mechanism conclusion caused by comparing
different physical or numerical settings. This note is a stop/go checklist
before interpreting the next PIDL experiments.

## Executive Verdict

We do not yet have one fully strict FEM/PIDL comparison. We have several useful
references, but they answer different questions.

- Historical PIDL baseline is closest to the diffuse-precrack FEM in notch
  convention and top/bottom horizontal constraint, but it is not strictly
  aligned because PIDL uses a soft initial damage-history field and zero initial
  fatigue history, while diffuse FEM uses a hard `d=1` precrack band and
  initializes `alpha_bar=1`/`f=0.4444` in that band.
- Old/fine void FEM are not directly comparable to baseline PIDL because the
  notch is a real void/slit in FEM but a damaged material band in PIDL.
- Fine reverseBC FEM and diffuse reverseBC FEM are closer to PIDL's default
  top/bottom `u_x=0` constraint than the old bottom-left-anchor FEM setting.
- Irreversibility penalty strength is not aligned: FEM default `tol_irrev=1e-3`
  gives a penalty coefficient 25 times larger than PIDL `tol_ir=5e-3`.

Therefore, before making a physics claim, each comparison must declare which
reference track it belongs to:

1. **Void-notch track**: FEM void/slit reference compared with PIDL using
   `void_notch_mask` and matched reverseBC or FEM-anchor BC.
2. **Diffuse-precrack track**: FEM diffuse precrack compared with PIDL using
   a damaged-material precrack, matched initial fatigue/history, and matched
   reverseBC.

Do not mix void FEM and diffuse PIDL when explaining mechanism-level gaps.

## Evidence Sources Checked

- PIDL config: `SENS_tensile/config.py`
- PIDL field/energy/history code:
  `SENS_tensile/field_computation.py`, `source/compute_energy.py`,
  `source/fatigue_history.py`, `source/model_train.py`,
  `source/pff_model.py`, `source/utils.py`
- Historical setting note: `docs/fem vs pidl setting.md`
- Criteria note: `docs/fem_pidl_criteria_alignment_audit_2026-05-28.md`
- FEM old/fine/diffuse README and input handoffs in OneDrive, including:
  `_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28`,
  `_pidl_handoff_fine_reverseBC_u12_cyclewise_mechanism_2026-05-28`,
  `_pidl_handoff_reverseBC_u12_diffuse_precrack_2026-05-28`

## Strict Alignment Matrix

| Aspect | PIDL baseline | Old void FEM | Fine reverseBC void FEM | Diffuse-precrack reverseBC FEM | Alignment risk |
|---|---|---|---|---|---|
| Domain | `[-0.5,0.5]^2` | nominally same | nominally same | `[0,1]^2`, must shift by `-0.5` for comparison | Medium: coordinate shift needed |
| Mesh | Gmsh triangles, default `meshed_geom2.msh`: 34030 nodes, 67276 triangles | 77900 nodes, 77730 Q4 elements | 10401 nodes, 10261 Q4 elements | 45591 nodes, 45000 Q4 elements | High: no direct elementwise comparison |
| Discretization | continuous NN field sampled on triangles | FE Q4 | FE Q4 | FE Q4 | High: peak/history smoothing differs |
| Notch representation | damaged phase-field region retained in material | real void/slit with crack-face geometry | real void/slit | continuous material with hard phase-field precrack | Critical |
| Initial damage/precrack | `hist_alpha_init`, soft irreversibility history; not a hard Dirichlet band | physical void | physical void | hard `d=1` nodes/elements in precrack band | Critical |
| Initial fatigue history | `hist_fat=0` unless a runner changes it | void has no material history in slit | void has no material history in slit | `alpha_bar=1` in precrack elements; initial `f=0.4444` there | Critical |
| Essential BC for `u_x` | default vertical ansatz gives `u_x=0` on top and bottom | base `INPUT_SENT_PIDL_12.m` fixes only bottom-left `u_x` | `fix_X top_bottom` | `fix_X top_bottom` | Critical for old FEM; mostly aligned for reverseBC |
| Essential BC for `u_y` | bottom `v=0`, top `v=U` | bottom fixed, top displaced | bottom fixed, top displaced | bottom fixed, top displaced | Mostly aligned |
| Side boundaries | natural through energy, not hard traction-free | natural traction-free FE boundary | natural traction-free FE boundary | natural traction-free FE boundary | Medium-high: NN representation can leave side residual |
| Loading | one peak solve per cycle, `Umax=0.12`, `R=0` | cyclic, 8 steps/cycle, `Umax=0.12`, `R=0` | same | same | High for fatigue timing |
| Material | `E=1`, `nu=0.3`, `l0=0.01`, `w1=1` | `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01` | same | same | Aligned after normalization |
| Phase-field model | AT1 | AT1 | AT1 | AT1 | Aligned |
| Strain split | `se_split='volumetric'` | `split_type='AMOR'` | `AMOR` | `AMOR` | Medium: formulas look related but need exact audit |
| Fatigue law | Carrara accumulator, asymptotic degradation, `alpha_T=0.5`, `p=2` | same intended law | same | same | Law-level aligned |
| Fatigue update timing | PIDL updates from peak `g(alpha)*psi_plus`, then resets previous peak each cycle | FE loading substeps/Gauss history | same | same | High |
| Residual stiffness | PIDL `g=(1-alpha)^2`, no confirmed `eta` | `res_stiff=1e-6` | `res_stiff=1e-6` | `res_stiff=1e-6` | Medium, important near `alpha=1` |
| Irreversibility penalty | `tol_ir=5e-3`, coefficient `27/(64 tol^2)=16875` | default `tol_irrev=1e-3`, coefficient `421875` | same | same | Critical: FEM 25x stronger |
| Solver | RPROP/NN variational minimization of `log10(E_el+E_d+E_hist)` | staggered FE Newton/line search | same | same | High: same minimum not guaranteed |
| Fracture detection | right-boundary alpha threshold, node count, confirmation cycles | FEM monitor/exported boundary criterion | same | same | High unless post-hoc harmonized |
| Energy reporting | `E_el`, `E_d`, plus explicit `E_hist` penalty in PIDL loss | FEM exported energies, no separate PIDL-style `E_hist` term | same | same | High: compare definitions before numbers |

## Red-Line Mismatches

These must be controlled before we trust a mechanism comparison.

### 1. Notch Type

Void FEM and baseline PIDL are different physical problems.

- Void FEM removes the slit material and has crack faces.
- Baseline PIDL keeps material in the notch region and represents the precrack
  through damage/history.
- Diffuse FEM keeps material like PIDL, but with hard `d=1` in the precrack
  band.

This affects absolute `E_d`, local stiffness, stress concentration, fatigue
history accumulation, and the location of maximum damage/history.

### 2. Initial History State

For the diffuse-precrack FEM comparison, PIDL is still not aligned if
`hist_fat` starts from zero.

Diffuse FEM initializes the precrack band with high phase-field damage and
fatigue/history state. PIDL baseline initializes damage irreversibility history
but not the fatigue history. This can change the early fatigue degradation loop:

```text
initial history -> f_fatigue -> E_d weighting -> stress redistribution
-> psi_plus -> next history increment
```

This is exactly the kind of small setting difference that can be amplified over
cycles.

### 3. Boundary Conditions

PIDL default vertical-loading ansatz imposes `u_x=0` on both top and bottom.
That matches reverseBC FEM better than the old bottom-left-anchor FEM. It is not
strictly aligned with any FEM run that only fixes one horizontal anchor point.

For comparisons:

- Use reverseBC FEM when comparing to default PIDL.
- Use PIDL `exact_bc_mode='fem_anchor'` if comparing to bottom-left-anchor FEM.

### 4. Irreversibility Penalty Strength

FEM default `tol_irrev=1e-3` and PIDL `tol_ir=5e-3` are not equivalent.

With AT1 penalty scaling proportional to `1/tol^2`:

```text
PIDL coefficient = 27 / (64 * 0.005^2) = 16875
FEM coefficient  = 27 / (64 * 0.001^2) = 421875
ratio FEM/PIDL   = 25
```

This can change healing suppression, damage sharpness, history feedback, and
optimizer conditioning.

### 5. Cycle Timing

FEM resolves each cycle through multiple load steps. PIDL currently performs one
peak solve per cycle and updates fatigue history from the peak state. Even with
the same Carrara law, the accumulated history may differ because the path inside
the cycle is different.

### 6. Field Reduction and Monitor Trap

FEM element-field maxima and FEM monitor maxima are not the same object.
Comparisons must state whether a scalar is:

- element mean,
- Gauss-point/internal max,
- nodal projection,
- monitor scalar,
- loaded peak,
- unloaded/cycle-end snapshot,
- pre-history-refresh or post-history-refresh.

## What Is Already Aligned Enough

These are not the first suspects:

- `E=1`, `nu=0.3`
- `Gc/ell = w1/l0 = 1` with `Gc=0.01`, `ell=l0=0.01`
- AT1 phase-field model
- `Umax=0.12`, `R=0`
- Carrara-style fatigue accumulator and asymptotic degradation at law level
- `alpha_T=0.5`, `p=2`
- plane-strain intent

They still need exact implementation awareness, but they are not the obvious
source of the huge differences.

## Required Fair-Comparison Tracks

### Track A: Void-Notch FEM Reference

Use this track if the FEM reference is old/fine void/slit FEM.

Required PIDL settings:

- enable `fatigue_dict["void_notch_mask"]`,
- exclude the precrack/slit region from energy and fatigue accumulation,
- use a BC mode matching the FEM run:
  - reverseBC/top-bottom clamp for reverseBC FEM,
  - FEM-anchor mode for bottom-left-anchor FEM,
- align or explicitly vary `tol_ir`,
- evaluate fields on a common probe grid or FEM centroids, not raw elements.

This track tests whether PIDL can reproduce a void/slit FEM mechanism.

### Track B: Diffuse-Precrack FEM Reference

Use this track if the FEM reference is the diffuse precrack run.

Required PIDL settings:

- keep material in the precrack region,
- match the precrack width and length,
- initialize or strongly impose the precrack damage state,
- initialize the fatigue/history state in the precrack band consistently with
  FEM, or run a FEM variant with zero initial fatigue history,
- use reverseBC/top-bottom horizontal constraint,
- align or explicitly vary `tol_ir`,
- compare after shifting FEM coordinates from `[0,1]^2` to `[-0.5,0.5]^2`.

This track tests whether PIDL can reproduce a damaged-material precrack FEM
mechanism.

## Stop/Go Rule Before Next Experiments

Before launching or interpreting a new method experiment, write one line in the
run log:

```text
reference_track = void_notch | diffuse_precrack
notch = void_mask | diffuse_soft | diffuse_hard
bc = reverseBC | fem_anchor | other
tol_ir = ...
hist_fat_init = zero | precrack_initialized
fracture_metric = native | harmonized
```

If any of these are unknown, do not use the run for a FEM/PIDL mechanism claim.

## Recommended Immediate Action

1. Keep the existing baseline comparison as a diagnostic, not a strict
   mechanism claim.
2. Finish the void-notch PIDL diagnostic for the void FEM track.
3. Add a diffuse-precrack-aligned PIDL diagnostic for the diffuse FEM track:
   same reverseBC, same precrack width, same initial fatigue/history convention,
   and preferably `tol_ir=1e-3` as a controlled variant.
4. For every comparison, report native and harmonized criteria separately.

The key logic is:

```text
Do not ask whether PIDL differs from FEM until we know which FEM setting
PIDL is supposed to match.
```

Only after this alignment gate should we interpret thin bands, local history
weakness, patch strength, or architecture effects as true PIDL limitations.
