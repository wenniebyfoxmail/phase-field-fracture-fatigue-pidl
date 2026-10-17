# FEM teacher candidate library survey

**Date:** 2026-08-06  
**Purpose:** identify existing finite-element implementations that might generate trustworthy phase-field fatigue data for later PIDL training.  
**Current boundary:** this is a read-only candidate survey, not a teacher qualification, corpus authorization, or PIDL-training authorization.

## 1. Research objective

The long-term objective is not to invent another phase-field fatigue solver. It is to identify an existing FEM implementation that can generate auditable, physically credible fatigue-fracture trajectories for later PIDL training and, eventually, road-crack forecasting.

A useful teacher candidate should ideally provide all of the following:

1. An existing fatigue degradation or accumulation model.
2. A direct phase-field irreversibility constraint such as `d_old <= d <= 1`, rather than only a history-energy approximation.
3. Auditable nonlinear and coupled-solver convergence reasons.
4. Failure when an iteration cap is reached, rather than cap-as-success.
5. Raw state output without post-hoc clipping.
6. Published or machine-readable benchmark results.
7. A usable license, locked source version, and reproducible inputs.
8. A formulation that can eventually represent repeated traffic loading, temperature effects, and layered road materials.

No surveyed library should be called a teacher merely because it reproduces a paper curve or successfully completes a run.

## 2. What was searched

The survey used agent-reach/Exa technical search, GitHub repository and code search, official documentation, repository metadata, README files, source trees, selected solver source files, tests, and paper companion pages.

Representative search terms were:

```text
open source phase field fatigue fracture FEM irreversibility bound constraint benchmark
phase field fatigue FEniCS MOOSE PETSc SNES-VI
phase field fatigue SENT benchmark GitHub
Carrara phase field fatigue source code
Abaqus UEL phase field fatigue benchmark
primal-dual active set phase field fracture
```

The main questions applied to each hit were:

- Is fatigue actually implemented, rather than only mentioned?
- Is damage irreversibility enforced on the damage variable itself?
- Are upper and lower bounds explicit?
- Is coupled convergence checked after alternating displacement and phase solves?
- Does reaching the outer iteration cap produce a failure?
- Are benchmark inputs, raw outputs, tests, and licensing available?

Part of the later Exa search reached the free MCP rate limit (`HTTP 429`). The remaining checks therefore used direct GitHub and official project sources rather than search-result summaries.

## 3. Summary table

| Candidate | Existing fatigue | Direct damage bounds | Public benchmark/tests | Main limitation | Current role |
|---|---:|---:|---:|---|---|
| MOOSE/Felino | Yes | Yes, intended SNES-VI route | SENT tutorial/input and MOOSE regression infrastructure | Full fatigue run still requires strict qualification | Primary candidate platform |
| PhaseFieldX | Yes | No direct `d_old <= d <= 1` found | Cyclic SENT example, outputs, CI, JOSS paper | Miehe history-field irreversibility; coupled-cap semantics require audit | Independent fatigue-behaviour reference |
| `tjhei/cracks` | No | Yes, primal-dual active set | Published tests and regression cases | No existing fatigue model | Constraint-solver reference |
| Pavan Fatigue-Solidshell | Yes | No direct variable bounds found | Paper companion Abaqus inputs | Commercial Abaqus, history variables, no repository license | Conditional backup candidate |
| Martinez-Paneda fatigue UEL | Yes | Not established | Published UEL/input package | Commercial Abaqus and incomplete bound/stop audit | Conditional backup candidate |
| RACCOON | No existing fatigue module found | Can use MOOSE fracture machinery | Active repository and fracture tutorials | Thermal-mechanical fracture is not fatigue accumulation | Fracture-platform reference |
| `tangweinuaa/fatigue-moose` | Partial research implementation | No VI/bounds found | Only template-like diffusion test found | No usable fatigue input/regression evidence | Reject before deployment |
| Azinpour/Ferrite | Yes | No | Published behaviour reproduced | Damage overshoot, healing, no active-set/KKT qualification | Behaviour reference only |
| GRIPHFiTH | Yes | Subproblem bounds/KKT passed | Existing project qualification package | Coupled damage increment did not converge; outer cap reached | Not an unconditional teacher |
| PhiPsi Phase-Field-Fracture | Claimed | Not established | Minimal examples | No detected license and old/inactive snapshot | Low-priority research code |
| `manirm/phaseField_fatigue` | Indirectly | Inherits PhaseFieldX limitations | GUI tests and specimen meshes | Wrapper around PhaseFieldX, not an independent solver | Do not count as independent evidence |
| Battery-Li-Ion-Simulation-Fatigue | Yes, chemo-mechanical | Not established | Application examples | Different battery physics and no detected license | Not a road-fatigue teacher candidate |
| EasyFEA | No | History-based quasi-static route | Mature package, CI, many tests | No existing fatigue accumulation model | General FEM/fracture reference |
| Tao Jin deal.II solvers | No | History-energy irreversibility | Standard fracture benchmarks | Monotonic fracture rather than fatigue | Solver-convergence reference |
| `phase_field_exact_linesearch` | No | Requires separate detailed audit | Paper reproduction code | Brittle fracture only | Iterative-solver reference |
| PhaseFieldComp | No | Not established | Published composite-fracture examples | Abaqus, composite fracture, not fatigue | Out of scope |

