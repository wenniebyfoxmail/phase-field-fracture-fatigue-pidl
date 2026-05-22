# Evolution of the PIDL-FEM Method Comparison

**English advisor-facing version, v1. 2026-05-13 local session.**

This document explains how the project moved from a simple fatigue-life comparison to a multi-metric diagnosis of when PIDL looks like FEM and when it does not. It is not a chronological log. It is a structured account of why each method was tried, what it changed, what it taught us, and why the next method followed.

The main update in this version is that the C4 + Fourier stack is no longer a single-seed result. It has now been reproduced at N=100 across three seeds, with mean alpha_bar_max = 27.50, a 2.9% spread, and V7 passing in all three runs. The second update is the Phase 2 / PCC reframing: the current GRIPHFiTH Wu PF-CZM run is treated as a fatigue-layer check and solver-limitation finding, not as a completed fracture N_f reference.

---

## 1. How The Main Question Evolved

The project did not start as a search over many methods. It started from one practical question: can a PIDL model with Carrara fatigue reproduce fatigue life N_f for the SENT benchmark? Once the answer became yes, the question became narrower and more mechanical.

The question chain is now:

1. Can PIDL + Carrara produce a reasonable fatigue life N_f?
2. If N_f is close to FEM, why do the local fields still look unlike FEM?
3. Should the gap be attacked through representation, the fatigue law, the optimization path, or supervision?
4. Which quantities are already aligned, and which quantities are still wrong?
5. For quantities such as symmetry and free-boundary residual, should we remove the error by construction instead of asking the loss to learn it?

This matters because N_f alone is too weak as a success criterion. A model can match the final life while using the wrong local damage and stress fields. The later method changes are best understood as attempts to separate timing agreement from field agreement.

---

## 2. The Five Alignment Metrics

We now judge "FEM-likeness" using five categories. This is the main conceptual shift in the project.

### 2.1 Trajectory

The first metric is the crack or damage trajectory across cycles, not just the final life. We compare a_PIDL(N) and a_FEM(N) over a set of sampled cycles:

```text
J_a = sqrt( (1/M) * sum_N (a_PIDL(N) - a_FEM(N))^2 )
```

For FEM, a(N) is measured from the rightmost point where alpha > 0.95. For PIDL, alpha is usually more diffuse, so the primary proxy is the rightmost point where alpha > 0.5. A second proxy uses a psi+-weighted crack-tip estimate. Both give the same qualitative trend.

### 2.2 Local Process-Zone Metrics

The second metric asks whether the driving energy is concentrated near the crack tip. We integrate quantities such as g(alpha) psi+ and f(alpha_bar) psi+ over a ball of radius l0 around the current crack tip.

The important point is that f(alpha_bar) psi+ is a diagnostic quantity. It is not the exact energy term in the variational functional. It asks whether the fatigue degradation field and the tensile driving energy are co-located in the process zone.

### 2.3 Integrated Budget

The third metric compares the total accumulated fatigue history. A useful ratio is:

```text
R_alpha_bar = alpha_bar_domain^FEM / alpha_bar_domain^PIDL
```

This metric often looks much better than alpha_bar_max. For example, baseline u=0.12 gives R_alpha_bar about 1.138, and Path C lambda=1 gives about 1.082. This means PIDL is not failing to accumulate fatigue history in total. It is spreading the history too broadly instead of concentrating it near the tip.

### 2.4 Symmetry

The SENT specimen is symmetric about y=0, so alpha(x,+y) should equal alpha(x,-y). Baseline PIDL has a symmetry RMS around 0.072. C5 hard-symmetry encoding removes this error by construction, driving the metric to machine precision.

### 2.5 Free-Boundary Residual

The side boundaries x = +/-0.5 are traction-free. Therefore sigma_xx and sigma_xy should vanish there. Baseline PIDL has a side-boundary residual around 26.5% for sigma_xx and 17.4% for sigma_xy. C4 exact-BC ansatz removes this residual by construction.

This metric was a major turning point. It showed that some errors are not good candidates for soft penalties. If a boundary condition is known exactly, the model should be built so that the error is impossible.

---

## 3. Baseline: PIDL Fatigue Works, But The Fields Are Wrong

