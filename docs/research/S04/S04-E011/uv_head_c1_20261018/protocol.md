# c1s4 same-energy UV output head — prospective r1

Prepared 2026-10-18 Europe/London. Owner: chat `01a14e3b-f1ff-7360-a084-c1f13b261cc6`,
“验证位移–damage 耦合机制”. Parent Experiment S04-E011, new bounded exploratory
diagnostic, not a repeated PBD arm or modification of a prior verdict. No
execution/data-read approval exists. User approved code/card preparation only.

Branch `codex/s04-c1-uv-energy-head-20261018`, explicit clean base
`bf0f21b572ad2f5a74d30dfcf8fbf402ece2ab08`. Only this subdirectory and
`tools/s04_e011_uv_head/` are owned here. Existing FEM/PIDL source is inherited
unchanged. The shared checkout, E025, E026/L32, other owner documents and
Obsidian/Roadmap are excluded. Local branch is recoverable without a public push.

## Question and smallest intervention

Can a retained fixed-feature UV output-head energy solve produce lower **same
fixed-d elastic energy** than saved PBD's c1s4 full-network U-energy endpoint?
Synthetic seen development state, C1 numerical/optimization diagnosis, horizon0.
This is not a physical teacher, generalization, network-capacity theorem,
damage-coupled rollout or E024 supervised residual-head experiment.

State: canonical86756-node/86408-Q4/2x2GP c1s4, U=.11999988, MCS natural outer9
conditional accepted reference, source0a0691e, old original s3 FEM predecessor.
Original PIDL model4/ad749c8 (8x400 TrainableReLU, seed1). Fixed d is FEM d;
no PIDL/FEM histories are imported into a damage problem or equated. FEM and
PIDL original histories are NOT asserted equal. Elastic U objective has no
fatigue coefficient, phase penalty or history contribution when d is fixed.

Preserve PBD's original bubble/lift and float64 local reinterpretation: U and
theta are explicitly float64 as in PBD make_smooth, not the float32 joint-control
arm. Existing hidden features, trainable activation coefficients and damage-head
row remain bitwise unchanged. Legacy damage output is not used for energy.

One CPU economy SVD of mass-weighted physical displacement design, fixed
rcond1e-10. Add retained-subspace UV increments to ALL original head coefficients;
discarded directions remain at the original coefficients. No rank sweep, new
regularizer, head supervision, hidden-weight training or model overwrite.
One L-BFGS-B energy arm starts at zero increment; callback-confirmed accepted
points alone are retained if a trial/deadline is interrupted. Finite-budget
failure does not imply whole-network capacity limitation. Report retained and
full head gradients; retained stationarity cannot establish stationarity in
discarded directions. No reduced optimum is called an oracle.

## Inputs and reference reuse

`inputs.json` freezes FOUR files (21,049,958bytes): c1 prepared NPZ, original
model4, saved PBD U endpoint fields NPZ, saved PBD result JSON. Hashes/sizes are
copied from existing contract/retrieval metadata, not recomputed from payloads
during preparation. Runtime verifies them once before decode. Entire-file
hashing is explicitly scientific access, including bytes of unselected pack
members. Decode only listed fields; no MAT, checkpoint3, c20, nine E025 sources,
U0.1175/U0.125, confirmation data, scanning or fallback paths.

Saved baseline Eel=.005672469584399648 is the comparator. Runtime reads the saved
PBD fields once and checks energy identity within1e-10; it never reruns the PBD
optimizer or original full network arm. FEM free force must reproduce native
force within1e-10 and free-uL2<1e-8. Original UV energy must match saved PBD
objective_scale within1e-10. These are identity/numerical checks, not new fits.

## Decision and numerical realization

Primary directional quantity: G=(saved_PBD_Eel-actual_head_Eel)/saved_PBD_Eel.
Use the ACTUAL reconstructed raw-head network, not only cached basis predictions.
G>=1e-4 is the prospective directional screen inherited from the unrun head
proposal, not a physical accuracy or significance margin. Additionally the
absolute gain must exceed10times max(saved-PBD energy readout discrepancy,
actual-versus-basis energy discrepancy,64eps*original energy). These clauses
only require a positive gain to be resolved numerically. No all-metric-win gate.
Actual/basis displacement difference<=1e-9 and energy difference<=1e-10 are
realization-validity checks; failing them gives an uninterpretable implementation
result, not a negative mechanism result. One seeded FD direction at fixed
steps1e-5/1e-6/1e-7 checks retained derivative consistency; no optimizer run per step.

