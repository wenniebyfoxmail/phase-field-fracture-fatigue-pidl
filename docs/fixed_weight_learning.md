# Fixed-weight conditional fields and state transitions

Owner: `fixed-weight-learning` implementation infrastructure, 2026-10-21.
Branch: `codex/fixed-weight-learning-20261021`; explicit remote base:
`origin/codex/s09-e007-fixed-damage-holdout-20261012` at
`d61076b61fd92bf09d330c902abe9a1a6e77a79d`.

## Current decision — 2026-10-23 evidence inventory

Mode: C1 read-only evidence inventory and minimal completion design, requested
by the user; no training, FEM production, protected-target access or benchmark
replay. [The current gap report](fixed_weight_reference_gaps_20261023.md)
identifies the existing sealed U0.1175 v10 candidate and older full-native
U0.11/.12/.13 packages. U0.1175 independence remains conditional on same-condition
partial access and the original protected-use policy; no new test admission is
asserted. Reuse the completed v5 capture check and current interface results;
accepted-state numerical convergence and independent physical validation remain
separate missing evidence. The report gives a zero-new-trajectory reuse path
and the conditional one-new-condition fallback. This inventory is complete;
its proposed computations and training remain unstarted.

## Active decision — 2026-10-24 evidence-completion execution

The user has changed this work from the completed C1 inventory to **C1
scientific validation**: execute the zero-new-trajectory evidence-completion
path before considering a new FEM condition.  The active D2 is recorded in
[the execution record](fixed_weight_evidence_completion_20261024.md).  It has
three bounded parts: trace the U0.1175 partial-access boundary and freeze a
prospective test-admission protocol; bind the already exposed U0.11/U0.12/U0.13
native archives to the source-aware interface; and analyse the retained
development evidence for the declared numerical-reference scope.

This change authorises no training, replay of the historical benchmark,
protected-target decoding, U0.1175 scoring, or change to the existing
development manifest.  The frozen independence decision ruled U0.1175 out as
a strict test and the compatible-archive search found no U0.1225/U0.1275
candidate by name.  One predeclared U0.1225 trajectory is therefore the
conditional fallback, using the isolated overlay recorded in the execution
record. For a strict independent-test role it may launch only under a named,
non-development custodian with a separately named scorer, protected ACL roots,
and pre-result no-observation evidence, after the immutable bundle is
independently reviewed. The current shared MATLAB process also blocks any
producer launch.

## Prior handoff — 2026-10-22 fixed-benchmark rule

The native-archive adaptation task is complete and delivered; there is no active
execution card or pending benchmark. Reuse the completed result linked at the
end of this document. The commands and reviews below are historical evidence,
not a checklist to repeat after commits, metadata edits or handoffs.

For subsequently authorized work, use the installed research-decision-core
section “只跑固定基准，通过即交付”: one existing task benchmark, deliver on pass,
and repair/rerun only failed items. Do not automatically append full regression,
historical reruns, smoke ladders, per-commit review or metadata review. Documentation
and metadata edits receive direct consistency checks only. No new benchmark or
execution authority is created by this handoff update; the scientific comparison,
budgets and protected-data boundaries below are unchanged.

The completed admission review remains on record because the user explicitly
requested this instance: “完成验证和独立复核后，确认两条完整轨迹能否准入。”
That request does not create a standing review requirement for future edits.

**Purpose:** prepare shared-weight models that can evaluate new prescribed
conditions or continue an accepted numerical state without optimizing their
weights at every load step. **This delivery:** code, configurations and small
synthetic tests. **Conclusion:** implementation capability only; no trained
checkpoint, scientific accuracy, speedup or qualified new data are claimed.

## Scope and source audit

The original FYR neural solver remains intact. The meeting QA Q14/Q16
(`FYR/meeting/FYR_meeting_QA_20261020.md:210–246`) and frozen chapter
(`FYR/meeting/sources/fyr_f0675a5_Chapter3.tex:609–640`) describe coordinate
inputs with a displacement boundary ansatz. At frozen child-repo commit
`e9dc2632457f5f566db95c75b856ad96170fd0e6`,
`source/model_train.py:1431–1432,1710–1726` constructs an optimizer inside the
load-step loop. The network object survives: its weights warm-start the next
solve, but that is not cross-condition fixed-weight inference.

The frozen PIDL histories are external to that neural input:
`hist_alpha` is maximum nodal damage, `hist_fat` accumulated fatigue, and
`psi_plus_prev` the next update's driver baseline. The explicit-substep and
peak-only branches use different driver resets (`model_train.py:2214–2222`).
FEM `H` is not PIDL `hist_alpha`. No FYR results or manuscript files were changed.