The baseline model is an 8 x 400 MLP with TrainableReLU activations. The input is (x,y), and the outputs are displacement components and alpha. Dirichlet conditions and the pre-crack are imposed through output transformations. Carrara fatigue is added through the history variable alpha_bar and the degradation function f(alpha_bar).

The baseline result at u=0.12 is the first success and the first problem:

| Quantity | Baseline value | Interpretation |
|---|---:|---|
| N_f | 82 vs FEM 82 | Strong timing agreement |
| trajectory RMS | 0.087 | Weak field trajectory |
| local I_gpsi | 9.40e-08 | Weak process-zone concentration |
| R_alpha_bar | 1.138 | Total budget close |
| symmetry RMS | 0.072 | Weak |
| side-boundary residual | 0.265 | WARN |
| alpha_bar_max | 9.34 | Far below FEM scale |

The baseline taught us that the fatigue-life target is not enough. PIDL can get the life right while the local driver and damage fields remain too diffuse.

---

## 4. Representation-Enhancement Route

### 4.1 Williams Input Features

The first representation hypothesis was that the MLP could not learn crack-tip singular structure because of spectral bias. We therefore added Williams-style input features: sqrt(r/l0), r/l0, sin(theta/2), cos(theta/2), sin(3theta/2), and cos(3theta/2). The network body stayed the same, but the input dimension increased from 2 to 8.

This did not solve the problem. N_f stayed reasonable, around 77 for u=0.12, but alpha_bar_max dropped to about 5.14. The lesson was that giving the network crack-tip coordinates does not force the output field to use them.

### 4.2 Fourier Features

The second representation hypothesis was that the network needed higher-frequency basis functions. We used random Fourier features:

```text
gamma(x) = [cos(2 pi Bx), sin(2 pi Bx)]
```

where B is frozen after initialization. The inner MLP receives the Fourier feature vector, not the raw coordinates. A sweep over sigma later showed that sigma=30 is the useful peak in the tested setup.

Fourier features did increase localization. At u=0.12, sigma=30 gave alpha_bar_max around 14.26 by c49, above the baseline value of 9.34. The cost was severe boundary ringing: sigma=30 produced V7 side-boundary failures from about 74% to 124% across seeds. This trade-off motivated the later C4 + Fourier stack.

### 4.3 Enriched Ansatz

The next representation hypothesis was stronger: instead of only feeding crack-tip features into the network, we added a Williams Mode-I singular displacement term directly to the output. The network learned the smooth residual, while a learnable scalar controlled the amplitude of the singular enrichment.

This helped the process-zone driver. For u=0.12, N_f stayed close to FEM at about 84, alpha_bar_max rose to about 11.15, and I_gpsi increased by roughly 5x relative to baseline. But the enriched field also worsened symmetry and free-boundary residuals. The conclusion was that output enrichment points in the right direction but cannot be used blindly without boundary control.

---

## 5. Fatigue-Chain Modification Route

### 5.1 Tip Weighting

Tip weighting put larger weights on high-psi+ elements inside the Deep Ritz loss. The intended effect was to make the optimizer care more about the crack-tip region.

The retest after the plumbing fix showed a clear pathology. With beta=2 and p=1, Kt started near the baseline value around 7.5 but collapsed to 1.43 by cycle 2. The model found a cheap way to reduce the weighted loss: flatten the high-weight crack-tip energy instead of creating a sharper FEM-like driver.

This is a key negative result. "Looking harder at the tip" through a weighted functional changes the variational problem and can create degenerate minima.

### 5.2 Spatial alpha_T

Spatial alpha_T lowered the fatigue threshold near the crack tip. The idea was to make the local fatigue degradation activate sooner.

This was useful as an ablation but not as a physical closure. In Carrara/Baktheer fatigue, alpha_T is a material parameter, so making it spatially dependent is not first-principles. The tested broad and narrow variants did not produce a qualitative localization improvement. Narrow alpha_T kept N_f near 80, but alpha_bar_max remained below the needed scale.

### 5.3 Golahmar Accumulation Law

The Golahmar-style law changes the fatigue history accumulation from a linear Carrara update to a nonlinear power-law update. It can strongly affect fatigue kinetics.

