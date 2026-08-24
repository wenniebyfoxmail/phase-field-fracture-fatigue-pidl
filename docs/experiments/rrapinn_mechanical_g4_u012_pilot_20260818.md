# RRaPINN mechanical residual risk — G4 U0.12 development pilot

Status: **PREREGISTRATION FROZEN; LAUNCH BLOCKED**.

This document freezes the scientific design and decision thresholds. It is not
a launch receipt. No producer command may be derived from it until every
machine-readable prelaunch prerequisite in `rrapinn_g4_u012_packet.json` is
closed by a new review and the user separately authorizes launch. Full-run
receipts and sealed metrics are post-run evidence, not circular prelaunch
requirements.

## Five-question experiment gate

1. **Mechanism question.** Starting from the matched Formal PIDL U0.12 state at
   c60 unloaded, does the sole ME85 interior mechanical-residual tail term
   reduce genuine equilibrium-residual tails and FEM field-error tails, and
   move boundary first-detect from the Formal c89 result toward FEM c83?
2. **Claim changed by success/failure.** A full pass supports only a late-stage
   U0.12 intervention and permits a separately gated full-from-initialization
   U0.12 confirmation. Failure blocks longer training and held-out amplitudes.
3. **Cheaper diagnostic first.** G1b qualified the mechanical residual, G2
   qualified the opt-in utility, and G3 qualified producer plumbing. Before G4
   launch, an offline lambda-trajectory audit and a one-cycle A replay sentinel
   must pass.
4. **Minimal assets.** One sealed metrics table, one event/state map, one
   residual/field figure suite with sidecars, a machine-readable first-detect
   receipt, and `analysis/decision.md`.
5. **Registry handoff.** Close the case in the canonical RRaPINN track and add
   exactly one row to `docs/pidl_experiment_inventory.md`. Do not add it to the
   aligned-result registry unless all three efficacy categories pass.

Claim class: `field-mechanism` plus timing, conditional on a qualified replay.
This is not a full-trajectory method claim and is not a real-road claim.

## Why c60, not c82 or full-from-initialization

- A c82-peak branch inherits virtually the entire baseline trajectory and has
  only one physical cycle before FEM c83. It can test local optimizer response,
  but cannot support a causal first-detect claim.
- A full-from-initialization pair is the correct eventual confirmation, but it
  is unnecessarily expensive before restart, residual-export, exact-peak FEM,
  event-receipt and blind-analysis capabilities are qualified.
- The frozen pilot therefore branches at c60 unloaded. It exposes about 22
  physical cycles before c82, covers a trajectory guard at c76, and remains
  materially cheaper than replaying c1 onward.

## Frozen start state

The common source is the existing Formal PIDL U0.12 baseline:

- state: `c60_unloaded_post_commit`;
- saved raw step: `300`;
- next raw step: `301 = c61 substep 0.25`;
- `checkpoint_step_300.pt` SHA256:
  `771bf8122c34097ddaee55e9952c3bef187aa320dfcd02eed148febe6e10e729`;
- `trained_1NN_300.pt` SHA256:
  `1316984f53297075dccadd38efd04972ce3942caa294b4b0a4f61c3c87b10d41`.

The restart bundle must also contain the common pretraining model and every
history array used by restore logic, truncated to exactly 301 entries (steps
0--300). It may not contain future c61+ baseline values. A manifest must bind
every file name, SHA256, shape and state label. Both arms must receive
byte-identical bundles.

## Frozen paired design

- Arm A: Formal PIDL with the mechanical-risk config absent.
- Arm B: the same Formal PIDL plus ME85 with `alpha=0.85`,
  `lambda=0.000549728557462236`, `E_ref=1`, and `L_ref=1`.
- G3 already proved absent/off exact equivalence, so no long risk-off arm is
  added.
- Seed 1, 8x400 coordinate MLP, eta=0, five absolute substeps
  `[0.03,0.06,0.09,0.12,0]`, hard-alpha recovery history, current-active
  driver, `fem_gp_tri3_g_mean`, FEM-like irreversibility quadrature, mesh,
  material, event thresholds and all non-risk mechanisms remain identical.
- Optimizer is frozen to RPROP 10000, LBFGS 0, relative tolerance `5e-7`.
- No tuning of alpha, lambda, optimizer, clipping, masks, sampling or stopping
  criteria is permitted after seeing either arm.

Run from step301 through boundary first-detect and the existing archive-complete
stop, with a hard outer limit at physical c92. Confirmation bookkeeping may be
retained for safe archival, but it is never the truth or headline metric.

## First-detect semantics

The headline event is the first raw step at which at least three right-boundary
nodes have damage greater than 0.95. The receipt must separately record raw
step, physical cycle, substep, maximum boundary damage, qualifying-node count
and trigger source. Energy-drop fallback is diagnostic only and cannot satisfy
the headline event.

With one recovery step and five retained substeps:

`physical_cycle = floor((raw_step - 1) / 5) + 1` and
`substep_index = (raw_step - 1) mod 5` for raw steps at least one.

FEM truth is first-detect c83. FEM c86 is its historical confirmation and is
not used as truth. A must replay the original boundary first-detect c89;
otherwise implementation drift makes the pair inconclusive. B passes timing
only if its first-detect is within c80--c86 and strictly closer to c83 than A.
Detection before c80 or no detection through c92 fails timing.

## Frozen evaluation states and residual gate

The trajectory guard is c76 peak, which is guaranteed pre-event under the
timing window. c82 peak is a fixed same-cycle transition-stress state, not
unconditionally pre-event: each arm must be labelled `pre-first-detect` or
`post-first-detect` from its sealed event receipt. Each report must include
architecture, arm ID, physical cycle, substep, raw step, comparison class and
per-arm event status.

