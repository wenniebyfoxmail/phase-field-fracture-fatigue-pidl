# Proposed observation-conditioned latent-temporal fracture figures

These figures translate the visual logic of Yang, Guo and Ren (2026), Figs. 1 and C.12, into a fracture-specific **proposed architecture**. They do not claim that this architecture has already been implemented or validated.

## Figure 1

**Purpose:** separate invariant context, evolving fracture state, known loading input, observation assimilation and FEM-centred validation.

**Suggested caption:**

> Proposed observation-conditioned latent-temporal fracture surrogate. Static geometry, material and boundary-condition information are encoded as a context latent, while the current fracture state and available measurements are encoded independently. A recurrent update processes the assimilated state together with the known loading increment, and FiLM conditions the temporal representation on the invariant context before graph decoding of the next-cycle mechanism fields. FEM fields enter only through aligned training and validation objectives and are not available during inference.

## Figure 2

**Purpose:** show the proposed multiscale graph latent module at implementation level while keeping unvalidated widths and pooling ratios symbolic.

**Suggested caption:**

> Proposed mechanism-preserving graph latent representation module. Evolving mesh fields and observation features are compressed through multiscale message passing into a probabilistic state latent and decoded to next-cycle mechanism fields. Dashed skip connections preserve local crack-tip and process-zone information that may otherwise be lost through aggressive compression. Dimensions are symbolic because graph coarsening ratios and latent widths remain controlled architecture variables rather than validated constants.

## Evidence boundary

- The current FEM evidence supports short-horizon state-conditioned propagation and transition-state reset recovery.
- It does not yet support autonomous generation of the c87 transition.
- The figures therefore distinguish observed inputs, known controls and FEM-only supervision explicitly.
- A deterministic graph autoencoder should remain the control when testing whether a probabilistic latent is useful.

## Files

- `fig01_proposed_observation_conditioned_latent_temporal_framework.{png,pdf,svg}`
- `fig02_proposed_graph_latent_representation_configuration.{png,pdf,svg}`
- `draw_proposed_framework.py`

## Reproduction

Run with the project Mac Python containing Matplotlib:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 draw_proposed_framework.py
```