D1 reuse decision: **continue existing numerical-surrogate components**, with
a separate narrow API. Reused:

- `source/fem_mechanism_operator.py::PointwiseResidualOperator` for MLPs;
- `source/s09_q4_quadrature.py` for native Q4 support;
- `source/s09_stage0a_transition.py` for nodal/GP transfers and Carrara factor;
- `source/s09_fem_physics.py` for optional AMOR/AT1 consistency diagnostics.

The existing transition-aware GNO represents peak fields and categorical
hard/soft + 5/8-step families, not arbitrary substep actions. S09 Stage0A
represents s00→s04; its exporter and qualification are not automatically an
unload/reload rollout interface. The S09-E008 source-state audit identifies
current `H`, accumulated `alpha_bar`, and committed `q_prev`; its P1 fit was
negative. These outcomes remain unchanged. FNO/CA-FNO/GNO/PINO naming does not
remove a missing state or unqualified trajectory. No large new operator stack
was added and no scientific archive was opened for this task.

## Implemented routes

| Route | Learned map | Inference |
|---|---|---|
| A, `conditional` | Position + material + known load pair/increment + complete origin field → absolute displacement, damage and history candidates | One forward evaluation for a resolved substep |
| B, `transition` | Same complete committed state and action → field increments | Add increments, then pass predicted state to the next step |

Both use one shared parameter set across training conditions. A branch MLP
receives the entire native origin field, and pointwise decoders receive local
fields, material constants, positions, prescribed loads and that context.
There is no cycle/event-distance input. Both routes are conditioned on a
current state; A does not claim a memoryless material/load-to-solution map.
To query after several increments, use the full resolved sequence through
`FrozenPredictor.rollout`; do not replace it by cycle number or net load change.

This minimal baseline is **bound to one mesh, ordering, geometry and scalar
tensile boundary family**. Complete field input addresses the omission of
nonlocal context, but a learned finite context vector is not a proof of state
sufficiency. The dense branch scales with node/GP count; choose a small already
qualified mesh for a first study. Cross-geometry transfer, arbitrary boundary
conditions and general loading histories remain unsupported. Existing mesh
GNO components can replace the branch after a data/accuracy study justifies it.

The displacement ansatz fixes horizontal and vertical values at the specimen
bottom/top. Projection imposes damage irreversibility/bounds and nonnegative
history, with `alpha_bar` nondecreasing. It does **not** force `H` or `q_prev`
monotone. Both raw and projected candidates are retained. The training loss
includes raw candidates to avoid hiding errors or eliminating all gradients
at a clipped increment. These constraints do not enforce equilibrium.

## Contract and data admission

`fixed_weight_contract.py` supports `explicit_substep_post_commit_v1`:

| Quantity | Support | Meaning |
|---|---|---|
| `u` | nodes × 2 | committed displacement |
| `d`, `d_lower` | nodes | committed damage and next-step bound; equal in this strict no-healing post-commit contract |
| `history[...,0]` | elements × 4 native GP | `H`, current undegraded tensile energy for this convention; not maximum damage |
| `history[...,1]` | same GP | accumulated `alpha_bar` |
| `history[...,2]` | same GP | committed `q_prev`, allowed to fall during unloading |
| `State.fatigue(material)` | same GP | derived Carrara factor; not an independent target |

Material explicitly supplies E, nu, Gc, ell, fatigue threshold/power, residual
stiffness and thickness. State keys preserve trajectory, parameter condition,
FEM reference identity, mesh, cycle, substep, ordinal, branch, actual prescribed
load and post-history-commit timing. The adapter explicitly requires the
`clamped_tensile_y` boundary family and checks its displacement values. It
rejects stale `d_lower` rather than silently mixing pre/post-update history.
Keeping the two named fields does not make them independent for this producer;
FYR finite-penalty history requires its own adapter. Each request advances one ordinal and
checks the increment against endpoint loads. The source adapter must ensure
that a resolved step has no omitted reversal; endpoints cannot prove that.
Initialization aliases need explicit source mapping before this API; the old
S09 s00 alias must not be treated as a second physical increment.

