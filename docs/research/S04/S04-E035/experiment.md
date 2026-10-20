# S04-E035 — Monotonic shear FEM/PIDL comparison

Purpose: extend the tensile solver comparison to a different loading mode;
exploratory synthetic numerical comparison, not material/road validation.

Goal anchor: tensile mechanism comparison → shear under an explicit common
material/loading/initial-state contract. User-directed fork on 2026-10-20;
existing tensile results and negative results are unchanged. One owner: this
Experiment. Branch `codex/fem-pidl-shear-20261020`; explicit remote base
`bf14e16a15173bc416d67f86ee2cac02025bbc56`. In scope: `scripts/shear/`, this
Experiment record and a concise Obsidian milestone. Shared source is reused
without modification. No public push, third-party communication, cyclic
fatigue, parameter sweep, or physical-validation claim is included.

## D1 reuse and option inventory

Searched the installed GRIPHFiTH `Scripts/{elasticity,brittle_fracture,fatigue_fracture}`,
`Sources/+specimen/+internal`, the existing `examples/SENS_shear`, shared PIDL
`SENS_tensile/field_computation.py`, `source/{compute_energy,fit,optim,utils}.py`,
and prior Windows handovers. Decision: reuse loading and model components;
fork a fresh shear case. The old `examples/SENS_shear` config names
`meshed_geom1.msh`, while only `meshed_geom1ses.msh` is present: do not blindly
execute the historical directory.

| Option | Actual installed source | Interpretation/readiness |
|---|---|---|
| Clamped single-edge-notched shear | `Scripts/brittle_fracture/INPUT_SENS.m` | Native MIEHE/AT2, sharp notch, E=210000/Gc=2.7, Ux=.015. Not interchangeable with normalized PIDL. |
| Simple plate horizontal displacement | `Scripts/elasticity/INPUT_SHEAR.m` | Bottom fixed, top Ux prescribed, top Uy free; differs from clamped SENS. |
| Tension | `Scripts/brittle_fracture/INPUT_SENS_tensile.m` | Existing AT1/AMOR normalized reference. |
| Three-point bending | `Scripts/fatigue_fracture/INPUT_TPB.m`; `Sources/+specimen/+internal/tpb.m` | Existing force-controlled bending setup, separate geometry/contact/support comparison required. |
| Mixed horizontal/vertical loading | `Sources/+phase_field/+fem/+bc/set_boundaries.m`; step params | X/Y displacements and tractions are supported. A mixed-mode case must explicitly define both components and supports. |
| Compression / reverse cyclic shear | BC primitives only | Do not infer qualified crack contact/friction or cyclic shear physics from available sign changes. Outside this first case. |

## Active decision and contract (revision 1, before execution)

**D2 active:** can the existing physics-informed NN reproduce the native FEM's
monotonic shear response and damage pattern? The mechanism is rotation of the
driving strain field and freedom for the crack to kink, while the material law
is kept at AT1/AMOR. No horizontal crack-growth or tensile mirror constraint.

- 1×1 domain centered at zero; retained material; initial crack segment
  x∈[-.5,0], y=0. Diffuse AT1 squared-distance profile with support 2ell.
- Plane strain; E=1, nu=.3, Gc=.01, ell=.01; residual stiffness=0;
  irreversibility penalty tolerance=.005; fatigue off.
- Bottom u=v=0; top u=U,v=0; sides natural free boundaries.
- Reuse historical PIDL shear schedule: .03,.06,…,.21,.24,.25,…,.46 (30 states).
  FEM native mesh `Dependencies/meshes/sens_mesh.m` Q4; PIDL uses the identical
  nodes with each Q4 split into two positively oriented T3 cells. Parent map
  and areas retained. This is a Q4/T3 comparison, not identical discretization.
- FEM retains native AT1 recovery penalty; PIDL retains its nonsmooth alpha
  map and three-point T3 irreversibility quadrature. These implementation
  differences remain explicit; do not attribute every discrepancy to NN capacity.
  In particular, T3 elastic/degradation energies use one-point centroid
  integration, while native Q4 FEM uses 2×2 integration; only the PIDL
  irreversibility penalty uses three points.
- PIDL 6×100 TrainableReLU seed1; existing log-energy/RPROP and weight decay
  1e-5; first-state LBFGS plus up to 10000 RPROP epochs per state; existing
  early stopping 5e-7. No FEM displacement/damage supervision.
- State0 is explicitly exported before any solve. Each state key is
  `(trajectory=shear-r1,U,step,post_solve_pre_history_update,support,channel)`.
  No fatigue-cycle mapping is imported from the tensile archives.

Primary descriptive observable: trajectory-mean area-weighted damage MAE on
the common Q4 cells over all states with accepted FEM output and a saved NN
candidate, with coverage and NN validity violations reported. No NN candidate
is removed to improve the score; an invalid candidate cannot support an
agreement claim. This clarification precedes any paired output. FEM nodal Q4
mean and area-weighted child-T3 means are declared
reductions. No ex-post binary accuracy threshold or superiority claim.
Diagnostics: direct top/bottom Rx, free-DOF equilibrium residual, E_el/E_d,
damage bounds/healing, forward damage morphology and selected matched-U fields.
PIDL reaction is sum of discrete nodal elastic internal forces at top DOFs,
obtained by differentiating E_el with respect to independent nodal u/v;
`2 E_el/U` is never substituted. FEM reaction comes from native assembly.
Raw/active AMOR energies, strain components and pre-update history retained.

Minimum output: explicit initial mesh/profile, per-state fields, scalar CSV,
source/runtime receipt and matched-U reaction/field plots plus README. Invalid
FEM states are not accepted. Incomplete/invalid NN states are reported as such;
an epoch limit is not convergence. Keep numerical status separate from errors.

