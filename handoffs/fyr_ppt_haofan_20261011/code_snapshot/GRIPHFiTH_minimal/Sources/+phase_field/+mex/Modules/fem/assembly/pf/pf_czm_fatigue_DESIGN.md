# Task G Wu PF-CZM kernel design notes (FEM-9 Task G, 2026-05-12)

**Goal**: Implement Wu PF-CZM (Wu 2017 IJSS, Baktheer 2024) for Phase 2 PCC concrete fatigue reference. Two new Fortran files + MATLAB wrappers + INPUT.

**Anchor**: Baktheer 2024 C60 concrete @ S^max=0.75·f_t → N_f ≈ 1,500–3,000 cycles. PCC AT2 (FEM-9 Task C) gave VHCF ~5.5×10⁵ at same loading — Wu PF-CZM should hit HCF cleanly.

## Math summary

### Equilibrium (new file `equilibrium/pf_czm.f90`)

No volumetric/deviatoric or spectral split. Effective stress = full elastic:

```
σ̃_ij = CC_ijkl · ε_kl       (effective / undegraded stress)
σ_ij = g(d) · σ̃_ij           (Cauchy stress in equilibrium)
K_ij = g(d) · CC_ijkl         (tangent stiffness)
```

with degradation function

```
g(d) = (1-d)^traction_p / [(1-d)^traction_p + φ(d)]
φ(d) = a₁·d + a₁·a₂·d²        (Cornelissen rank-1, a₃=0)
traction_p = 2.5               (Baktheer 2024)
a₁ = 4·E₀·G_f / (π·ℓ·f_t²)    (cohesive length scaling)
a₂ = 2^(5/3) − 3 ≈ 0.1748      (Cornelissen 1986 closed-form)
```

### Driving force Y (per Gauss point, new file `equilibrium/pf_czm.f90` output)

```
σ̃₁ = first principal of effective stress σ̃     (Macaulay-positive only)
Y = ⟨σ̃₁⟩²₊ / (2·E₀)
```

In 2D plane strain:
```
σ̃₁ = (σ̃_xx + σ̃_yy)/2 + sqrt((σ̃_xx − σ̃_yy)²/4 + σ̃_xy²)
```

History variable H:
```
H_t = max( H_min, max over τ ∈ [0,t] of Y(τ) )
H_min = f_t² / (2·E₀)        (initial threshold to prevent spurious damage in pristine material)
```

### Phase-field PDE (new file `pf/pf_czm_fatigue.f90`)

Strong form (Baktheer 2024 Eq. 38 / page-9 prose: fat_deg multiplies G_c only):
```
−g'(d)·H + f(ᾱ)·G_c · [α'(d)/(c_α·ℓ) − (2ℓ/c_α)·Δd] = 0       in Ω
∇d · n = 0                                                       on ∂Ω
```

with
```
α(d) = 2·d − d²              (Wu / Baktheer ξ=2)
α'(d) = 2 − 2·d
α''(d) = −2
c_α = π
```

**Carrara fatigue layer reuse** (same as Phase 1 AT2 fatigue):
```
Δᾱ_t = H_p( g(d)·Y_t − g(d_prev)·Y_prev )    [Carrara unidirectional accumulator on degraded driving force]
ᾱ_{n+1} = ᾱ_n + Δᾱ
f(ᾱ) = (2·α_T / (ᾱ + α_T))^p                 [Carrara fatigue exponent stays in MAT_CHAR.p]
fat_deg = min(1, f(ᾱ))
```

### Weak form / FE discretization

Newton residual at element level (per Gauss point):
```
r_d = N^T · [−g'(d_GP)·H + fat_deg·(Gc/c_α/ℓ)·α'(d_GP)] − fat_deg·B^T · (2·Gc·ℓ/c_α)·∇d_GP
```

Tangent stiffness (per Gauss point) — matches Fortran code:
```
K_dd = N^T · [−g''(d_GP)·H + fat_deg·(Gc/(c_α·ℓ))·α''(d_GP)] · N + fat_deg·B^T · (2·Gc·ℓ/c_α) · B
```

(Sign convention: `r_d = K_dd · d − rhs_d`. fat_deg placement per Baktheer 2024 Eq. 38 + page-9 prose: `f(ᾱ)` multiplies the geometric `G_c`-side terms only, **NOT** the elastic-energy `g'(d)·H` driving term. The Day-1 placement of fat_deg on `g''·H` / `g'·H` was wrong; fixed per Mac review 2026-05-12 commit `e52cd03`. Convention now matches existing `at2_history_fatigue.f90:100-101`.)

Note: α''(d) = −2 < 0 for Wu. Both terms `−g''·H·fat_deg` and `+(Gc/(c_α·ℓ))·α''` are **NEGATIVE** in isolation (g''>0, α''<0). Only the `+B^T·(2·Gc·ℓ/c_α)·B` term provides positive stiffness globally — the **strong-coupling property of Wu PF-CZM** that motivates BFGS / augmented-Lagrangian solvers per Wu/Huang/Nguyen 2019 CMAME. Vanilla Newton may stall near d→0.99+.

AT2 has α''(d) = 2 > 0 and g''(d) = 2 > 0, both positive on the NtN term — Newton-stable everywhere.

## g(d) derivatives (Wu rational fraction, traction_p=2.5)