`SplitManifest` groups whole trajectories and **whole parameter conditions**
(including seeds) into train/validation/test. It rejects cross-split conditions.
No random nodes, overlapping windows or adjacent-frame split is provided.
Protected records are denied before loader invocation. The adapter uses an
explicit callback returning decoded states, requires a qualification pointer,
material identity, exact total state count and gap-free coverage, and verifies
native support. The qualification pointer is the caller's assertion, not a
substitute for source review. There is no auto-glob, NPZ/HDF5 archive discovery,
old-PIDL fallback, or implicit permission to open a test set.

`adapt_decoded_stage0a` connects an already decoded native
`s09_stage0a_packet.DecodedStage0AState` to this contract without opening files.
The caller must declare source semantics and post-commit timing. The adapter
checks physical cycle/substep, native source key (rejecting aliases), prescribed
load, channel shape and the redundant Carrara `f` before retaining `[H,A,q]`.
It derives the next damage bound from committed damage only under this declared
strict FEM convention. Existing s00 pre-cycle records and FYR histories are
not silently converted.

The [2026-10-22 remote audit](fixed_weight_data_audit_20261022.md) verified all
882 physical native Hard5 states in the U0.115 and U0.125 archives, including
matching mesh/material/initial-field identities. All required fields exist.
Full trajectories still fail current admission: the initial timing is outside
the API, U0.115 CSV loads lose a final precision bit, tiny negative H/q occur
at three unloading states, and the producer/current Carrara arithmetic paths
exceed the adapter's strict relative tolerance at some points. These are
recorded without changing the contract or original arrays. No new FEM solve
or training was started. Both conditions are development-exposed; no matching
untouched test set is established. The [earlier inventory](fixed_weight_data_audit_20261021.md)
retains other assets, missing fields and original whole-condition splits.
Other real multi-condition carriers have cadence/support/semantics mismatches.
The known S09 exact producer and state adapters
are useful precedents, but one fixed trajectory, a source/export check or
numerical convergence does not qualify new parameter transfer or autonomous
rollout. FEM is a numerical reference, not experimental truth.

## APIs and local checks

Put `source/` on `PYTHONPATH`, as existing runners do. Configurations are in
`configs/fixed_weight/{conditional,transition}.json`; their scales are explicit
unit/example choices, not fitted from held-out data. Before a scientific run,
freeze physical units and scales using training-only information.

```python
config = ModelConfig(**json.loads(config_path.read_text()))
model = FixedWeightFieldModel(mesh, config)
# Producer-only, after separate execution approval:
corpus = prepare_training_corpus(manifest, explicit_loader, mesh, materials)
trained, receipt = train_shared_weights(corpus, mesh, config, training_config, authority)
save_checkpoint(checkpoint_path, trained, provenance=receipt)
# Inference has no optimizer, targets or training call:
predictor = FrozenPredictor.load(checkpoint_path)
one_step = predictor.predict(origin, next_request, material)
continuation = predictor.rollout(origin, prescribed_requests, material)
```

`fixed_weight_training.py` constructs one Adam optimizer for the entire shared
training run; sampling is uniform over trajectories, then transitions. Its
guard rejects Mac, missing authority, excess step/wall budgets and non-CUDA
placement before training. It does not perform remote submission or a retry.
The authorization object records prior human approval; it does not grant it.
Producer availability, immutable code identity, exact data and execution
receipt still require the project's approved handoff. Importing does no work.

`fixed_weight_inference.py` deep-copies and freezes the model, uses
`torch.inference_mode`, and has no optimizer or training import. Checkpoints
contain configuration, mesh, weights and provenance, with no optimizer state.
An untrained model stays explicitly marked untrained.

Historical 2026-10-21 check commands (completed; not a default rerun suite), all
synthetic and no optimizer updates:

```bash
python -m pytest -q tests/test_fixed_weight_contract.py tests/test_fixed_weight_learning.py tests/test_fixed_weight_evaluation.py
python scripts/check_fixed_weight_learning.py --config configs/fixed_weight/conditional.json
python scripts/check_fixed_weight_learning.py --config configs/fixed_weight/transition.json
```

Tests intercept optimizer construction/backpropagation in inference, compare
all parameters and buffers before/after load/unload/reload, exercise checkpoint
roundtrip, whole-condition splitting, denied loader callbacks, timing and
identity mismatches, raw/projected outputs, and history behavior on unloading.
Gradient-only loss tests do not create an optimizer or enter a training loop.