## Bounded execution authority and resources

User request directly authorizes preparing and computing one shear FEM result
and its matching PIDL result. Conservative task-selected ceilings: one FEM
attempt ≤4 wall hours on `citpc12-ssh` (CITPC12); one PIDL attempt ≤4 single-GPU
hours on `gpu-server` (D-26-09); ≤10 GiB output per producer. These are ceilings,
not measured runtimes or additional authorizations for sweeps/retries. Stop on
nonfinite output, failed native acceptance, exhausted time/storage, or resource
conflict. No scientific retry or load/model change is silently allowed. At most
three short zero-start resource/environment rechecks within the ceiling.
Use fresh task directories, detached process and watchdog, immutable local
code snapshot; preserve shared installations/environments and other processes.
Independent read-only implementation review is complete; see code_review.md.

Resource coordination received from original research HQ at 22:25 UTC:
D-26-09 GPU0 is reserved for D5's authorized 40-epoch comparison. The earlier
idle snapshot does not admit this PIDL task. Hold PIDL launch until D5 exits
and the coordinated release is established; do not switch devices to bypass
the reservation. FEM producer has a one-experiment-at-a-time rule; recheck
MATLAB processes immediately before its launch. No reply/message to another
chat is sent by this task without human authorization.

## Decision ladder

| Step | Evidence / decision |
|---|---|
| D1 complete | Reuse native shear BCs + historical normalized PIDL loading; use AT1/AMOR in both. |
| D2 active | Review/validate the paired implementation, then execute one native shear trajectory and corresponding independent NN trajectory under resource admission. |
| D3 pending | Retrieve both; compare jointly valid U states, diagnose discretization/optimization/model differences; decide cyclic shear or another loading mode only from the result and new scope authority. |

## 2026-10-20 first-attempt outcome

R001 stopped at U=.03 after about31.22 supervisor seconds: final residual
assertion passed, combined damage-bounds/healing assertion failed. Accepted
loaded states 0/30; specific offending invariant was not exported. Initial
state/logs/code archive retrieved; no shear/FEM-PIDL agreement result exists.
See [run receipt](runs/S04-E035-R001.md). D2 remains active at reference repair;
R002 PIDL is prepared, not launched. No repeated attempt is implied.

The export-only diagnostic correction and bounded one-state proposal are ready
in [diagnostic_proposal.md](diagnostic_proposal.md), with fresh authority still
pending. Preserve R001, its consumed attempt and original thresholds. The
scientific verdict for the requested comparison remains inconclusive.

## R003 authority and local no-launch outcome

The original research HQ subsequently approved exactly the proposed one-state
diagnostic under its human-delegated night authority, adding 4CPU/16GiB RSS
limits and a total180-second envelope. Local resource-binding preparation
consumed148.92 seconds; the guard found only31.08 seconds left and stopped
before SSH. No R003 stage/worker/solve exists. The envelope was not reset.
See [R003 preparation receipt](runs/S04-E035-R003-preparation.md).

The single-call deployment is now assembled, with transport-failure receipts
and dirty-native source checks. It is preparation only pending a fresh execution
window; no additional scientific result, complete trajectory, or PIDL training
is claimed. The original shear comparison goal is unchanged.

## R004 diagnostic outcome and next decision

R004 retrieved the failing vector under the new900s total window. Both bounds and residuals pass; healing.00960853>.005 fails on250nodes, all on the initial fully damaged line. Independent recomputation confirms localisation and identical initial data. Accepted loaded states0/30; PIDL still not launched. See [receipt](runs/S04-E035-R004.md) and [prospective paired repair/resource proposal](repair_and_comparison_plan.md). D2 now awaits review/authority for the common hard initial-crack condition; no further solve is authorised by R004. Earlier pending-status paragraphs are historical.

## Prospective revision 2 — paired hard initial crack, 21 October BST

HQ-SHEAR-PAIRED-PRECRACK-20261020 (human_delegated_hq) authorises the proposed common alpha=1 condition on the existing251-node segment in both solvers, review, one full30-state FEM and—only if reference complete and HQ explicitly releases GPU0—one matching PIDL. Off-line initial profile, original material/load/penalty/tolerances unchanged. Contract family now shear-r2-hard-initial-crack. This does not replace or rehabilitate revision1 negatives.

Total new package hard8hours INCLUDING preparation, review, queue, both runs, retrieval, analysis and Obsidian. Conservatively count from23:17:49Z; stop07:17:49Z, earlier than HQ absolute07:50Z. Native/PIDL each≤4hours,4CPU,16GiB hostRSS,10GiB output including temp/archive; GPU allocated/reserved≤24GiB, physical free≥4GiB. First scientific failure stops whole package. One≤60s zero-start admission per producer. See authority_paired_precrack.json; older proposed extra1hour is superseded, not additive. First FEM state is production prefix, no new diagnostic/pilot.

## R005 zero-launch transport outcome

Revision2 implementation and full FEM controller passed independent review. Actual native boundary/DOF source and installed21MEX byte identities verified;3no-training checks and actualmesh masks pass. One upload succeeded but SSH start failed during banner exchange; readonly attribution confirms freshproducerroot absent,0actualadmission/0worker/0solve/0acceptedstate. The one mechanical submission is consumed and not reset; see [R005 receipt](runs/S04-E035-R005.md). D2 remains preparation-complete/transport-blocked; no new scientific inference, no PIDL SSH/training. No additional start is authorised by this report.

R005 control-accounting limitation: all remote identity/upload/start/attribution66.202s exceed60s mechanical envelope by6.202s; startpath53.700s alone was below60s. Required attribution lacked a remaining-mechanical-time clamp. Preserve this defect and costs; no scientific work or rerun.
