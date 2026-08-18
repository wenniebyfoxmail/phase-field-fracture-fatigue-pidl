# Independent GPT Pro review — fixed-calendar fatigue exposure

Date: 2026-08-18

Conversation: `构造疲劳暴露坐标`
(`6a8451f1-4144-83ed-8285-6671daa8e36e`)

Verdict: **`FREEZE_MINIMAL_FIXED_CALENDAR_EXPOSURE_GATE`**.

The reviewer found that the current archive can support an asset/operator
pre-gate but not the exposure experiment: c10/c20/c40 retain only s5 unloaded
VTK and element hidden fields, not s4 peak displacement. It explicitly forbids
using s5 displacement, fixed-damage reconstruction, psi inversion, or event
peaks as substitutes.

The frozen next package is nine native states:

```text
Umax in {0.11, 0.12, 0.13}
cycle in {10, 20, 40}
substep = 4 peak, post-convergence and post-state-commit
```

No c50 state is allowed because it is only nine cycles before U0.13 first
detect. If replay is required, each case stops at c40.

Each trajectory uses its own c1/s4 field as a
`within-trajectory c1 normalized reference`, not as a proven virgin/healthy
elastic solution. The primary observable is frozen before opening the nine
states:

```text
u_res(N) = u_s4(N)/Umax - u_s4(c1)/Umax
h_ROI = max(4*ell, 2*h_e) = 0.04 for ell=0.01
Omega_L = {x >= initial tip x0=0, |y| <= h_ROI}
A_u(N) = area-weighted RMS_Omega_L ||sym(grad u_res)||_F
```

The only exposure candidates are `N*A_u(N)` and the fixed trapezoidal
`sparse-calendar exposure integral` over c10/c20/c40. Searching Umax exponents
`p`, response exponents `q`, ROIs, norms, or architectures is forbidden.

The formal evaluation is three-fold leave-one-Umax-out threshold/timing
transfer against `N*Umax` and raw normalized-displacement controls. A pass
requires 3/3 timing improvement over `N*Umax`, stable hidden-state ordering,
no sign reversal, and no U0.13 c40 terminal saturation. A pass may authorize
only a denser fixed-calendar confirmation export, not training, universal
critical exposure, or an early-warning claim.

