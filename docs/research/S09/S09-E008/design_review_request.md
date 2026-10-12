# S09-E008 Design Ready review request

Review `experiment.md` and `state_capability_audit.md` as a relaxed Stage-0
prototype design. Return exactly `DESIGN_READY`, `REVISE_AND_REREVIEW`, or
`REDIRECT` first.

Check especially:

1. whether Stage 0A/0B removes same-cycle leakage and makes rollout closure
   honest;
2. whether the mixed nodal/GP support is minimal and FEM-consistent;
3. whether the physics ladder uses the actual exported state without claiming
   a full phase-field PINO prematurely;
4. whether gradient-balanced multi-objective training follows the E005/E006
   evidence without turning diagnostics into model-selection votes;
5. whether P0/P1 are relaxed enough to run the architecture but still reject
   zero-growth and false-growth shortcuts;
6. whether the complete-trajectory split and sealed-confirmation requirement
   are adequate.

A pass authorises a bounded data-capability audit and code design. It does not
authorise scientific-array unsealing, training or a scientific result.
