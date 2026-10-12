# Stage 0A synthetic P0 Code Ready request

Return exactly `CODE_READY`, `REVISE_AND_REREVIEW` or `REDIRECT` first.

Review only the frozen synthetic P0 implementation:

- `source/s09_stage0a_transition.py`
- `SENS_tensile/run_s09_stage0a_p0.py`
- `tests/test_s09_stage0a_transition.py`
- `configs/s09_e008_stage0a_p0.json`

Check that:

1. the callable input contains only causal pre-cycle nodal damage, native-GP
   history, frozen geometry and the prescribed s00--s05 load path;
2. node-to-GP and GP-to-node messages preserve native Q4 support and weights;
3. zero raw heads preserve qualified `d/H/alpha/q/f`, displacement boundaries
   are hard, and projected damage/alpha/Carrara constraints are correct;
4. raw-increment supervision retains corrective gradients behind projections;
5. nodal-state, GP-history and equilibrium objectives remain separate, while
   `fixed_judgement_loss` contains no adaptive training weight;
6. the runner cannot accept a scientific packet, perform optimiser updates,
   authorise training or imply Stage 0B rollout;
7. tests are sufficient for a synthetic wiring gate and do not promote P0 to
   data capability or scientific validity.

Exact producer state sufficiency remains blocked on Windows-FEM Request 32.
Code Ready must not authorise scientific-array decode or training.
