# S04-E036 independent mechanism endpoints

`run_mechanism_matrix.py` implements the prospective four-state design in the
owner case `gap_attribution_20261022/analysis/first_principles_design.md`.
It is separate from the D3 window runner. This document describes prepared code,
not an execution receipt or a numerical result. Do not run its CLI on Mac.

Three separately authorized phases are available:

```text
python tools/s04_e036/run_mechanism_matrix.py --manifest mechanism_inputs.json \
  --authority phase_authority.json --out NEW_OUTPUT --device cuda:0 --phase matrix

python tools/s04_e036/run_mechanism_matrix.py --manifest mechanism_inputs.json \
  --authority fit_authority.json --out NEW_FIT_OUTPUT --device cuda:0 \
  --phase target_fit --targets mechanism_targets.json

python tools/s04_e036/run_mechanism_matrix.py --manifest mechanism_inputs.json \
  --authority continuation_authority.json --out NEW_CONTINUATION_OUTPUT --device cuda:0 \
  --phase candidate_continuation --source-endpoints C0_sources.json
```

Every phase requires a finite positive `job_wall_seconds`, an external owned
watchdog using that value, a fresh output directory, matching production source
lock, and completed Stage A semantic reuse. There is no cumulative resource cap
in this prospective program. A per-job timeout is an interruption, not evidence
of a representation limit. No phase automatically retries a failure.

Optional `--case c1s2|c1s4|c83s2|c83s4` partitions execution across independent
owned GPU jobs. The manifest still names all four states; authority must bind
`requested_case` exactly (`null` means all four). Attempt/finished receipts
record declared and executed cases. A one-state job never labels itself a
complete four-state program. All four predetermined results, including failures,
must be gathered before an overall interpretation; no outcome-driven partition
selection is authorized by this interface.

The existing execution authority schema additionally requires
`mechanism_phase`, `requested_case`, `job_wall_seconds` equal to the manifest,
and `cumulative_resource_limit:null`. Fit binds `target_manifest:{path,sha256}`;
continuation binds `source_endpoints:{path,sha256}`. The production lock must
also include this runner, mechanism_metrics, native_q4_diagnostics, scorer and
tri3_quadrature dependencies. This is independent of Stage A operator reuse.

## Physical inputs and precision

The physics manifest has **exactly** these keys:

```json
{
  "schema": "s04_e036_mechanism_inputs_v1",
  "trajectory": "explicit native trajectory identity",
  "mesh": {"path": "mesh.npz", "sha256": "..."},
  "common_problem": {"path": "common_problem_q4.json", "sha256": "..."},
  "cases": {
    "c1s2": {"state_key": {}, "predecessor": {}, "admission": {}, "network": {}},
    "c1s4": {"state_key": {}, "predecessor": {}, "admission": {}, "network": {}},
    "c83s2": {"state_key": {}, "predecessor": {}, "admission": {}, "network": {}},
    "c83s4": {"state_key": {}, "predecessor": {}, "admission": {}, "network": {}}
  },
  "solver": "copy the exact SOLVER object from the reviewed runner",
  "job_wall_seconds": "explicit finite positive number, agreed by owner"
}
```

The illustrative strings above are not runnable defaults. Each `{}` file
reference is exactly `{path,sha256}`. `state_key` uses `window_inputs.state_key`.
`solver` is an object, exactly the reviewed `SOLVER` constant, including a null
`cumulative_resource_limit`. No future target reference is permitted in this
manifest. The four network hashes are fixed in `NETWORK_SHA`: canonical
model1/model3/model411/model413, chosen before these outcomes. There is no
fallback network or state selection.

Each predecessor is the **F1** s1 or s3 native checkpoint. FEM-B exports its
`as_predecessors["c1/s1"|"c1/s3"|"c83/s1"|"c83/s3"]` sidecars without another
solve. It uses the predecessor admission schema and float64 arrays `u,v,damage,
history,active_driver,f_commit`, physical key, native checkpoint SHA and ordered
mesh identity. The runner verifies concrete source/residual/readback evidence,
saved physical support, bounds, load and fatigue consistency before using it.

All four physical arms retain original native float64 old d/A/r. The initial
parameters and neural coordinate evaluation are float32. **All** neural nodal
outputs are promoted to float64 before energy, driver, quadrature or acceptance;
the common native float64 geometry is used for every arm. Clamp is applied to
this double nodal damage and the exact native lower bound. This avoids mixing
an operator dtype change into the mapping comparison or rounding a lower bound
down across the healing tolerance. It is a new D4 arithmetic contract, not a
claim to reproduce D3's previous float32 arithmetic byte for byte. A subsequent
float64 branch changes the whole NN evaluation as well and is labeled separately.

## Matrix and continuation

The four arms are Lplus `(legacy,1e-5)`, L0 `(legacy,0)`, Cplus
`(nodal_clamp,1e-5)` and C0 `(nodal_clamp,0)`. Each copies the same canonical
theta0 for its state and uses the same original F1 predecessor. The matrix
always records 2000 RPROP updates, in ten blocks of 200 with optimizer resets,
including an arm that already passes acceptance earlier. Fatigue is fixed and
detached inside a block, rebuilt from the same old state afterward. Every arm
has history commit count zero. Nonfinite/log-domain failure preserves the
failed arm; persistence, implementation and infrastructure failures stop the job.