Let q(d) = (1-d)^traction_p, w(d) = q(d) + φ(d).

```
g(d)   = q/w
g'(d)  = [q'·w − q·w'] / w²        with q' = -traction_p·(1-d)^(traction_p-1), w' = q' + φ'
g''(d) = [q''·w² − q·w''·w − 2·g'(d)·w·w'] / w²·w   (long expression; can split numerically)
                                                    or via analytical simplification
```

Cleaner numerical-stable form (Baktheer 2024 supplemental Eq. SI-4):
```
g(d) = (1-d)^traction_p · ω(d)
     where ω(d) = 1 / [1 + φ(d)/(1-d)^p]
```

Computational shortcut: compute q, q', q''; compute φ, φ', φ''; then chain rule:
```
q'(d) = -traction_p·(1-d)^(traction_p-1)
q''(d) = traction_p·(traction_p-1)·(1-d)^(traction_p-2)
φ'(d) = a₁ + 2·a₁·a₂·d
φ''(d) = 2·a₁·a₂
```

Then plug into quotient rule.

## File structure

```
Sources/+phase_field/+mex/Modules/fem/assembly/
├── equilibrium/
│   ├── amor.f90              (existing)
│   ├── miehe.f90             (existing, patched April)
│   ├── pf_czm.f90            (NEW — Wu PF-CZM equilibrium)
│   └── ...
└── pf/
    ├── at1_*_fatigue.f90     (existing)
    ├── at2_*_fatigue.f90     (existing)
    ├── pf_czm_fatigue.f90    (NEW — Wu PF-CZM phase-field + Carrara fatigue)
    └── ...
```

MATLAB-side:
```
Sources/+phase_field/+mex/+fem/+assembly/
├── +equilibrium/pf_czm.m    (NEW wrapper)
└── +pf/pf_czm_fatigue.m     (NEW wrapper)
```

INPUT/driver:
```
Scripts/fatigue_fracture/
├── INPUT_SENT_concrete_PCC_v3.m    (NEW — Wu PF-CZM PCC fatigue at S^max=0.75)
└── main_SENT_concrete_PCC_v3.m     (NEW driver)
```

## MAT_CHAR additions needed

Wu PF-CZM needs new material parameters in MAT_CHAR:
- `f_t` (tensile strength)
- `traction_p` (degradation traction order = 2.5)
- `a1`, `a2` (cracking function coefficients — auto-derived from G_f, ℓ, E, f_t if not given)
- already have: `E`, `ni`, `Gc` (= G_f), `ell`, `alpha_T`, `res_stiff`

Check `Sources/+phase_field/+init/material_characteristic.m` for the param-passing API.

## Compile pipeline

Same as April MIEHE patch:
1. Build Fortran .obj with `/free` flag
2. Link wrapper with `-R2018a` (default mex API)
3. Output: `MIEHE.mexw64` style (e.g. `PF_CZM.mexw64`)

## Validation plan

1. **Smoke**: compile + run minimum INPUT, verify no crash + stress field shape sane
2. **Brittle benchmark**: Miehe 2010 SEN(B) (E=210 GPa, f_t=2000 MPa, G_f=2.7 N/mm, ℓ=0.0075 mm). Compare peak load to Wu 2017 IJSS Fig 11 — accept ±5%.
3. **PCC fatigue smoke at S^max=0.75**: target N_f ≈ 1,500–3,000 cycles (Baktheer 2024 C60). If hit within ±50%, calibration good.
4. **Cross-amplitude S-N**: S^max ∈ {0.65, 0.75, 0.85}, 3 runs for §5 plot.

## Known risks

1. **Principal stress at zero discriminant**: `sqrt((σ̃_xx − σ̃_yy)²/4 + σ̃_xy²)` at zero gives 0/0 in d/dε derivative. Handled in `macaulay_sigma1_2D` with `if (disc < 0) disc = 0` + `max(0, s1)`.
2. **g''(d) at d→1**: q''(d) = traction_p · (traction_p−1) · (1-d)^(traction_p−2). With traction_p=2.5, exponent = +0.5, so q''(d→1) → **0** (not infinity). φ(1) > 0 ⇒ w(1) > 0 ⇒ g''(d) bounded. **No d_max clip needed for this reason.** (Fixed per Mac review P3b, 2026-05-12; Day-1 doc claimed (1-d)^(−0.5) singular, which was wrong sign on the exponent.)
3. **fat_deg → 0 numerical**: when ᾱ → ∞, fat_deg → 0 — solver may stall. Floor at 1e-6 in `pf_czm_fatigue.f90`.
4. **Cycle_jump = OFF default**: hardcoded in INPUT_v3 (per PCC v2 lessons).
5. **Wu K_dd locally non-PD**: see §K_dd note above. May need BFGS port from Wu's `pfczm_bfgs.for` if Newton stalls.

## TODO (next session)

- [ ] Write `pf_czm.f90` (equilibrium) skeleton with stubs
- [ ] Write `pf_czm_fatigue.f90` skeleton with stubs
- [ ] Add MATLAB wrappers
- [ ] Build script `build_pf_czm_mex.m` (model after `build_miehe_mex.m`)
- [ ] Write `INPUT_SENB_miehe2010_pfczm.m` for brittle benchmark
- [ ] Compile + smoke test
- [ ] Brittle benchmark vs Wu 2017