Use the genuine interior-free-node intensive mechanical residual with nodal
dual-area weighting. Report mean, p95, p99, CVaR95, CVaR99 and worst-1%-area
mass. The element proxy `abs(E_el)+abs(E_d)` is forbidden as a substitute.

- c76: `CVaR99_B / CVaR99_A <= 0.90`;
- c82: `CVaR99_B / CVaR99_A <= 0.80`;
- at both states: `mean_B / mean_A <= 1.05`.

## Frozen FEM field gate

Headline comparisons require hash-locked c76/c82/c83 exact-peak FEM exports and a
hash-locked contained-domain projector. The existing mixed-timing c82 package
is context only and cannot satisfy this gate. Mapping-fallback cells are a
whole-domain sensitivity, not part of the headline tail domain.

At c82 peak:

- active-driver log-error CVaR99: `B <= 0.80 * A`;
- active-driver mean log-error: `B <= 0.95 * A`;
- raw-driver log-error CVaR99: `B <= 0.90 * A`;
- absolute FEM-p99 support IoU:
  `IoU_B >= max(IoU_A + 0.05, 0.10)`;
- absolute support-area ratio for B lies in `[0.5,2.0]`;
- own-top1% support IoU for B is greater than A;
- active-driver correlation:
  `corr_B >= max(corr_A + 0.05, 0.20)`.

At c76 peak, active-driver mean and CVaR99 may each be at most `1.10 * A`.
At c82, damage MAE, history log-MAE and fatigue-factor MAE may each be at most
`1.10 * A`.

Report damage IoU at 0.25/0.5/0.75, connected components, crack tip, centroid,
forward extent, width and mirror asymmetry. Persistent one-sided support or
more than 10% asymmetry amplification relative to A fails the field gate.

If an arm first-detects before c82, its c82 result remains a declared
post-event transition stress and cannot be relabelled as common-pre-event
accuracy. The c76 guard remains the trajectory-level pre-event evidence.

## Blind analysis and stopping rules

- Producer arms use opaque IDs. The analyzer cannot read risk mode, provenance
  or logs while calculating metrics.
- Freeze and hash the analysis code, metric schema, exact-peak FEM files,
  projector and masks before launch.
- Write and hash the sealed metrics table before opening the arm map.
- Before launch, validate and hash-lock the Request 27 FEM/input files and seal
  the analysis-code hash. During each arm, record a host-level path-access
  ledger alongside the runtime receipt.
- Stop on NaN/Inf, missing checkpoint/export, hash or state mismatch, an A
  replay sentinel failure, two consecutive predeclared field regressions, or
  B/A wall-time-per-step or peak-memory ratio above 3 on their common c61--c82
  interval.

All three categories -- residual, FEM field, and first-detect -- must pass. A
residual-only gain is diagnostic and cannot promote the candidate.

## Qualification snapshot and remaining launch blocker

The frozen requirement catalog remains unchanged, but its current status is:

| Requirement | Status before a full A/B run |
|---|---|
| fail-closed c60 restart materializer | pass offline |
| optimizer-post/pre-history-refresh residual exporter | pass bounded Taobo A smoke |
| synchronized exact-peak c76/c82/c83 FEM bundle | **blocked: Windows-FEM Request 27 package absent** |
| boundary-only first-detect receipt capability | pass bounded producer trace |
| c60-to-c61 A replay sentinel | `PASS_EXACT_DECODED_REPLAY` |
| frozen c60/c76/c82 lambda audit | pass offline; 0.795%/0.972%/1.000% |
| contained-domain projector | pass offline and hash locked |
| producer validator, blind analyzer and runtime-receipt framework | framework qualified; full A/B receipts are generated only by the run |

The Taobo archive root is also qualified: the conventional result path under
the checkout is a compatibility symlink whose resolved target is the declared
`/mnt/data2/drtao/pidl_archives/<run_id>/...` root. This is not a launch
blocker and does not require a rerun.

Therefore the only unresolved external input prerequisite is Request 27's
native-Q4 exact-peak FEM package. After it arrives, its files must be
independently validated and hash-locked, the analysis-code hash must be sealed,
and a fresh launch gate must pass. Full A/B runtime receipts, sealed metrics,
per-arm first-detect receipts and the host path-access ledgers are required
outputs of a future run, not prelaunch inputs. Even after Request 27 arrives
and validates, G4 launch still requires explicit user authorization. Longer
training and held-out amplitude access remain unauthorized.

## 2026-08-24 exact-input integration amendment

Request 27 is now closed by native-Q4 package
`hard5_u012_exact_peak_native_q4_c76_c82_c83_20260824_v2.1`. All 20 package
hash records pass. The sparse c76/c82/c83 first-detect counts are `0/0/22`;
the c83 all-history identity is a hash-locked `historical_reference_receipt`,
not a continuous-history scan. c86 remains confirmation only.

The old projector is superseded for this package. Rebuilding against exact
double-precision centroids changes one contained assignment (FEM row 57509)
while preserving 85,113 headline and 1,295 excluded fallback rows. The real
blind analyzer now computes the complete residual, field, event and reported
morphology grid. Because the contained Q4 domain is not elementwise
mirror-closed, mirror asymmetry uses a frozen 64x64 area-weighted grid about
`y=0`, comparing only reflected occupied-cell pairs and requiring at least 50%
paired-area coverage; the exact domain provides 51.9323%.

This amendment closes the external input blocker but does not authorize
training. The remaining sequence is clean integration commit, immutable
prelaunch lock, fresh independent launch gate, then a separate exact user
authorization receipt bound to the lock and commit.