Local verification on 2026-10-21: **80 tests passed**, including the three new
test modules and reused `test_s09_fem_physics.py` /
`test_s09_stage0a_transition.py`. Both configuration-driven synthetic inference
checks completed and reported unchanged weights/buffers. No measured model
accuracy is reported. Independent implementation review found and prompted
repairs to the committed lower-bound timing, boundary admission, secant
branch logic and roundoff-safe unload/reload boundaries; the regression tests
preserve those cases. Final independent read-only review is bound to code
`440d4f7dea60175d2ce36deba99692a49e1332ee`, both committed configurations,
and the synthetic/component test scope. It found no blocking implementation
issues; its own rerun also passed all 80 tests. This is not experiment approval,
data qualification, or evidence of scientific predictive performance. The
subsequent documentation-only commit records this review without changing code.

## Evaluation and next decision

`fixed_weight_evaluation.py` supplies native-support MAE/RMSE/relative L2 for
each field, raw/projected admissibility, a kinematically lifted persistence
baseline, branch-restricted load-secant extrapolation, horizon-wise rollout
errors and equal-trajectory aggregation. `evaluate_continuation` connects these
to autonomous and teacher-forced predictions without passing reference future
fields into autonomous inference. Zero-reference relative errors are
undefined rather than silently assigned zero. Compare untrained conditions
using condition IDs absent from checkpoint training provenance; report within-
domain held-out conditions separately from extrapolation outside declared bounds.

Optional physics diagnostics require the explicitly named native Q4 AMOR,
AT1/Carrara, current-H, post-commit convention. They report boundary error,
elastic/surface energy, free-DOF force residual and H/q/alpha consistency.
Absent semantics or source, they are skipped. Phase KKT is skipped because
penalty/constraint data are missing. Do not interpret a falling total stored
energy during external loading as a universal validity criterion.

For each complete test trajectory report one-step, teacher-forced and autonomous
rollout separately; use horizons 1, 2, 4, 8 and the full available continuation,
including unloading/reloading. Compare with persistence and admissible secant.
Plot reference/prediction/error fields with matched scales and error versus
horizon; document raw/projected violations and any nonfinite failure. A good
one-step result cannot establish long-term prediction. Timing comparisons must
use matched accuracy, device, support and horizon, with synchronization/warmup,
and report data-generation + training + inference costs separately.
`matched_costs` refuses a speedup claim when the supplied quality criterion fails.

Decision ladder: D1 source/reuse audit complete; D2 implementation and synthetic
checks complete after code review; D3 an approved numerical-reference study
pending. Proposed D3 scope (not authorized or launched):

- First admit an existing, unprotected corpus of at least six complete distinct
  parameter/load conditions on one qualified small native mesh; use four train,
  one validation and one untouched test condition. All channels, substeps and
  source identities must satisfy this contract. Fix membership before outcomes
  are loaded. Six conditions support an exploratory comparison, not broad
  generalization. If the corpus is unavailable, stop; new FEM generation needs
  a separate explicit budget and approval.
- One seed, two routes, at most 1,000 optimizer steps and 15 minutes on one
  authorized GPU per route; combined cap 0.5 GPU-hour, no automatic retry or
  architecture sweep. Exact producer/data identities and physical normalization
  must be attached before the user approves execution.
- Primary exploratory decision: does either route reduce full-continuation
  training-scale-normalized error against both admissible simple baselines on
  the untouched condition? Select the scalar field weighting and meaningful
  tolerance from the scientific use and reference uncertainty **before** viewing
  that condition. Report individual field errors and horizon drift regardless
  of this decision. This proposal is not a frozen confirmatory protocol.
- Stop on data/identity mismatch, nonfinite loss/gradients/predictions, resource
  budget exhaustion or unavailable producer. Preserve a negative result. If
  one-step fit improves but rollout drifts, investigate state/update consistency
  before expanding architecture. Accuracy, reference qualification and physical
  validation remain separate decisions.

Current authority covers only this local implementation and lightweight tests.
No training, FEM solve, remote producer run, retry, protected holdout access,
external message, file transmission or Git push occurred.


## 2026-10-22: complete native archive adaptation

The explicit v2 recovered-initial path extends the interface without relabelling
pre-cycle recovery as a post-history refresh. `iter_trajectory` requires full
exhaustion; `load_trajectory` retains its eager API. Source-aware archive
adaptation preserves immutable originals, validates source fatigue arithmetic,
binds complete-precision loads, and certifies only the five fixed rigid-translation
negative-energy points. The generic v1 adapter retains its strict rejection rules.

See [the source-aware adaptation report](fixed_weight_native_adaptation_20261022.md)
for exact source/run identities, the complete 882-state / 880-transition Torch
validation, independent reviews and the limited development-data scope. No training
or new FEM solve was launched.
