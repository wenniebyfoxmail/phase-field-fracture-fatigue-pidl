# Yang, Guo and Ren (2026): latent-temporal surrogate

## Bibliographic record

- **Paper:** Yu-Sen Yang, Ling Guo and Xiaodan Ren, "Generalizable latent-temporal learning for path-dependent nonlinear mechanical responses across heterogeneous microstructures"
- **Journal:** *Computer Methods in Applied Mechanics and Engineering*, 461 (2026), 119166
- **DOI:** [10.1016/j.cma.2026.119166](https://doi.org/10.1016/j.cma.2026.119166)
- **Local PDF:** `upload code/references/Yang_Guo_Ren_2026_CMAME_LatentTemporal_HeterogeneousMicrostructures.pdf`
- **PDF SHA-256:** `08d5fcaf6baf86408b92f31c28f9730b92981736bb2b7c1ccc81c2c458a8af41`
- **Read on:** 2026-07-20

## One-sentence verdict

The paper is a strong reference for separating fixed morphology encoding from loading-history dynamics and coupling them through FiLM, but it is **not** evidence that latent temporal models can autonomously predict an unseen fracture-regime transition or recover local fracture fields.

## What the paper actually solves

The supervised mapping is

\[
(\text{static microstructure image},\ \text{prescribed strain path})
\longrightarrow
(\text{homogenized stress history},\ \text{plastic-energy history}).
\]

At time step \(t\), the current strain \(\varepsilon_t\) is supplied to the temporal model. The task is therefore a **causal, loading-conditioned constitutive surrogate**, not an autonomous future forecast from an earlier observed state.

This distinction is central for comparison with our c87/c89 study. Their out-of-distribution loading-path experiment still provides the new loading path as input. It does not ask the network to infer a future loading change or an unobserved transition trigger.

## Architecture

1. A convolutional VAE maps a static \(128\times128\) two-phase microstructure image \(x\) to a probabilistic morphology latent \(z\).
2. A GRU maps the prescribed strain sequence to hidden temporal states \(h_t\).
3. FiLM uses the VAE mean vector \(\mu\) to generate feature-wise scale and shift terms for \(h_t\).
4. A final head predicts the three homogenized stress components and plastic-energy dissipation.

The core coupling is

\[
\mathrm{FiLM}(\mu,h_t)
=
(1+\gamma(\mu))\odot(W_hh_t)+\beta(\mu).
\]

This is more structured than simply concatenating morphology and temporal features: the fixed morphology explicitly conditions how the temporal representation is interpreted.

Baseline configuration:

- VAE latent dimension: \(d_z=128\);
- GRU hidden dimension: \(d_h=512\);
- batch size: 512;
- Adam learning rate: \(10^{-3}\);
- 2000 epochs;
- both separate VAE-then-temporal training and joint end-to-end training were tested.

## Dataset and validation design

- Two circular-inclusion microstructure categories provide 20,000 in-distribution supervised samples.
- Static images are standardized to \(128\times128\) pixels.
- Loading paths independently vary \(\varepsilon_{11}\), \(\varepsilon_{22}\), and \(\varepsilon_{12}\) through interpolated random control points.
- FEM supplies time-resolved homogenized stresses and plastic-energy dissipation.
- OOD1 tests random-inclusion morphologies absent from training.
- OOD2 tests prescribed strain paths absent from training.

The paper therefore earns its generalization claim through variation over **many morphology-loading pairs**, not through a single trajectory split into many windows.

## Main quantitative findings

For the separate-training baseline with \(d_z=128\) and batch size 512:

| Test set | Stress MSE |
|---|---:|
| In-distribution validation | \(8.156\times10^{-5}\) |
| OOD1: unseen morphology | \(1.167\times10^{-3}\) |
| OOD2: unseen loading path | \(9.795\times10^{-3}\) |

The loading-path shift is much harder than the morphology shift. The authors interpret loading history as governing the global stress evolution, while morphology supplies more localized adjustments.

Latent capacity matters up to a point: increasing \(d_z\) from 8 or 16 to 32 improves prediction, while differences among 32, 64 and 128 are generally not significant. This argues against either extreme compression or an automatic "larger latent is better" claim.

The morphology ablation sets the latent-conditioned FiLM coefficients to zero. Error increases in every evaluated dataset, supporting the claim that the morphology latent contributes information beyond loading history.

### GRU versus Transformer

Under a shared pretrained VAE, matched data split and approximately matched parameter budget:

| Temporal module | Validation MSE | OOD1 MSE | OOD2 MSE |
|---|---:|---:|---:|
| GRU | \(8.156\times10^{-5}\) | \(1.167\times10^{-3}\) | \(9.795\times10^{-3}\) |
| Best listed Transformer by OOD2 | \(2.369\times10^{-4}\) | \(1.102\times10^{-3}\) | \(2.615\times10^{-1}\) |

The causal Transformer fits the familiar distribution reasonably but is about 27 times worse than the GRU on unseen loading paths. This independently supports our current result that adding a more elaborate temporal block does not guarantee better path-dependent generalization.

### Transfer and cost

- Transfer to a different phase-constitutive combination reduces training from 2000 to 500 epochs while retaining broadly comparable accuracy.
- Reported online speedups over FEM range from \(1.73\times10^4\) to \(5.54\times10^4\), after about five hours of offline VAE and temporal training on an NVIDIA A800.

## Explicit limitations in the paper

The authors state that:

- accuracy decreases under strong OOD shifts;
- a new constitutive setting still requires data and retraining;
- only macroscopic responses are predicted;
- microstructural field distributions are not resolved;
- experimental microstructures and uncertainty quantification remain future work;
- deployment in implicit FEM requires strain-increment self-consistency and a reliable tangent operator.

These limitations prevent direct promotion of the method to our hidden fracture-field or digital-twin problem.

## Relationship to our current evidence

| Question | Yang et al. | Our fracture problem |
|---|---|---|
| Static spatial condition | Two-phase morphology image | Geometry, notch, mesh, material and BC descriptors |
| Temporal input | Known strain value at every step | Observed state plus known loading/cycle increment |
| Output | Homogenized stress and plastic energy | Damage, history, raw driver, degradation and active-driver fields |
| Forecast type | Loading-conditioned sequence response | Observed-state h1-h3 propagation and autonomous transition forecast |
| Generalization evidence | Many morphology-loading pairs | Currently one complete legal FEM trajectory |
| Transition test | Not isolated | c87 regime transition is the decisive failure |

The paper does **not** contradict our multi-origin result:

> Graph-temporal models can propagate a supplied state over short horizons, but temporal memory alone cannot generate a transition whose identifying information is absent from the inputs and training trajectories.

It actually sharpens the explanation. Yang et al. obtain generalization by giving the model both the morphology and the full causal loading signal across a diverse joint dataset. Our current c87 failure is primarily an observability and trajectory-diversity problem, not evidence that the temporal block is too small.

## Useful design ideas for our next model

### 1. Separate invariant context from evolving state

Use distinct encoders:

\[
z_g=E_g(\text{geometry, notch, material map, BC type}),
\]

\[
z_t=E_s(\alpha_t,\bar\alpha_t,\psi_{\rm raw,t},\text{observations}_t).
\]

The temporal update should receive the known load increment and the current observed/assimilated state:

\[
h_{t+1}=T(h_t,z_t,\Delta u_t),
\qquad
\widehat z_{t+1}=\mathrm{FiLM}(z_g,h_{t+1}).
\]

The graph decoder can then reconstruct mechanism fields. Static geometry should condition dynamics; it should not be confused with the evolving fracture state.

### 2. Test FiLM, not another broad temporal sweep

A clean matched experiment is:

1. Markov graph baseline;
2. GRU with concatenated context;
3. GRU with FiLM-conditioned geometry/state latent;
4. causal Transformer with the same encoder and FiLM block.

Hold parameter budget, supervision, origins and seeds constant. This tests whether structured conditioning helps, rather than repeating a generic architecture contest.

### 3. Preserve process-zone information in the latent

VAE image reconstruction loss is insufficient for us. A latent can reconstruct most of the domain while discarding the small active process zone. Any compression objective must include mechanism-aware terms for:

- active-driver log residual;
- FEM-p99 absolute support;
- own-p99 localization;
- support-area ratio;
- process-zone centroid and width;
- damage/history residuals;
- neighbour-jump or high-frequency artefacts.

A deterministic graph autoencoder is the safer first control. A probabilistic VAE should only be promoted if calibrated uncertainty or generative use adds measurable value.

### 4. Build diversity along transition-relevant axes

The next dataset should vary at least one causal axis beyond cycle index:

- loading amplitude or path;
- notch/crack geometry;
- material or fatigue parameters;
- boundary-condition pattern;
- pre-transition hidden energetic state;
- sparse observations around the transition.

Randomly splitting windows from the same c1-c89 trajectory cannot support a generalization claim comparable to this paper.

### 5. Link to realistic observations

The paper briefly motivates CT plus controlled mechanical tests. For our digital-twin direction, the analogous inputs are:

- geometry/crack mask from imaging;
- DIC or sparse displacement measurements;
- reaction force/global stiffness;
- repeated temporal observations;
- sparse raw-energy or strain probes near the predicted process zone.

Our existing inverse-state result already shows that transition-sensitive energetic probes carry information that geometry and reaction force alone do not. These observations should enter the state encoder before the FiLM-conditioned temporal update.

## Recommended claim and non-claim

**Defensible claim:**

> Yang et al. demonstrate that morphology-aware latent conditioning can be coupled with recurrent loading-history encoding to generalize nonlinear constitutive response prediction across diverse microstructures and prescribed loading paths. Their results also show that incremental recurrent structure can outperform parameter-matched causal Transformers under loading-path shift.

**Do not claim:**

> Their method predicts unseen fracture transitions, recovers local crack fields, solves inverse state identification, or demonstrates generalization from a single trajectory.

## Decision for our project

Classify this paper as a **high-value architecture and dataset-design reference**, not a directly comparable fracture benchmark.

The immediate lesson is:

\[
\boxed{
\text{diverse conditional data}
+
\text{structured context-state coupling}
>
\text{another temporal architecture sweep}
}
\]

The next justified experiment is a FEM-referenced, multi-trajectory, FiLM-conditioned graph-GRU evaluated separately on same-regime h1-h3 propagation, autonomous transition generation and post-observation-reset propagation.