For u=0.12, it moved N_f to about 154, far away from the FEM value of 82. alpha_bar_max rose only to about 10.87. The result suggested that changing the fatigue law changes the timing but does not fix the missing driver concentration.

### 5.4 Logarithmic f(alpha_bar)

The logarithmic degradation function is a Carrara-discussed alternative to the default asymptotic form. It was tested to see whether a different f(alpha_bar) shape could increase local fatigue concentration.

For u=0.12, N_f became about 121, and alpha_bar_max stayed near 10.83. The conclusion was similar to Golahmar: the fatigue degradation curve affects life, but it is not the main bottleneck behind the local field gap.

---

## 6. Diagnostic Injection Route

### 6.1 psiHack

psiHack artificially amplifies psi+ near the crack tip by a Gaussian factor. This is not a proposed method. It is a diagnostic intervention.

The result was decisive. At u=0.12, N_f remained about 81, but alpha_bar_max rose from 9.34 to about 457. This showed that the Carrara accumulator can produce large alpha_bar if the upstream driver is sufficiently sharp.

### 6.2 Oracle psi+ Injection

The Oracle test replaced PIDL psi+ with projected FEM psi+ inside a process-zone override region. This was done every cycle while leaving the rest of the PIDL pipeline intact.

At u=0.12, Oracle injection gave N_f = 83 and alpha_bar_max about 776.8. At u=0.11, alpha_bar_max reached about 13138. This shows that FEM-like upstream psi+ is sufficient to produce FEM-scale fatigue accumulation.

The caveat matters. Oracle proves sufficiency, not necessity. It does not rule out downstream issues, because we did not run the reverse experiment of keeping PIDL psi+ while injecting FEM alpha_bar or f. Still, it strongly redirected the project toward fixing the upstream driver.

---

## 7. Architecture And Supervision Route

### 7.1 MIT-8 Weak psi+ Supervision

MIT-8 used FEM psi+ as a weak supervision target during a warm-up period. The aim was to move the network into a better basin and then release it back to pure physics.

The warm-up helped while supervision was active, but the model tended to drift back toward the baseline after release. This suggested that the pure-physics attractor remained too smooth.

### 7.2 Refined Tip Corridor Mesh

The tip-resolution branch asked whether the local field gap was mainly a mesh or collocation-density issue. The network architecture did not change; only the crack-tip corridor resolution increased.

The result was positive but small. alpha_bar_max increased by about 1-2 units in some runs, but there was no qualitative change. Better resolution is useful, but it is not enough on its own.

### 7.3 Multi-Head Architecture

The multi-head model split the network into far-field and tip-field heads, mixed by a spatial gate. The hope was that the tip head would specialize in high-gradient local fields.

The tested results were weak. The tip head did not naturally become the sharp crack-tip model. Without an explicit objective that assigns roles to the heads, the decomposition did not produce the desired specialization.

### 7.4 XFEM Jump Head

The XFEM jump-head architecture added a local discontinuity-like component inspired by XFEM. This made the representation more flexible near the crack.

It produced a marginal improvement, roughly 10-20% in alpha_bar_max, but not a stable closure. The result supported the same broad lesson: architecture alone helps, but the physics loss still prefers a smoother field.

### 7.5 Path C: Local Alpha Supervision

Path C added local alpha supervision inside a process-zone region. This was not the only possible next step, but it was the cheapest controlled ablation after Oracle, MIT-8, and the pure architecture variants.

The best setting was lambda=1. At u=0.12, it gave N_f = 89, trajectory RMS about 0.026 versus baseline 0.087, alpha_bar_max ratio FEM/PIDL about 8.80 versus baseline 79.3, and R_alpha_bar about 1.082.

Path C is the best learned reference so far. It improves trajectory, local fields, and the integrated budget. It does not close alpha_bar_max completely, and it does not solve symmetry or free-boundary residuals.

---

## 8. Branch 1: Closing V4 And V7 By Construction

### 8.1 Why This Branch Was Created

By May 11, many soft-loss and representation changes had been tested. The remaining errors were not all of the same kind. Symmetry and traction-free boundary conditions are exact physical facts of the benchmark. They should not have to be discovered by the optimizer.

This led to Branch 1: remove V4 and V7 errors by construction. This is separate from Branch 2, which continues to target alpha_bar_max localization.

