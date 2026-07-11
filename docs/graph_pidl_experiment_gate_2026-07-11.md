# Graph-PIDL Experiment Gate

- Mechanism question: under the unchanged eta=0 hard-recovery physics, does explicit FE-mesh neighbourhood aggregation improve mechanism recovery relative to the coordinate MLP?
- Claim changed if success: representation is an independent contributor if Graph-PIDL improves FEM-referenced event and process-zone metrics without FEM field supervision.
- Claim changed if failure: mesh message passing alone does not resolve the mismatch under the current constitutive pathway.
- Cheaper diagnostic first: the completed supervised residual discriminator found neighbourhood structure, but cannot answer whether PIDL itself improves. A producer-side training-path smoke is required before a trajectory.
- Minimal output asset: smoke decision note first; trajectory decision table and raw/degradation/active-driver figure only after smoke passes.
- Code/producer alignment: opt-in code developed on Mac; any optimization-loop execution runs on Taobo. Existing MLP runners are unchanged unless `--graph-pidl` is passed.
- Success criteria: graph binding on coarse and fine meshes; finite forward/backward loss; checkpoint reload; no FEM target access; trajectory evaluation against aligned FEM using event timing and mechanism fields.
- Failure criteria: graph/input ordering mismatch, non-finite gradients, checkpoint failure, prohibitive memory, or apparent gain limited to event timing/global averages.
- Registry destination: `docs/pidl_experiment_inventory.md`; promote to aligned registry only after mechanism-level review.
- Decision: launch Taobo smoke, then decide on one eta=0 trajectory. The eta=1e-4 residual-stiffness run remains an independent constitutive branch.

## Controls

- FEM remains the validation reference but supplies no training labels.
- Legacy c69 is excluded from training, validation, and final comparison.
- The first Graph-PIDL case uses residual stiffness eta=0.
- The graph uses actual triangular FE node connectivity and is rebound when PIDL switches from coarse to fine mesh.
- Boundary ansatz, numerical FE gradients, variational energy, fatigue history, degradation law, and fracture criterion remain unchanged.