Robust gain -> usable optimization/conditioning witness, even if small and not
mechanically closed. No resolved gain -> stop this candidate; if retained
stationarity is unresolved, label it unresolved. Stationary retained solution
with remaining error limits only this retained fixed-feature problem, never the
whole network. Better energy with worse H1/residual/hotspots is reported as a
component tradeoff. No result automatically authorizes coupled continuation.

## Joint budget and stop rules

One approved guard invocation, one worker, one state, one head candidate:

- Max400 total elastic objective evaluations, including original/FEM/baseline
  readouts, FD trials, line searches, callback reads, restored/basis/actual final
  reads. Eight evaluations reserved from optimization for final observations.
-600s from guard start: no new optimization evaluation.840s: no new scientific
  worker evaluation.900s total guard envelope including input hash/decode, SVD,
  validation, fit, maps, caches, receipts and cleanup. Guard stops at895s with
  <=4s child termination reserve. One GPU; maximum0.25 GPU-hours, not a promise
  that the algorithm can finish within it.
- Sampled aggregate child-tree RSS8GiB; Torch CUDA reserved-memory cap12GiB;
  generated results/logs/caches/receipts100MiB.100ms RSS/output monitoring is not
  an OS hard-peak guarantee. Newly provisioned immutable code checkout is an
  input deployment asset, excluded from result bytes and reported separately.
- Taobo GPU0 only, no fallback. Require no existing GPU0 compute process,
  >=16GiB free VRAM, >=16GiB available host RAM, canonical data2 mount and >=5GiB
  disk; no shared-process/service mutation. Before launch recheck thread ownership
  and all producer processes for a duplicate item; possible duplicate stops.
- Accepted guard invocation atomically consumes `attempt_claim.json` BEFORE
  resource/source preflight. Any preflight, identity, numerical, IO, nonfinite,
  OOM, resource, exact stagnation or budget failure stops; no retry/resume, cap
  increase, extra state/seed/rank or silent producer change. Interrupted guard
  status is unknown until its OWN process/output state is checked, never a
  reason to launch again. Only its fresh child process group may be terminated.

Minimum outputs: head/conditioning, actual candidate u/v/d/raw, compact energy/
force/H1/L2/gradient/uncertainty summary, counted trace, worker+guard receipts,
one same-run field/difference/energy/residual figure and README_analysis.
Plot all elements at the fixed state, aligned scales, signed differences and
synthetic/single-state label. Missing render/identity/terminal evidence is
incomplete evidence, not physical failure. Later numerical/figure checking
requires explicit scope; no implicit post-run rescore or array reread is granted.

## Preparation and review boundary

Preparation may parse Python AST and input JSON or read existing text/receipts.
No numerical fixture, import of scientific runtime, optimizer, array hash/decode,
FEM/PINN computation, SSH, source deployment or Obsidian edit is performed.
The source package needs independent read-only static review bound to its exact
commit, contract and this protocol. That review cannot qualify numerical behavior
without a later approved run. Existing independent PBD findings are inherited
only for unchanged source; they do not approve this new optimizer/guard.

## Duplicate-work check, 2026-10-18

Read-only app list and latest turns inspected:

- `检查 PINN 和 FEM 网格差异` (01a0ed13…): completed PBD; same-energy UV head
  remains a proposed next card, explicitly no new computation started.
- `探索神经网络学习 FEM-PINN 残差` (01a1131d…): preparing L32 only; source chat
  further identifies its exclusive S04-E026 owner. This task never touches L32.
- `细化PINN复现FEM算法流程` (01a0ff36…): completed supervised residual-head
  shrinkage; that objective is different and does not establish this energy solve.
- `PIDL 上翘诊断与改善：完整物理场` (01a14bbc…): completed saved-field symmetry
  preparation, prospective separate two-arm trial, no same-item head execution.

No same-item execution observed in those current chat records. No remote process
inspection was authorized/performed, so this is a conversation-level check, not
a claim of live producer vacancy. Refresh again at action time; no messages were
sent to these chats and no other owner's files were edited.
