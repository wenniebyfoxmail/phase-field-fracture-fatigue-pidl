# Deep Research Report

**Topic**: High-frequency components, crack-tip singularity, and discontinuity handling in neural PDE / fracture solvers  
**Date**: 2026-05-11  
**Project context**: PIDL vs FEM field-level gap in phase-field fatigue fracture

## 1. Executive summary

The current PIDL-FEM gap is not well explained by "the neural network cannot learn high frequencies" alone. That statement is too weak and too generic. The evidence in this project points to a more specific mechanism:

1. the target field contains a **localized singular or near-singular structure** near the crack tip,
2. this structure occupies a **very small spatial support** relative to the full domain,
3. the optimizer is free to reach many solutions with similar global energy and similar `N_f`,
4. the collocation / quadrature budget is dominated by the bulk domain rather than the crack-tip process zone,
5. therefore the network can match global life and even integrated damage budget while still missing the correct local spatial organization.

This means the next useful question is not "how do we make the network more high-frequency?" but:

**How do we explicitly allocate model capacity, samples, and constraints to the crack-tip process zone and the discontinuity/singularity structure?**

The literature suggests three main families of solutions:

1. **spectral-bias mitigation**: Fourier features, SIREN, multi-scale Fourier embeddings, adaptive activations, momentum, frequency upscaling, transfer learning;
2. **localization / decomposition**: FBPINNs, multilevel FBPINNs, adaptive sampling, local patch networks, partition-of-unity style basis composition;
3. **fracture-specific enrichment**: XFEM/PUM-style enrichment, crack-tip asymptotic enrichment, signed-distance-based discontinuity embedding, and neural methods that explicitly encode crack surfaces and near-tip singularity.

For this project, the third family is the most relevant, and the second family is the best support layer for it.

## 2. Three core concepts in plain English

### 2.1 Optimization basin

An optimization basin is a region of parameter space that gradient descent can fall into and stay in. Different basins can produce solutions with similar training loss but different field shapes.

In this project, the Oracle multi-seed behavior already points in this direction: similar `N_f`, very different `alpha_bar_max` and field geometry. That is the signature of a **multimodal loss landscape**. The network is not learning one unique physical field. It is choosing one of several field organizations that all satisfy the coarse objectives reasonably well.

In crack problems this is especially plausible because:

1. the loss is global,
2. the crack-tip zone is small,
3. boundary and symmetry defects can be traded against local concentration,
4. the fatigue chain integrates effects over many cycles, which can hide local field differences.

So "wrong basin" here does not mean the optimizer is broken. It means the current objective leaves too much freedom in how the field is spatially arranged.

### 2.2 Sampling dilution

Sampling dilution means the important region is too small a fraction of the total samples or quadrature points. The crack-tip process zone may drive fracture, but the optimizer sees far more bulk points than tip points.

If most samples come from smooth regions, the learned solution is pulled toward what helps the bulk residual or bulk energy. The crack-tip peak then gets averaged away. This is exactly the kind of failure adaptive PINN papers target when they re-sample points into high-residual or failure regions.

In this project, "sampling dilution" should be read very concretely:

1. the tip zone is small in area,
2. the crack-tip driver `g(alpha) psi+` is highly localized,
3. global training objectives can still be reduced without reproducing the correct local peak,
4. therefore the learned field is too smooth and too spread out.

### 2.3 SDF

SDF means **signed distance function**.

For a crack surface `Gamma_c`, an SDF `d(x)` gives:

1. distance to the crack geometry,
2. a sign that tells which side of the crack the point lies on,
3. special values near the crack tip when combined with a tip location.

Typical uses:

1. `sign(d(x))` or a smoothed sign gives a discontinuity indicator across the crack faces;
2. `|d(x)|` gives distance to the crack line;
3. a separate tip distance `r(x) = ||x - x_tip||` and angle `theta(x)` describe near-tip asymptotics.

SDFs are attractive because they convert geometry into functions that can be fed into a neural network or used to build hard constraints.

## 3. What does "explicit embedding" mean?

It means the geometric or asymptotic structure is not left for the MLP to discover from raw `(x, y)` alone. Instead, we **build the structure into the representation**.

There are three common levels of explicitness.

### 3.1 Feature embedding

We augment the input:

`x -> [x, y, r, theta, sqrt(r), sin(theta/2), cos(theta/2), H_crack, d_crack, ...]`

This is the mildest form. It says: "network, here are coordinates adapted to the crack geometry."

This is close to what Williams-style features already tried in your repo.

### 3.2 Ansatz enrichment

We decompose the output into a regular part plus explicit enriched terms:

`u(x) = u_reg(x; theta) + sum_k a_k(x; theta) Phi_k(x)`

where `Phi_k` are known enrichment functions, such as:

1. Heaviside jump across crack faces,
2. crack-tip asymptotic functions from Williams expansion,
3. oscillatory interface-crack terms,
4. local patch functions supported near the tip.

This is closer to XFEM logic. The NN learns amplitudes or smooth corrections, while the singular structure is represented directly by `Phi_k`.

### 3.3 Embedded discontinuity representation

We explicitly feed discontinuity descriptors into the network or build them into the trial space so the network can represent jumps or weak discontinuities without relying on a globally smooth MLP.

This is the logic of DEDEM and DENNs: use SDF-derived functions so the network "knows" there is a crack surface and a tip.

## 4. What XFEM / PUM-style neural enrichment means

### 4.1 Classical XFEM / PUM idea

In XFEM and Partition of Unity Methods, the approximation is expanded as:

`u_h(x) = sum_i N_i(x) u_i + sum_j N_j(x) H(x) a_j + sum_k N_k(x) sum_m F_m(r, theta) b_k^m`

where:

1. `N_i(x)` are the standard shape functions,
2. `H(x)` is a jump function across the crack,
3. `F_m(r, theta)` are crack-tip asymptotic enrichment functions.

The point is simple: the approximation space is enlarged to contain the right discontinuity and singularity.

### 4.2 Neural translation of XFEM / PUM

The neural analogue is:

`u(x) = u_bulk(x; theta_b) + w_jump(x; theta_j) H(x) + sum_m w_m(x; theta_t) F_m(r, theta)`

Possible implementations:

1. `u_bulk` is a smooth MLP for the far field,
2. `w_jump` is a scalar or vector NN controlling crack-face displacement jump,
3. `w_m` are NN-produced amplitudes for each crack-tip basis function,
4. support is optionally localized with a window `chi(r)` so enrichment acts only near the tip.

This is more powerful than feeding `r` and `theta` as plain features. It changes the **solution space**, not just the coordinates.

### 4.3 Why this matters for your project

Your current negative results suggest the network does not fail only because it lacks crack-aware coordinates. It fails because the trial space remains mostly globally smooth. A smooth global MLP can still choose to under-concentrate the driver even if it sees `(r, theta)`.

XFEM-style neural enrichment attacks that exact weakness.

## 5. What SDF / discontinuity embedding means in technical terms

The main idea is to convert crack geometry into auxiliary functions and inject them into the representation.

### 5.1 Input embedding version

Use:

`z(x) = [x, y, d(x), sign_eps(d(x)), r(x), theta(x)]`

and feed `z(x)` into the network instead of only `(x, y)`.

This helps the network separate the two crack faces and identify the tip neighborhood.

### 5.2 Output embedding version

Build:

`u(x) = u_smooth(z; theta) + q(z; theta) H_eps(d(x))`

where `H_eps` is a sharp or smoothed Heaviside-type function.

This allows a displacement jump across the crack without forcing the base network to create a jump using only smooth activations.

### 5.3 Hybrid crack-tip version

Add crack-tip asymptotic channels:

`u(x) = u_smooth + q_jump H_eps(d) + sum_m q_m(z; theta) F_m(r, theta)`

This is the closest neural analogue to discontinuity plus crack-tip enrichment in XFEM.

### 5.4 Why SDF methods are attractive

1. crack geometry enters directly;
2. no remeshing-style basis update is needed in the same way as FEM;
3. the method can be extended to curved cracks and evolving cracks if the SDF is updated;
4. the jump and tip structure can be localized and controlled.

## 6. What the high-frequency literature actually says

### 6.1 Fourier features

Fourier features help standard MLPs learn higher frequencies by mapping coordinates into sinusoidal features with tunable bandwidth. This directly targets spectral bias.

But this family is strongest for **oscillatory functions**, not necessarily for **localized fracture singularities plus discontinuities**. Your existing negative Fourier result is therefore not surprising.

### 6.2 SIREN

SIREN replaces standard activations with sinusoidal activations. It is good at representing detailed fields and derivatives. It can be useful in crack problems, especially in local patches, but by itself it still does not encode "there is a crack here."

So SIREN is better viewed as a possible **local enriched subnetwork**, not a standalone cure.

### 6.3 Multi-scale Fourier / eigenvector-bias work

Wang, Wang, and Perdikaris show that PINNs are biased toward dominant NTK eigen-directions and propose multi-scale Fourier embeddings. This is stronger than naive Fourier features because it explicitly targets multi-scale PDE failures.

This is relevant if the project wants a better crack-tip local subnetwork, but still not enough as the whole answer.

