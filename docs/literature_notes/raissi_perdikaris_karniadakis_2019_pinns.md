# Raissi, Perdikaris and Karniadakis (2019): foundational PINNs

## Bibliographic record

- **Paper:** M. Raissi, P. Perdikaris and G. E. Karniadakis, "Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations"
- **Journal:** *Journal of Computational Physics* 378 (2019), 686-707
- **DOI:** [10.1016/j.jcp.2018.10.045](https://doi.org/10.1016/j.jcp.2018.10.045)
- **Local version of record:** `upload code/references/dr_literature_batch_2026-06-19/D_pinn_operator/Raissi_Perdikaris_Karniadakis_2019_JCP_PINNs.pdf`
- **PDF SHA-256:** `d76375e7834b3381da5d53a4238378b5d5e5b63fb9f9e5fa7210a89f551a5a59`
- **Full-text status:** 22-page Elsevier version of record read and visually checked
- **Read on:** 2026-07-27

Crossref and OpenAlex independently resolve the title to the DOI above. The public OSTI download associated with the record is the earlier arXiv Part I manuscript (`arXiv:1711.10561`), not the exact combined journal version; the existing local Elsevier PDF is therefore the preferred full text. The companion arXiv Part II manuscript is `arXiv:1711.10566`.

## One-sentence verdict

This is the correct foundational citation for the PINN idea and a useful conceptual template for observation-constrained hidden-state inversion, but it is not direct evidence for phase-field fracture, fatigue-history evolution, autonomous crack forecasting, uncertainty calibration, or real-data validation.

## What the paper actually introduces

The paper separates two tasks:

1. **Data-driven solution:** infer a latent solution field when the differential operator and parameters are fixed.
2. **Data-driven discovery:** infer unknown operator parameters, and sometimes an unobserved field, from partial measurements.

For continuous time, a neural approximation `u(t, x)` is differentiated by automatic differentiation and trained with

```text
MSE = data / boundary loss + PDE residual loss.
```

The PDE residual is enforced at collocation points. For discrete time, the network outputs the hidden stages of an implicit Runge-Kutta scheme, so known time-integration structure becomes part of the neural representation.

The paper uses ordinary fully connected `tanh` networks and L-BFGS. It does not introduce a fracture-specific architecture, a graph network, a neural operator, or a probabilistic posterior.

## Verified results and locators

| Result | Verified evidence | Locator |
|---|---|---|
| Continuous PINN loss combines initial/boundary data and PDE residual at collocation points. | Equations (3)-(4) define the shared `u` and residual networks. | pp. 688-689 |
| Sparse data can be amplified by known physics in smooth benchmark PDEs. | Schrodinger example uses 50 initial points, 50 boundary times, and 20,000 Latin-hypercube collocation points; relative L2 error is `1.97e-3`. | pp. 689-690, Fig. 1 |
| A discrete physics-informed transition can bridge widely separated snapshots. | Allen-Cahn example predicts from `t=0.1` to `t=0.9` using 200 initial points, a 100-stage implicit Runge-Kutta representation, and one step; relative L2 error is `6.99e-3`. | pp. 690-692, Fig. 2 |
| Physics can expose an unmeasured field while fitting unknown parameters. | Navier-Stokes example uses velocity observations without pressure labels; the network recovers a pressure field up to a constant and estimates the two operator parameters from 5,000 sampled points. | pp. 693-695, Figs. 3-4 |
| The authors do not claim replacement of FEM or other classical solvers. | The conclusion explicitly argues for coexistence between neural networks and classical numerical methods. | pp. 696-697 |
| Architecture, optimization, loss choice, robustness and uncertainty remain unresolved. | The conclusion lists these as open questions and notes that settings successful for one equation can fail for another. | p. 697 |

## Evidence boundaries

- All reported examples are numerical PDE benchmarks generated with analytical, spectral, or high-order solver references.
- There is no phase-field fracture, crack-tip singularity, fatigue history, irreversibility constraint, material degradation field, or experimental crack data.
- The continuous formulation can require many global collocation points; the paper itself identifies high-dimensional scaling as a bottleneck on p. 690.
- Appendix Table A.1 is strongly non-monotone in training/collocation-point count. More points do not automatically give a better result because optimization and representation still matter.
- The high-stage Runge-Kutta result assumes a known smooth evolution equation and does not establish that irreversible, path-dependent fatigue evolution can be cycle-jumped safely.
- Uncertainty is proposed as future work rather than demonstrated.
- The paper validates within individual benchmark equations; it does not perform leave-one-geometry, leave-one-load-path, or leave-one-physical-trajectory-out validation.

## Implications for our research

### 1. Use it as the conceptual PINN citation, not the direct fracture-method citation

For our method section, Raissi et al. is the foundation for automatic-differentiation physics constraints and forward/inverse task separation. Our actual solver is closer to **Deep Ritz / variational PIDL**: it minimizes the AT1-Carrara energy terms `E_el + E_d + E_hist` per cycle. The direct phase-field-fracture methodological anchors remain Goswami et al. (2020), Ghaffari Motlagh et al. (2023), and Manav et al. (2024).

### 2. The hidden-pressure example is the closest conceptual analogue to our current inverse problem

The Navier-Stokes example infers pressure without pressure labels because observed velocity and the governing equations constrain it. Our analogous target is a hidden degradation/process-zone field inferred from visible crack geometry, load-reaction response, and sparse DIC mechanics without using phase-field labels.

The analogy is useful, but it is not evidence of identifiability. Our completed c86 reaction-conditioned inversion already shows the limit:

- one reaction curve identified a scalar aligned-skeleton amplitude (`beta=3.146756`);
- the same global reaction could also be matched by a spatially shifted reconstruction;
- c89 active-support IoU remained only `0.236`, while the shifted control fell to `0.0045`.

Therefore a global reaction observes effective stiffness amplitude, not the spatial process zone. The next useful inverse target is a bounded spatial field such as `log10(g(alpha))`, constrained by registered crack geometry plus spatially resolved DIC/strain and multiple load states.

### 3. Preserve the forward/inverse/forecasting distinction

The paper's "data-driven solution" and "data-driven discovery" are both conditioned inference problems. They do not demonstrate autonomous forecasting through an unseen fracture transition. For our project, the following claims must stay separate:

- inverse state assimilation at c86;
- conditional propagation from a supplied near-critical state;
- autonomous c87/c89 forecasting;
- material or fatigue-parameter identification.

Success in the first two cannot be cited as proof of the last two.

### 4. Borrow the structured-transition idea, not the Runge-Kutta claim verbatim

The discrete-time section suggests embedding a known transition rule between sparse inspection snapshots rather than fitting an unconstrained sequence model. For fatigue fracture, the transferable idea is to encode the **incremental phase-field equilibrium plus irreversible history update** between inspections.

We should not copy the "one very large time step" interpretation directly. Crack onset, inequality constraints, fatigue degradation, and event transitions are path dependent. Any inspection-to-inspection bridge must carry the necessary hidden history state and be checked at held-out intermediate cycles and at the process-zone field level.

### 5. Keep FEM as the physical reference and transition-library interface

The paper explicitly does not position PINNs as replacements for classical solvers. This supports our current hierarchy:

- FEM remains the physical reference and a candidate transition model;
- PIDL is evaluated by FEM-centred field and mechanism gates;
- real observations enter through an explicit observation model;
- a faster neural method is promoted only under identical observation and uncertainty gates.

### 6. Do not respond with another architecture or collocation-size sweep

The paper's own sensitivity table and open questions show that network size and point count are not monotone guarantees. Our local evidence is stronger and fracture-specific: multiple local heads, Fourier/SIREN variants, FBPINNs, adaptive sampling, and mesh-local corrections changed timing or bookkeeping without closing the active-driver/process-zone mismatch.

The actionable question is now observability and spatial state semantics, not whether a larger vanilla PINN can fit the same trajectory.

## PIDL Experiment Gate

- **Mechanism question:** Can pre-target, deployable spatial observations identify the c86 degradation/process-zone field well enough to improve locked c87 raw-driver and c89 active-support fields?
- **Claim changed if success:** Observation-conditioned spatial inversion becomes a credible bridge from real sensing to conditional fracture propagation.
- **Claim changed if failure:** Crack geometry, reaction and the proposed sparse mechanics tier are insufficient; richer sensing or a stronger transition prior is required.
- **Cheaper diagnostic first:** Reuse the completed reaction-conditioned package; evaluate sensitivity/rank and spatial non-uniqueness using existing c86 load states and candidate DIC locations before any neural training.
- **Minimal output asset:** One identifiability/sensitivity table plus a locked c87/c89 FEM-centred field figure and `decision.md`.
- **Code/producer alignment:** Analysis-only on Mac first. Any PIDL training remains producer-only after external experiment-plan review.
- **Success criteria:** Predeclared improvement over both scalar-beta and pointwise controls in c87 raw log error/correlation and c89 absolute-support IoU/area ratio, with no c87/c89 target-field leakage.
- **Failure criteria:** Non-unique observation Jacobian, shifted/spatial controls matching observations equally well, or field gates failing despite observation fit.
- **Registry destination:** Supporting/negative result in the aligned evidence registry; update the research frontier only if the spatial observability verdict changes the active branch.
- **Decision:** Diagnose first; do not launch a new vanilla-PINN or architecture sweep from this paper alone.

## Citation-ready use

```bibtex
@article{Raissi2019PINNs,
  author  = {Raissi, Maziar and Perdikaris, Paris and Karniadakis, George Em},
  title   = {Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations},
  journal = {Journal of Computational Physics},
  volume  = {378},
  pages   = {686--707},
  year    = {2019},
  doi     = {10.1016/j.jcp.2018.10.045}
}
```