## 4. Candidate details and shortcomings

### 4.1 MOOSE/Felino

Sources:

- [Felino repository](https://github.com/DanielChou0916/felino)
- [Felino cyclic SENT tutorial](https://danielchou0916.github.io/felino.github.io/tutorials/1_sent_cyclic_pulling/)
- [MOOSE phase-field fracture stress documentation](https://mooseframework.inl.gov/source/materials/ComputeLinearElasticPFFractureStress.html)

Why it remains the leading candidate:

- Felino supplies an existing fatigue implementation and cyclic SENT inputs.
- MOOSE supports PETSc SNES variational-inequality solvers.
- `VariableOldValueBounds` can provide the previous damage as a lower bound.
- `ConstantBounds` can provide an upper bound of one.
- `vinewtonrsls` or `vinewtonssls` can solve the bound-constrained phase problem.
- The author confirmed that the tutorial uses a loosely coupled approach and a bounding approach rather than only historical-energy restriction.

Remaining shortcomings and unresolved questions:

- A successful MOOSE installation or native fracture regression is not a fatigue-teacher qualification.
- Each displacement and phase subsolve can converge while the alternating coupled state remains inconsistent.
- The full SENT route must demonstrate coupled fixed-point convergence at every accepted step.
- Reaching the outer iteration cap must be a failure, not a successful accepted step.
- Raw damage must satisfy `d_old <= d <= 1` without clipping.
- Solver reasons, accepted-step semantics, fatigue observables, mesh sensitivity, and physical benchmark agreement remain required.

Current status: **candidate platform only**. It is not yet an authorized teacher.

### 4.2 PhaseFieldX

Sources:

- [PhaseFieldX repository](https://github.com/CastillonMiguel/phasefieldx)
- [PhaseFieldX documentation](https://phasefieldx.readthedocs.io/)
- [JOSS paper](https://doi.org/10.21105/joss.07307)

Strengths:

- MIT licensed and based on FEniCSx.
- Has CI, documentation, install instructions, source code, and published software documentation.
- Includes a cyclic single-edge-notched-tension fatigue example, mesh, selected VTU output, energy files, reaction files, and convergence output.
- Implements a Carrara-style fatigue degradation route.
- Relatively easy to install and reproduce compared with a large MOOSE build.

Shortcomings confirmed from the inspected solver path:

- `irreversibility="miehe"` updates a maximum tensile-energy history field. This is not the same as directly imposing `d_old <= d <= 1`.
- The phase subproblem uses an ordinary nonlinear solve; no SNES-VI or equivalent damage-variable bound solve was found in the inspected path.
- The solver checks convergence reasons for the individual displacement and phase subsolves, but a separate strict audit is still needed for outer staggered convergence and iteration-cap failure semantics.
- Its published SENT example is useful behavioural evidence, but it is not experimental ground truth.

Current status: **best independent open fatigue-behaviour reference**, but not a strict teacher under the present admissibility requirements.

### 4.3 `tjhei/cracks` (`pfm-cracks`)

Source: [`tjhei/cracks`](https://github.com/tjhei/cracks)

Strengths:

- deal.II-based parallel adaptive FEM.
- Implements a primal-dual active-set method for fracture irreversibility.
- Supports 2D and 3D fracture.
- Provides published versions, regression cases, and GPL-2.0-or-later licensing.
- Strong candidate for checking whether another implementation's active-set and irreversibility behaviour is numerically plausible.

Shortcomings:

- No existing fatigue accumulation or degradation model was found.
- Adding fatigue would create a new adapted solver rather than selecting a ready-made teacher.
- Its published problems are primarily monotonic or pressurized fracture benchmarks, not road fatigue.

Current status: **constraint-mechanism reference**, not an existing fatigue producer.

### 4.4 Pavan Fatigue-Solidshell

Source: [`Pavan-asur/Fatigue-Solidshell`](https://github.com/Pavan-asur/Fatigue-Solidshell)

Strengths:

- Provides Abaqus UEL/UMAT source and example inputs for fatigue and non-fatigue simulations.
- Accompanies a published 2023 phase-field fatigue paper.
- Includes shear and three-point-bending examples and homogeneous/layered-material capability.

Shortcomings:

- Requires commercial Abaqus and a compatible Fortran compiler.
- The inspected source uses maximum-energy and fatigue history variables; no native damage-variable VI bounds were identified.
- The GitHub repository has no detected license.
- Solver convergence, rollback, outer-coupling, raw damage bounds, and cap semantics still need qualification.
- The solid-shell/composite focus is not directly aligned with a layered asphalt-road SENT problem.

Current status: **backup only if a licensed Abaqus environment is already available**.

### 4.5 Martinez-Paneda Abaqus fatigue implementations

Source: [Abaqus UEL for phase-field fatigue and quasi-Newton](https://www.empaneda.com/codes/abaqus-uel-for-phase-field-fatigue-quasi-newton/)

Strengths:

- Published research code from an established phase-field fracture group.
- Includes a UEL, input file, quasi-Newton configuration, and instructions.
- Relevant fatigue and fracture formulations have been exercised in published studies.

Shortcomings:

- Requires commercial Abaqus.
- Public availability of code does not by itself establish redistribution rights or a suitable open-source license.
- Direct `d_old <= d <= 1` variable bounds were not established by this survey.
- Abaqus job completion does not automatically prove coupled convergence, raw-state admissibility, or absence of cap-as-success.
- Reproducibility depends on Abaqus version, compiler, subroutine interface, and proprietary solver behaviour.

Current status: **potential published-code backup**, requiring a separate license and numerical-semantics audit.

### 4.6 RACCOON

Sources:

- [RACCOON repository](https://github.com/hugary1995/raccoon)
- [RACCOON modules documentation](https://hugary1995.github.io/raccoon/modules/index.html)

Strengths:

- Active LGPL-2.1 MOOSE-based phase-field fracture application.
- Includes many brittle, cohesive, ductile, thermal-mechanical, and adaptivity tutorials.
- Suitable for large parallel fracture calculations.
- Benefits from MOOSE infrastructure and phase-field fracture machinery.

Shortcomings:

- No ready-made fatigue degradation/accumulation module was found by repository code search.
- Official documentation describes thermal-mechanical-fracture coupling, not repeated-load fatigue accumulation.
- Repeating a mechanical load is not automatically a fatigue model: an internal cycle-history law is still required.
- Adding a fatigue law would become model development and is outside the current candidate-selection stage.

Road relevance:

- Mechanical means solving displacement, strain, stress, and material force balance.
- Thermal-mechanical fracture is useful for temperature-shrinkage cracks and combined temperature/load fracture.
- Real road fatigue additionally needs cyclic accumulation, temperature-dependent viscoelastic or viscoplastic response, layered interfaces, traffic spectra, and eventually moisture, ageing, or freeze-thaw effects.

Current status: **useful fracture platform, but not an out-of-the-box road-fatigue teacher**.

### 4.7 `tangweinuaa/fatigue-moose`

Source: [`tangweinuaa/fatigue-moose`](https://github.com/tangweinuaa/fatigue-moose)

Strengths:

- Contains C++ kernels and material code for a MOOSE-based fatigue-fracture research implementation.
- LGPL-2.1 license is declared by GitHub.

Shortcomings:

- README is essentially a generated MOOSE application stub.
- No usable fatigue input deck or fatigue benchmark was found in the repository tree.
- The visible test is a template-like simple-diffusion test, not a fatigue fracture regression.
- No `VariableOldValueBounds`, `ConstantBounds`, or SNES-VI configuration was found.
- Compiled `.so` and intermediate build products are committed, weakening provenance and portability.

Current status: **reject before deployment** because it lacks the minimum evidence needed for qualification.

### 4.8 Azinpour/Ferrite

Strengths:

- Existing Julia/Ferrite implementation.
- Published R=0.1 SENT crack-length endpoint and solver-count statistics were reproduced.
- Provides useful independent phase-field fatigue behaviour for comparison.

Known shortcomings from the existing audit:

- Uses a maximum-history energy formulation rather than explicit old-damage lower bounds and an active-set/KKT solve.
- Raw native output exceeded the nominal damage upper bound.
- Adjacent checkpoints showed healing/decreasing damage.
- No direct damage active-set or projected-KKT qualification was available.

Current status: **paper-behaviour reproduction passed; strict teacher qualification failed**.

### 4.9 GRIPHFiTH

Strengths:

- Existing FEM implementation aligned with prior project settings.
- Windows Hard5 replay was reproduced.
- Projected KKT and primal-bound checks passed for the audited phase subproblems.

Known shortcomings:

- The strict coupled qualification reached the outer cap of 100 iterations.
- The damage-increment gate failed for all 100 recorded outer iterations.
- The active set oscillated near the crack tip.
- The final decision was `failed_to_converge`, not a successful teacher state.

Current status: **not an unconditional teacher**. Subproblem admissibility did not establish coupled convergence.

### 4.10 Lower-priority and adjacent repositories

#### PhiPsi Phase-Field-Fracture

Source: [`PhiPsi-Software/Phase-Field-Fracture`](https://github.com/PhiPsi-Software/Phase-Field-Fracture)

- Claims fracture and fatigue capability and contains Python examples.
- No license was detected.
- Repository activity and evidence are limited, and no explicit bound-constrained solver was established.
- Lower priority than PhaseFieldX.

#### `manirm/phaseField_fatigue`

Source: [`manirm/phaseField_fatigue`](https://github.com/manirm/phaseField_fatigue)

- Provides a desktop interface, meshes, plotting, and workflow around PhaseFieldX/FEniCSx.
- It does not provide an independent numerical formulation or independent solver evidence.
- It inherits PhaseFieldX's qualification limitations and must not be counted as a separate confirming implementation.

#### Battery-Li-Ion-Simulation-Fatigue

Source: [`noiiG/Battery-Li-Ion-Simulation-Fatigue`](https://github.com/noiiG/Battery-Li-Ion-Simulation-Fatigue)

- Implements a FEniCS fatigue phase-field application for battery charge/discharge.
- The chemo-mechanical swelling problem is materially different from road traffic fatigue.
- No repository license was detected.
- It may provide formulation ideas but is not a direct road-crack teacher candidate.

#### EasyFEA

Source: [`matnoel/EasyFEA`](https://github.com/matnoel/EasyFEA)

- Mature GPL-3.0 Python FEM package with CI, PyPI releases, tests, and phase-field damage examples.
- Its advertised phase-field capability is quasi-static brittle fracture, not fatigue accumulation.
- Useful for general FEM comparison, but adopting it would require adding a fatigue model.

#### Tao Jin deal.II solvers

Sources:

- [`taojinllnl/Phasefield_staggered_approach`](https://github.com/taojinllnl/Phasefield_staggered_approach)
- [`taojinllnl/Phasefield_L-BFGS_monolithic_solver`](https://github.com/taojinllnl/Phasefield_L-BFGS_monolithic_solver)

- Provide well-described staggered and monolithic solver research implementations and standard brittle-fracture benchmarks.
- Irreversibility is based on a maximum-history energy approach.
- No existing fatigue model was found.
- Useful for studying iterative convergence, not as an existing fatigue teacher.

#### Exact-linesearch and cohesive FEniCSx research codes

Source: [`jonas-heinzmann/phase_field_exact_linesearch`](https://github.com/jonas-heinzmann/phase_field_exact_linesearch)

- Reproducible solver research with locked FEniCSx/PETSc versions and paper examples.
- Focuses on brittle fracture iterative convergence rather than fatigue.
- Useful as solver-method evidence but outside the current ready-made fatigue requirement.

#### PhaseFieldComp

Source: [`MCM-QMUL/PhaseFieldComp`](https://github.com/MCM-QMUL/PhaseFieldComp)

- Published MIT-licensed source for composite phase-field fracture in Abaqus.
- It is not a fatigue implementation and requires commercial Abaqus.
- It does not address the present teacher bottleneck.

## 5. Why the subsolve distinction matters

In a staggered method, a displacement solve may satisfy

```text
R_u(u_(k+1), d_k) approximately 0
```

and the following phase solve may satisfy

```text
R_d(u_(k+1), d_(k+1)) approximately 0.
```

After damage changes from `d_k` to `d_(k+1)`, however, the same displacement may no longer satisfy mechanical equilibrium:

```text
R_u(u_(k+1), d_(k+1)) not approximately 0.
```

Therefore a teacher qualification must check the final coupled state, not only the two inner solver reasons. At minimum it should audit displacement residual, phase projected KKT or equivalent VI residual, damage increment, primal bounds, and the outer fixed-point exit reason.

Similarly, an outer loop ending because `iteration == max_iterations` is not convergence. The accepted-step logic must explicitly distinguish:

```text
coupled error <= tolerance       -> CONVERGED
iteration >= maximum iterations -> FAILED_REACH_MAX_ITS
```

An iteration cap must never be accepted merely because the loop has stopped.

## 6. Road-crack relevance

No current candidate by itself proves suitability for real-road forecasting.

The eventual road producer will need a staged evidence chain:

1. Numerically admissible phase-field fracture states.
2. Qualified fatigue accumulation under repeated loading.
3. Mesh, time-step, and cycle-jump convergence.
4. Agreement with a published numerical benchmark that uses a clearly mapped formulation.
5. Agreement with independent experimental crack-growth or fatigue-life data.
6. Road-relevant material behaviour, including temperature dependence and asphalt viscoelasticity or viscoplasticity.
7. Layer and interface representation.
8. Traffic-spectrum and environmental loading.
9. Leakage-safe validation against observed road trajectories before any real forecasting claim.

Thermal-mechanical fracture is relevant to road cracking, especially temperature-shrinkage cracking, but it does not replace a fatigue history law. Repeated application of a load is not sufficient if the material model has no cycle-dependent degradation or accumulation state.

## 7. Recommended candidate hierarchy

### Tier 1: continue qualification

**MOOSE/Felino** remains the only identified candidate that combines an existing cyclic fatigue SENT implementation with a plausible native SNES-VI damage-bound route.

Required claim boundary: passing the current stage would promote it only to a **fatigue-model qualification candidate**, not directly to a teacher.

### Tier 2: independent references

- **PhaseFieldX:** independent fatigue behaviour and cyclic SENT reference.
- **`tjhei/cracks`:** independent irreversibility and active-set mechanism reference.

These two references test different dimensions. Neither should be treated as ground truth.

### Tier 3: conditional commercial backup

- Martinez-Paneda Abaqus fatigue code.
- Pavan Fatigue-Solidshell.

Only consider these if an existing licensed Abaqus environment is available and a separate source/license/constraint audit is acceptable.

### Reject or defer

- `tangweinuaa/fatigue-moose`: insufficient inputs, tests, and bound evidence.
- PhiPsi: insufficient maintenance, license, and solver evidence.
- GUI wrappers: not independent implementations.
- RACCOON, EasyFEA, Tao Jin solvers, PhaseFieldComp, and exact-linesearch codes: useful adjacent fracture tools but no ready-made fatigue teacher.

## 8. Bottom-line conclusion

The search found several useful libraries, but no hidden ready-made candidate that clearly dominates MOOSE/Felino under the strict teacher criteria.

The most defensible strategy is triangular qualification:

```text
MOOSE/Felino  -> candidate fatigue producer with native SNES-VI
PhaseFieldX   -> independent cyclic-fatigue behaviour reference
pfm-cracks    -> independent active-set/irreversibility reference
```

This avoids assuming that Azinpour, PhaseFieldX, or any published curve is automatically correct. It also avoids developing a new fatigue algorithm before the existing MOOSE/Felino candidate has completed its numerical and physical qualification gates.