### 6.4 Adaptive activations, momentum, frequency continuation

These methods help optimization:

1. adaptive activations reshape the loss landscape,
2. momentum reduces spectral bias during training,
3. frequency upscaling and transfer learning solve easier low-frequency tasks first, then move to harder ones.

These methods are valuable when the target solution already has the right representation. They are less powerful if the trial space itself is missing jump/singularity structure.

## 7. What the fracture-specific literature says

### 7.1 Enriched crack PINNs

Recent fracture papers are explicitly moving away from plain coordinate-to-field MLPs.

Examples:

1. enriched PINNs for interface cracks use known near-tip asymptotic functions to capture oscillatory singular behavior;
2. enriched holomorphic neural networks split the singular and regular parts in crack elasticity;
3. X-PINN-style fracture methods combine standard and enriched neural components with crack-tip functions;
4. DEDEM and DENNs use SDF-derived discontinuity embeddings to represent crack surfaces and tips directly.

The unifying idea is not "make the network deeper." It is:

**make the approximation space look more like fracture mechanics.**

### 7.2 Why these papers matter more than generic PINN high-frequency papers

The relevant pathology in fracture is often not a globally high-frequency wave. It is a **localized singular field plus a discontinuity set**. That is a different approximation problem.

Generic high-frequency methods help, but fracture-specific enrichment methods attack the geometry and asymptotics directly.

## 8. Literature map for this project

### Tier A: directly relevant to the next project branch

1. FBPINNs / multilevel FBPINNs: local subdomains for local high-frequency or multiscale behavior.
2. Exact boundary-condition imposition with distance functions: useful for your `V7` side-boundary weakness.
3. Symmetry-enhanced PINN ideas: useful for your `V4` weakness.
4. DEDEM / DENNs / enriched fracture PINNs: most directly aligned with crack-tip and discontinuity representation.

### Tier B: likely useful as supporting techniques

1. SIREN in a tip-local subnetwork,
2. multi-scale Fourier embeddings in a tip-local subnetwork,
3. adaptive sampling in process-zone or high-residual regions,
4. transfer learning or continuation from easier cases to harder cases.

### Tier C: lower-priority as standalone main branches

1. another global Fourier-feature branch,
2. another small activation swap on the whole-domain MLP,
3. another fatigue-law-only perturbation without representation change.

## 9. Most plausible technical designs for PIDL

### Design 1: bulk-tip decomposition

Build:

`u(x) = u_bulk(x; theta_b) + chi(r) u_tip(r, theta; theta_t)`

`alpha(x) = alpha_bulk(x; phi_b) + chi(r) alpha_tip(r, theta; phi_t)`

where `chi(r)` is a compact support or smooth window around the crack tip.

Recommended choices:

1. `u_bulk`, `alpha_bulk`: current smooth architecture;
2. `u_tip`, `alpha_tip`: SIREN or multi-scale Fourier local network;
3. local sampling concentrated in `B_{2l0}(x_tip)`;
4. symmetry and boundary constraints kept explicit.

This is the simplest branch that genuinely changes capacity allocation.

### Design 2: neural XFEM enrichment

Build:

`u = u_bulk + q_jump H_eps(d) + sum_m q_m F_m(r, theta)`

Implementation choices:

1. fixed analytical `F_m`,
2. trainable amplitudes `q_m`,
3. optional localization `chi(r)`,
4. separate losses for symmetry, side BC, and process-zone concentration.

This branch is conceptually strongest if the goal is crack-tip realism.

### Design 3: SDF/discontinuity embedding plus adaptive sampling

Inputs:

`[x, y, d, sign_eps(d), r, theta]`

Training:

1. oversample near crack tip,
2. re-sample by large residual or large `g psi` mismatch proxy,
3. impose hard or near-hard BC trial functions,
4. optionally mirror points to enforce symmetry.

This is cheaper than full neural XFEM and may be the best first serious rescue attempt.

## 10. Best interpretation for the current repo

The present evidence suggests:

1. the project has already tested many **representation hints**,
2. it has not yet fully tested a **representation split**,
3. it has not yet fully tested **process-zone-focused adaptive sampling**,
4. it has not yet fully tested **fracture-specific discontinuity embedding**,
5. it has not yet fully tested **harder symmetry / boundary constraints** as first-class objectives.

Therefore it is too early to say the gap is exhausted.

It is more accurate to say:

**The first generation of fixes has been explored thoroughly. The second generation, which explicitly changes the approximation space around the crack tip and crack faces, has not.**

## 11. Recommended next research order

### Branch A: cheapest high-value branch

1. exact or stronger BC imposition,
2. symmetry-aware training,
3. process-zone adaptive sampling,
4. SDF-augmented inputs.

