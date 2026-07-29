# FEM multi-trajectory contract decision

Date: 2026-07-29

## Verdict

**Two different readiness gates now have different outcomes.**

- Road-like leave-one-independent-trajectory-out: **BLOCKED_BY_DATA**. Zero independently varied road-like trajectories are currently ingested; the three producer handoffs remain pending. No road-generalization training is allowed.
- Shared-geometry Hard5 2x2 leave-one-combination-out: **READY**. The hard/soft initial-tip state x retained-5/explicit-8 loading-history cells may support a scoped numerical LOCO experiment after 4/4 bundle validation.

No model training was run by this task. The factorial result is not four independent roads, material generalization, or geometry generalization. It tests only whether a model can hold out one controlled combination while geometry, mesh, material, Umax=0.12, eta=0, and the event rule remain shared.

## Libraries and exclusions

The Umax 0.11/0.12/0.13 set passed 3/3 validation, but remains one load-amplitude sensitivity library. Its Umax=0.12 hard/5-step member duplicates the corresponding factorial configuration and cannot be counted again in a train/test split. The old reverse-BC c69 package remains rejected by provenance identity, while a genuinely new trajectory is not rejected merely because its event happens at cycle 69.

## Contract gates

Each accepted trajectory carries cycle-peak semantics, explicit substep-to-raw-step mapping, distinct first-hit and confirmed roles, immutable state/provenance hashes, mesh identity, and damage, alpha_bar, fatigue degradation, raw driver, derived damage degradation, and derived active driver. Crack-image and strain-localization channels are synthetic FEM proxies; FWD is unavailable, so none may be relabelled as real road measurement.

Both split locks use complete trajectories. Node, cycle, and cross-window leakage are forbidden. Mixed 5/8-step states are allowed only as explicitly conditioned separate factorial trajectories, never silently merged under one loading protocol.