### 8.2 C5: Hard Symmetry

C5 encodes y-symmetry directly. The input uses y^2 rather than y, so alpha is forced to be even in y. The v displacement output is multiplied by y, so v is forced to be odd in y.

This drives the alpha mirror RMS to zero at machine precision. The main cost in the first version was slower RPROP convergence, but the rescaled version reduced the slowdown.

### 8.3 C4: Exact-BC Distance-Function Ansatz

C4 encodes the side traction-free condition through a distance-function ansatz. The NN correction is multiplied by a side^2(x) factor, which vanishes at x = +/-0.5 together with its x-derivative. This makes the side-boundary traction residual zero for any network weights.

At u=0.12, the N=5 smoke gave V7 sigma_xx = 0 and sigma_xy = 0 by construction. The longer N=100 run gave alpha_bar_max = 23.05 at c99. This was already 2.5x the baseline, without Williams features, Fourier features, or supervision.

This was one of the main turns in the project. Correctly encoding the boundary condition did more than clean up V7. It also allowed the model to learn a sharper internal field.

---

## 9. Branch 2: alpha_bar_max Gap Closure

### 9.1 C2 Williams Hard Injection

C2 is a more explicit Williams ansatz than the earlier enriched-output method. Instead of adding a single scalar-amplitude singular displacement, C2 is designed to let the network output coefficients for Williams basis terms.

This is still a design branch. It has not produced a production result yet.

### 9.2 C6 FI-PINN Reweighting

C6 tried a FI-PINN-style adaptive reweighting of the Deep Ritz loss. The idea was to give more attention to high-residual or high-energy regions.

The result was catastrophic. With beta=2, Kt jumped from 7.51 at cycle 0 to 1924 at cycle 1. With beta=0.1, Kt still jumped above 1288. The issue was not just the magnitude of beta. The formulation itself distorted the variational objective.

Together with the tip-weight retest, this closed the reweighted-loss route. The recommended next path is adaptive sampling proper: keep the loss unchanged, but change the collocation distribution.

---

## 10. C4 + Fourier sigma=30 Stack

### 10.1 Why The Stack Makes Sense

C4 and Fourier features attack different failure modes. C4 enforces the side free-boundary condition. Fourier features add spectral capacity that can raise alpha_bar_max but cause boundary ringing.

The combination is therefore natural. Fourier is allowed to improve localization, while C4 prevents its boundary-ringing failure mode.

### 10.2 Main Results

All values below are for u=0.12.

| Method | alpha_bar_max | Cycle | V7 status | V4 alpha skew |
|---|---:|---:|---|---:|
| Baseline | 9.34 | N_f=82 | WARN | 0.072 |
| C4 alone | 23.05 | c99 | PASS by construction | 0.016 |
| Fourier sigma=30 alone, seed 1 | 14.26 | c49 | FAIL | 0.0035 |
| Fourier sigma=30 alone, seed 2 | 14.07 | c49 | FAIL | 0.0103 |
| Fourier sigma=30 alone, seed 3 | 14.26 | c49 | FAIL | 0.0073 |
| C4 + Fourier, seed 1 | 27.925 | c99 | PASS | 0.014 |
| C4 + Fourier, seed 2 | 27.427 | c99 | PASS | 0.0060 |
| C4 + Fourier, seed 3 | 27.133 | c99 | PASS | 0.0041 |
| C4 + Fourier, 3-seed summary | 27.50 mean, 2.9% spread | c99 | 3/3 PASS | 0.004-0.014 |

This is the strongest single configuration from the May campaign. It gives about 3x the baseline alpha_bar_max, passes V7 by construction in all tested seeds, and keeps V4 much smaller than the baseline.

### 10.3 sigma Sweep

The sigma=30 setting is supported by a six-point sweep:

| sigma | alpha_bar_max @ c10 | Kt @ c10 | Readout |
|---:|---:|---:|---|
| 10 | 2.75 | 8.15 | OK |
| 20 | 2.70 | 7.54 | OK |
| 30 | 2.93 | 7.04 | peak |
| 40 | 2.59 | 6.46 | OK but decelerating |
| 100 | 0.099 | 1.01 | degenerate |
| 300 | 1.73 | 121 | pathological |