Success criterion:

1. `V4` improves materially,
2. `V7` improves materially,
3. `int_gpsi_l0`, `gpsi_top1pct`, `a_trajectory_rms_diff` improve without losing acceptable `N_f`.

### Branch B: strongest mechanism-facing branch

1. bulk-tip decomposition,
2. tip-local SIREN or multi-scale Fourier block,
3. crack-tip asymptotic enrichment functions,
4. local sampling and local loss emphasis.

Success criterion:

1. process-zone concentration rises,
2. trajectory improves,
3. symmetry and BC do not collapse,
4. improvement holds across at least one second `Umax` or seed.

### Branch C: highest-risk but most fracture-native branch

1. SDF jump embedding,
2. crack-tip enrichment channels,
3. neural XFEM/PUM ansatz.

Success criterion:

1. local field sharpness improves substantially,
2. improvement is not only `alpha_bar_max` but also `g psi` concentration and trajectory,
3. side-boundary residual remains under control.

## 12. Bottom line

The strongest lesson from the literature is not that "we need a better generic neural network." It is that fracture problems reward methods that separate:

1. smooth bulk behavior,
2. crack-face discontinuity,
3. crack-tip singular or near-singular structure,
4. local process-zone sampling and optimization.

That is exactly what XFEM/PUM did in classical numerics, and recent neural fracture papers are converging toward the same design logic.

## References

Project-local context:

1. `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/experiment_inventory.md`
2. `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/advisor_method_evolution.md`
3. `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/fem_likeness_scorecard.md`
4. `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/diagoosis.md`

Primary and near-primary external sources:

1. Tancik et al., *Fourier Features Let Networks Learn High Frequency Functions in Low Dimensional Domains* (2020), https://arxiv.org/abs/2006.10739
2. Sitzmann et al., *Implicit Neural Representations with Periodic Activation Functions* (2020), https://arxiv.org/abs/2006.09661
3. Wang, Wang, Perdikaris, *On the eigenvector bias of Fourier feature networks* (2020), https://arxiv.org/abs/2012.10047
4. Moseley et al., *FBPINNs* (2021), https://arxiv.org/abs/2107.07871
5. Moseley et al., *Multilevel domain decomposition-based architectures for PINNs* (2023), https://arxiv.org/abs/2306.05486
6. Farhani et al., *Momentum Diminishes the Effect of Spectral Bias in PINNs* (2022), https://arxiv.org/abs/2206.14862
7. Gao, Yan, Zhou, *Failure-Informed Adaptive Sampling for PINNs* (2023), https://epubs.siam.org/doi/10.1137/22M1527763
8. Sukumar and Srivastava, *Exact imposition of boundary conditions with distance functions in physics-informed deep neural networks* (2021), https://arxiv.org/abs/2104.08426
9. Zhang et al., *Enforcing continuous symmetries in PINN* (2022), https://arxiv.org/abs/2206.09299
10. Gu et al., *Interface crack analysis in 2D bounded dissimilar materials using an enriched physics-informed neural networks* (2024), https://www.sciencedirect.com/science/article/pii/S095579972400122X
11. Calafa, Jensen, Andriollo, *Solving plane crack problems via enriched holomorphic neural networks* (2025), https://www.sciencedirect.com/science/article/pii/S0013794425003340
12. Zhao and Shao, *DEDEM* (2024), https://arxiv.org/abs/2407.11346
13. Zhao and Shao, *DENNs* (2025), https://www.sciencedirect.com/science/article/abs/pii/S0045782525004566
14. Lotfalian et al., *eXtended Physics Informed Neural Network Method for Fracture Mechanics Problems* (2025), https://arxiv.org/abs/2509.13952
15. Moes, Dolbow, Belytschko, *A Finite Element Method for Crack Growth without Remeshing* (1999), https://www.researchgate.net/publication/51992357_A_Finite_Element_Method_for_Crack_Growth_without_Remeshing
16. Belytschko and Black, *Elastic crack growth in finite elements with minimal remeshing* (1999), citation trail surfaced via XFEM references: https://www.scirp.org/reference/referencespapers?referenceid=2105422
17. Moes et al., *Discontinuous enrichment in finite elements with a partition of unity method* (2001), https://www.sciencedirect.com/science/article/pii/S0168874X00000354
18. Baek, Wang, Chen, *N-Adaptive Ritz Method: A Neural Network Enriched Partition of Unity for Boundary Value Problems* (2024), https://arxiv.org/abs/2401.08544
19. Pandey and Behera, *An adaptive wavelet-based PINN for problems with localized high-magnitude source* (2026), https://arxiv.org/abs/2604.28180