Clamp uses ordinary min/max derivatives, with an explicit constant/zero
derivative at collapsed `old_d==1` boxes. It changes the composite function
family. Payloads report that fact and the initial nodal projection J/counts.

The C0 continuation manifest is exactly
`{schema:"s04_e036_C0_continuation_v1",physics_manifest:{path,sha256},cases:{...}}`.
Each of its four case entries is `{completion:{path,sha256},bundle:{path,sha256}}`
for that case's C0 `first_2000` endpoint. No target is accepted by this phase.
It replays weights/mapping and verifies exact old state, source manifest,
theta0 and actual prefix work before proceeding. It stops normally at fresh
acceptance; otherwise RPROP continues until ten complete blocks improve the
best C by less than 1%, or an entire block leaves outputs identical. The one
predeclared float64 L-BFGS continuation then begins from that saved state.
This is a precision-plus-solver change, not an isolated precision experiment.

L-BFGS retains one optimizer's curvature across steps of the same fixed f.
It refreshes f after at most 200 steps or inner stagnation and discards curvature
when f actually changes. Per-step closure evaluation is hard-capped at 25;
an exception restores the exact pre-step parameters and does not increment the
accepted-step count. Twenty steps changing fixed-f energy by at most 1e-10,
with f fixed and acceptance still failing, stop as numerical stagnation.
An optimizer step here means an accepted `LBFGS.step` call, not a RPROP update;
closures and updates are separately recorded.

## Seen-target witness

The separate fit manifest is exactly
`{schema:"s04_e036_mechanism_targets_v1",physics_manifest:{path,sha256},targets:{...}}`.
Its four targets use the scorer's `{snapshot,admission}` references. The native
solver policy must be the admitted ordinary F1 policy (u1e-6/joint4e-4), with
exact same native old state. A stricter or easier reference is not substituted.
The authority separately binds the fit manifest. Physics matrix/continuation
never opens it.

The witness uses the original legacy mapping, all 1125211 network parameters,
float64 evaluation, zero L2 and continuous L-BFGS on `Q²=J²+G²`. J uses nodal
lumped area and scales .12/.12/1; G uses native Q4 gradients with ell=.01.
No neural-coordinate AD gradient, output table, graph or projection is added.
Q<=1e-3 and max damage error<=.01 are **program stopping points** only. A
stagnation of twenty steps with relative Q² change<=1e-8 stops without an
expression-limit claim. Actual J/G/per-channel/max errors are retained.

At a witness readout, f is rebuilt from the witness fields and unchanged old
state solely for zero-update physical inspection; it is not called a coefficient
used by the fitting optimizer. Bounds and fresh residual acceptance are reported
independently of fit success. The code exposes `release_contract(...)` for a
conditional teacher-initialized legacy/C0 release request. It does **not**
automatically execute that branch or mix it with physics-only theta0 results.
The request needs a subsequent implementation/review and bound phase authority.

## Saved state and FEM oracle interface

Every snapshot includes weights, actual/raw fields, exact native old state,
trial history, actual frozen f and fresh f, mapping/precision, actual work,
physical residual and acceptance. Initial/final snapshots additionally keep
full physical/L2/total parameter vectors and geometry summaries, native forces,
KKT and clipped-direction indices, scalar/GP/reaction readouts and zero-update
float64 realization comparison. Intermediate blocks do not repeat the three
million-entry parameter vectors. First plateau/f-fixed snapshots are retained.

Files are written in a newly created directory, read back, and used to rebuild
the actual mapping/network. Exact field/history/coefficient reproduction and
fresh acceptance identity are required before `completion.json` is published.
Completion labels a complete diagnostic; `physical_accepted` may be false.
An unaccepted diagnostic is never a committed predecessor.

The FEM oracle source is
`<matrix_output>/<case>/Lplus/first_2000/fields.npz` plus its `completion.json`.
Bind both hashes. NPZ arrays `u,v,d,raw_damage` are double actual fields;
`old_damage,old_history,old_active_driver` are retained for audit, but the native
oracle must load its old state independently from the F1 predecessor. Metadata
has schema `s04_e036_mechanism_fields_v1`, arm Lplus, stage first_2000,
rprop_updates2000, exact state/predecessor SHA, network SHA, mapping and dtype.
The oracle consumes only candidate u/v/d, then explicitly projects common
BC/box and records that projection. Missing/incomplete Lplus is unavailable,
not replaced by a different arm.

## Validation and review boundary

`tests/test_e036_mechanism_runner.py` uses artificial Q4 arrays, metadata,
plain-tensor mapping algebra and fake optimizer/persistence objects. It never
constructs or evaluates the project NN and never runs a scientific optimizer.
The producer run, native target qualification, GPU resources and true NN
readback remain unexecuted by these tests. The independent reviewer should
focus on source/target isolation, mixed arithmetic, old-state immutability,
equal prefix work, fixed-f curvature lifetime and completion-last semantics.