This does not make sigma=30 a universal constant. It means sigma=30 is the useful spectral scale for the current SENT mesh, FourierFeatureNet implementation, and FEM peak width.

### 10.4 Paper Claim

The clean claim is: architectural mitigations can stack when they target orthogonal failure modes. Fourier alone raises localization but breaks V7. C4 alone closes V7 and raises localization moderately. C4 + Fourier keeps the boundary condition correct and gives the strongest learned alpha_bar_max result so far.

The limitation remains important. C4 + Fourier is about 3x the baseline, but the Oracle/FEM scale is still far higher. This is partial localization closure, not complete alpha_bar_max closure.

---

## 11. Phase 2 / PCC / Wu PF-CZM Reframing

### 11.1 Why This Belongs In The Method Evolution

The project is now moving from Phase 1 SENT/Carrara comparison to a Phase 2 concrete demonstration. This is not just a change of material parameters. It changes the reference frame.

In Phase 1, our own FEM line was the direct benchmark. In Phase 2, the cleaner anchor is the published Wu PF-CZM and Baktheer fatigue literature. This avoids making the paper depend on a full GRIPHFiTH PF-CZM fracture-life closure that is not yet stable.

### 11.2 alpha_T Calibration

The current Phase 2A plan is Carrara extended to PCC concrete units. The fatigue threshold is calibrated using the Baktheer relation:

```text
alpha_T = G_f / (k_f * l)
```

Here G_f is fracture energy, l is the phase-field length scale, and k_f is the concrete fatigue constant. k_f = 0.01 is the standard starting value. If the PCC smoke falls far outside known S-N trends, k_f should be recalibrated for PCC.

Phase 2B is the full Wu PF-CZM rewrite. It is more physically complete, but it is a larger kernel change. The current paper path is to use Phase 2A as the framework-transition demonstration and leave Phase 2B for the next stage.

### 11.3 What The PCC v3 FEM Run Actually Shows

Windows-FEM ran a 3000-cycle PCC v3 case. It should not be reported as a successful fracture N_f result, because the damage field did not localize to fracture.

The important numbers are:

| cycle | max alpha_bar / alpha_T | min f(alpha_bar), element mean | max d |
|---:|---:|---:|---:|
| 100 | 4% | 1.0000 | - |
| 1000 | 38% | 1.0000 | - |
| 2000 | 76% | 0.9188 | - |
| 3000 | 114% | 0.7822 | about 0.005 |

At Gauss-point level, the minimum f reached about 0.40 by c3000. At element-mean level, it stayed around 0.78. More importantly, d stayed near 0.005 and did not form a propagating crack. Therefore the earlier extrapolated N_f around 1500-2500 is retracted as a fracture-life claim.

The correct interpretation is narrower. The fatigue accumulator and degradation layer behave in the expected direction over 3000 cycles. The current GRIPHFiTH staggered Newton / CHOLMOD path does not convert that degraded toughness into d-localization. BFGS remains the right long-term solver fix, but it is no longer a blocker for the current paper framing.

### 11.4 Consequence For Section 5

Section 5 should not say that our FEM code has produced a PCC fracture N_f. It should say that the concrete reference is anchored in Wu 2017 for brittle PF-CZM behavior and Baktheer 2024 for PF-CZM + Carrara fatigue behavior.

Our own PCC v3 run can still be used, but only as a check of the fatigue layer and as an honest solver-limitation result. This keeps the PIDL contribution in focus: the paper is about moving the PIDL framework toward concrete units, not about presenting a new FEM solver.

There is also a useful data handoff. Windows-FEM has exported d_elem_traj and mesh_geometry.mat for PCC v3. This enables alpha- or d-field supervision on the PIDL side, but it is a method option, not a validated closure result yet.

---

## 12. Compressed Evolution

