# S04-E014 R002 stratified-sampling screen result

Status: completed; independent `EVIDENCE PASS`; no rerun required

## Purpose

Test whether the smallest measured intervention, unbiased damage-stratified
sampling, fixes the S04-E013 supervised displacement failure at one early state
and one transition state without changing architecture, full-field objective,
optimizer or 10,000-step budget.

## Execution and admission

- producer: Taobo `GPUServer8`, GPU 0, sequential execution;
- reviewed code: `0ff6154072fd90dd6889231343ec12ef7b50c592`;
- Run root: `S04-E014-stratified-screen-0ff6154-20261011T223826Z`;
- units: `c20s4 seed7`, `c83s4 seed7`;
- both runs: `COMPLETED`, exact reference identity unchanged, step 10000,
  final LR `1e-5`, verified archive copy;
- aggregation: 2/2 valid, no missing rows, no integrity error;
- local reaggregation of the retrieved package is byte-identical to the Taobo
  metrics CSV and summary JSON.

## Result

| State | S04-E013 baseline | Stratified result | Improvement | Displacement gate | Strain | rho_u |
|---|---:|---:|---:|---|---:|---:|
| c20s4 | 0.00488847 | 0.00321176 | 34.30% | fail | 0.153324 | 51.5514 |
| c83s4 | 0.00532068 | 0.00343512 | 35.44% | fail | 0.109954 | 63.9573 |

BC error is exactly zero in both runs. Neither displacement result reaches the
absolute `1e-3` gate. Neither improvement reaches the preregistered 50% trigger
for deterministic full-field polish. Strain and rho_u remain secondary failures.

The frozen automatic verdict is:

```text
SAMPLING_ONLY_REPAIR_REJECTED
```

## Interpretation and solution route

The experiment rejects sampling-only repair, rather than sampling as a useful
ingredient. Oversampling the damage zone reduces final displacement error by
about one third in both early and transition states. The fixed monitoring trace
also shows large nonmonotonic excursions and, at c83 step 6000, a temporary
transfer of error into the background. Thus the shared global network still
struggles to represent and optimize the sharply localized correction while
preserving the smooth background.

The next bounded solution should test a local/multiscale representation with an
explicit smooth global branch and a damage-local branch, trained against the
same full-field objective and compared at c20/c83 before any wider matrix. This
targets the remaining spatial-scale conflict while retaining the demonstrated
benefit of damage-aware allocation. A larger seed sweep, longer budget or
full-field polish is not justified by this gate.

This screen does not resolve theoretical architecture representability and does
not authorize the 12-run validation, Stage 2, FEM reproduction or teacher
qualification.