| Phase | Stage | Main finding |
|---|---|---|
| 1 | Baseline PIDL fatigue | N_f can match FEM, but the fields are not FEM-like |
| 2 | Representation enhancement | Williams, Fourier, and enriched outputs help partly but do not close the gap |
| 3 | Fatigue-chain changes | Kinetics change, but the upstream driver remains the main bottleneck |
| 4 | Diagnostic injection | psiHack and Oracle show that sharp upstream psi+ is sufficient for large alpha_bar |
| 5 | Hybrid / supervision | Path C is the best learned reference but does not close all metrics |
| 6 | By-construction architecture | C5 closes V4; C4 closes V7 and raises alpha_bar_max |
| 7 | C4 + Fourier stack | Best current configuration: V7 pass, V4 reduced, alpha_bar_max about 3x baseline, 3-seed reproduced |
| 8 | Reweighted-loss closure attempt | Tip weighting and C6 fail through Kt collapse or explosion |
| 9 | Phase 2 PCC reframing | Use Wu/Baktheer published anchors; treat our PCC v3 run as fatigue-layer check plus solver limitation |

---

## 13. Current Stable Conclusions

### Already aligned

- N_f for the original SENT/Carrara benchmark is within about +/-10% in the tested range.
- Some trajectory metrics improve strongly under Path C. For example, Path C lambda=1 gives trajectory RMS 0.026 versus baseline 0.087.
- The integrated fatigue budget is often close. Path C lambda=1 gives R_alpha_bar about 1.082.
- V4 symmetry can be closed by construction with C5.
- V7 side-boundary residual can be closed by construction with C4.

### Still only partly aligned

- alpha_bar_max remains the hardest local-field gap. Baseline is 9.34, C4 alone reaches 23.05, and C4 + Fourier reaches a 3-seed mean of 27.50. The Oracle/FEM scale is still much larger.
- Process-zone driver concentration improves under enriched outputs and Path C but remains below FEM scale.
- Phase 2 PCC fracture N_f is not yet produced by our own GRIPHFiTH PF-CZM run. The reference should come from Wu/Baktheer published anchors.

### Closed or retired routes

- Williams input features did not improve alpha_bar_max.
- Golahmar accumulation moved N_f away from FEM.
- Logarithmic f(alpha_bar) changed life but did not improve localization.
- Tip weighting and C6 reweighted loss both failed through optimizer pathologies.
- MIT-8 psi+ warm-up did not hold after release.
- The PCC v3 3000-cycle fatigue-indicator extrapolation is retracted as a true fracture N_f claim.

---

## 14. Suggested Advisor Storyline

1. We first built PIDL + Carrara fatigue and showed that it can reproduce N_f for the original SENT benchmark.
2. We then found that N_f agreement does not mean local-field agreement. The PIDL fields were too diffuse, and the boundary and symmetry diagnostics exposed separate errors.
3. We tried representation fixes: Williams inputs, Fourier features, and enriched outputs. These helped some quantities but did not solve the full problem.
4. We tested fatigue-law changes. They changed the life and kinetics but did not fix the missing local driver concentration.
5. We used psiHack and Oracle injection to diagnose the bottleneck. These tests showed that if the upstream psi+ driver is sharp enough, the Carrara accumulator can produce FEM-scale alpha_bar.
6. We then separated errors that should be learned from errors that should be impossible. C5 removes symmetry error by construction. C4 removes side-boundary residual by construction.
7. The best current configuration is C4 + Fourier sigma=30. It passes V7 in all three N=100 seeds and gives alpha_bar_max = 27.50 mean with 2.9% spread, about 3x the baseline.
8. Reweighted-loss attempts for further alpha_bar_max closure failed. The next principled Branch 2 option is adaptive sampling proper: change the collocation distribution without changing the variational loss.
9. Phase 2 moves the framework toward PCC concrete units. Section 5 should use Wu/Baktheer published FEM anchors and present our PCC v3 run as a fatigue-layer verification plus solver-limitation result, not as a completed fracture N_f closure.

One-sentence summary:

> I no longer judge the method only by whether it hits N_f. I use trajectory, local-zone concentration, integrated fatigue budget, symmetry, and side-boundary residual to see where PIDL is FEM-like. The current best configuration, C4 + Fourier sigma=30, closes V7 by construction and reproducibly raises alpha_bar_max to about 3x the baseline, but it still does not reach the Oracle/FEM localization scale. Phase 2 will move this framework toward PCC concrete units, using Wu/Baktheer published anchors for the FEM reference and treating our own PCC v3 run as a fatigue-layer check plus solver limitation.
