---
storyline_id: S04
experiment_id: S04-E017
protocol_revision: v2-diagnostic-shared-vs-independent
status: design_revised_awaiting_rereview__training_not_authorized
started_at: 2026-10-15
primary_storyline: S04
related_storylines: [S09]
scientific_verdict:
---

# Diagnostic shared-versus-independent residual probe

## Road-Fracture Experiment Gate

- **Claim class / evidence domain:** C1 evidence-validity / synthetic.
- **One bounded question:** for the exact three-output architectures below, does
  the shared L0 configuration show a directional transformed-error advantage
  over the parameter-matched independent I0 configuration on every development
  fold/channel, while both remain numerically and state admissible?
- **Evaluation unit:** one complete Umax trajectory. Nodes, cells, cycles and
  adjacent states are not independent units.
- **Origin / horizon:** matched `cN_s4_post_history_commit`, horizon 0.
- **Allowed inputs:** exact frozen 32-column PIN-only causal feature recipe from
  S04-E016 lock `cb9f63f8...868c`; current/c-1/c-2 fields, missing masks,
  declared geometry, Umax and physical cycle only.
- **Learned targets:** FEM damage, `alpha_bar`, and direct `psi_raw`, each as the
  declared transformed Delta. There is no corrected `f`, active-support or
  event-time target. The existing causal `fatigue_f` input in the frozen 32
  columns remains an input only; it is not reconstructed from mean
  corrected history.
- **Evidence:** U0.11/U0.115/U0.12/U0.13 common pre-event prefixes, 357 cycles,
  85,112 admitted cells. U0.1175 and U0.125 remain closed.
- **Comparator:** I0, three independent MLPs. Candidate L0 is one shared encoder
  with three scalar heads. Total parameter counts are close, but this is not a
  compute-, per-task-capacity- or optimisation-equivalent causal ablation.
- **Primary diagnostic:** the fully specified Q in §5. It answers only whether
  these exact configurations show a worst-fold/channel relative advantage.
- **Stop rule:** any required missing, nonfinite, unidentified or inadmissible
  run makes the comparison inadmissible or inconclusive as specified in §5.
  A valid `Q >= 1-eps_Q` rejects directional advantage for this configuration;
  it does not reject every possible shared representation.
- **Minimum visualization:** paired seed ratios for every fold/channel plus
  L0/I0/B0 physical, transformed and C1-20 diagnostics; one fixed U0.115 C20
  raw field view if a Run is later authorized.
- **Blocked conclusion:** no useful-correction, FEM-teacher, physics, future
  prediction, road, confirmation, PCGrad or deployable-PIDL claim follows from Q.
- **Decision:** design-only revision. No runner implementation or training is
  authorized by this document.

## 1. Why v2 exists

S04-E016 D0-R002 was mixed: all-cycle transformed B1/B0 ratios improved, but
early damage worsened in all four folds, physical raw error worsened in three,
and the unconstrained correction produced materially invalid outputs. The old
D1 matrix proposed GradNorm/PCGrad before showing that a shared representation
beats an independent comparator. V1 therefore reduced the first question to
L0 versus I0.

Independent review of v1/e356da7 returned `NEEDS REVISION`; the bounded record
is `design_review_result_e356da7_20261015.md`. V2 removes the
invalid mean-history-to-mean-f derivation, narrows Q's interpretation, freezes
failure/tie/denominator rules, defines channel-scaled state tolerances and
positions this route relative to the cheaper physical-raw proposal. V1 remains
historical; no model result has been viewed and no Run exists.

GradNorm, PCGrad, CAGrad, hypervolume and confirmation scoring remain outside
this experiment. A later optimiser-conflict study would require a new reviewed
protocol after evidence of both shared value and actual gradient conflict.

## 2. Relationship to the single-channel physical-raw route

The S04-E016 physical-raw v2 proposal asks the cheaper upstream question:
whether a simple single-output, physical-scale raw correction can improve the
worst complete-Umax holdout without early-regime harm. It is the priority route
for the next design decision. S04-E017 asks a different question about three-
output shared versus independent representation and remains held; it does not
activate automatically.

The route order is:

1. complete independent review and the route decision for the single-channel
   physical-raw v2 design;
2. keep S04-E017 held unless that result motivates a multi-output representation
   question, or the user explicitly chooses that separate question despite a
   negative raw route;
3. if S04-E017 is later activated, obtain exact implementation review and fresh
   execution approval. Its result cannot retrospectively validate the raw route.

Thus this document is a ready-to-review alternative design, not authority to
implement it and not a claim that shared learning is now the preferred repair.

## 3. Frozen configurations and fairness boundary

| Arm | Architecture | Trainable parameters |
|---|---|---:|
| L0 | shared `32-128-128`, GELU, three linear scalar heads | 21,123 |
| I0 | three independent `32-68-68-1` GELU networks | 21,015 |

The total-count difference is 0.514%. This controls only total trainable count.
L0 has a wider shared trunk and three heads; I0 gives each task a private trunk.
The comparison cannot prove that parameter sharing itself caused any difference.

Four leave-one-Umax-out folds and seeds `[1701,1702,1703]` are frozen. Within a
fold/seed, both arms use identical sampled indices, row order, training-only
normalizers and target transforms. Training uses the same 2,048 systematic
geometry-only cells per cycle and the D0 case/three-stratum/cycle/native-area
weights; scoring uses all 85,112 admitted cells.

The implementation card must freeze one optimizer, learning rate, weight decay,
batch construction, fixed update count and scheduler for both arms. There is no
early stopping or score-based checkpoint selection: the final fixed-step
checkpoint is scored. For each shared update, L0 sees all three labels and uses
the arithmetic mean of the three individually standardized weighted MSEs. For
the same batch index, every I0 task receives one private optimizer update. Thus
per-task sample/update exposure is matched, while I0 performs three private
forward/backward paths per step and L0 performs one joint path. Wall time,
accelerator time, batches, optimizer updates, forward/backward counts and peak
memory must be reported separately; they are diagnostics, not Q.

Exact optimizer values and the measured resource cap are intentionally not
invented here. Until an implementation commit freezes and tests them without
scientific holdout selection, this experiment is not Run Ready.

Corrected fields are formed by adding predicted transformed Delta to the PIN
field and applying only the declared inverse transform. No clipping, projection,
cumulative maximum, target-derived mask or post-hoc repair is allowed. `f` is
not output or scored: `f(mean alpha_bar)` is not the native mean GP-level `f`.

## 4. State and numerical validity

The prerequisite audit established zero strict target violations over all
admitted development cells. The controlling output conditions are:

- damage must remain in `[0,1]` and be cellwise non-decreasing between admitted
  consecutive cycles;
- `alpha_bar` must be nonnegative and cellwise non-decreasing;
- direct `psi_raw` must be nonnegative; it is not a monotone state;
- all inputs, latent outputs, inverse transforms, predictions and metrics must
  be finite before and after each transform.

For each outer fold and channel y, freeze from outer-training data only:

```text
S_y = max(1, max_abs(training FEM y), max_abs(training PIN y))
tau_y = 8 * eps_float32 * S_y
```

The same frozen `tau_y` is used for that fold's three seeds and held-out
trajectory. Bounds use `tau_damage`, `tau_alpha` or `tau_raw`; temporal damage
and alpha decrements use their corresponding channel tolerance. This is a
channel-scaled arithmetic tolerance tied to the declared float32 inference
path, not a universal physical tolerance or an accuracy margin.

Strict counts/areas/magnitudes are always exported. A strict violation whose
magnitude is at most `tau_y` is reported as sub-tolerance numerical deviation.
Any bound or required temporal violation greater than `tau_y` invalidates that
fold/seed/arm. One such failure makes the complete arm comparison inadmissible;
no failing seed may be removed before aggregation. The target audit makes this
rule identifiable; it does not prove either model can satisfy it.

Before any real-data Run, deterministic tests must demonstrate:

1. **synthetic reachability:** known shared and independent mappings produce the
   expected directional/tie branches without using holdout values for tuning;
2. **zero-Delta control:** zero network Delta reproduces B0 fields and metrics
   to the declared dtype tolerance on every channel;
3. **violation detectors:** crafted sub-/over-tolerance bounds and damage/alpha
   decrements route exactly as specified, while raw temporal decrease is allowed;
4. **failure semantics:** NaN/Inf, missing run, denominator guard and tie
   fixtures cannot become a win or be silently dropped.

## 5. Primary Q and complete outcome rules

For fold u, channel v and paired seed s, let RMSE be the transformed,
stratum-equal, native-area-weighted error on the complete held-out trajectory:

```text
r(u,v,s) = RMSE_L0(u,v,s) / RMSE_I0(u,v,s)
m(u,v)   = median over the three paired seed ratios r(u,v,s)
Q        = max over four folds and three channels of m(u,v)
eps_Q    = 1e-10
```

Ratios are paired by the same fold/channel/seed. Never divide medians, substitute
another seed, or discard an invalid or unfavourable seed. For each denominator:

```text
tau_RMSE = 64 * eps_float64 * max(1, RMS(held-out transformed target))
```

If `RMSE_I0 <= tau_RMSE`, the relative advantage is unidentified and the
experiment is `INCONCLUSIVE_UNIDENTIFIED`; no floor is added. If I0 or L0 is
missing, nonfinite or invalid for any required fold/seed, the comparison is
`INADMISSIBLE`, not an L0 win. All twelve runs per arm are required.

The disjoint primary branches are:

| Complete valid result | Bounded interpretation |
|---|---|
| `Q < 1-eps_Q` | directional transformed-error advantage for exact L0 over exact I0 |
| `1-eps_Q <= Q <= 1+eps_Q` | numerical tie; no directional advantage |
| `Q > 1+eps_Q` | no directional advantage for this L0 configuration |
| unidentified denominator | inconclusive |
| missing/nonfinite/state-invalid required run | inadmissible |

This worst fold/channel median-seed diagnostic does not say that every seed
improved, that physical raw improved, or that either learned correction beats
B0. Report all paired seed ratios so the aggregation cannot hide seed failures.

## 6. Required non-voting diagnostics and research disposition

For L0, I0 and deterministic zero-Delta B0, export on every fold/channel/seed:

- transformed all-cycle RMSE and candidate/B0 ratio;
- physical-unit all-cycle RMSE and candidate/B0 ratio;
- C1-20 transformed and physical RMSE and candidate/B0 ratio;
- strict and tolerance-aware bounds/non-decrease area, RMS magnitude and maximum;
- parameter count, update/sample exposure and measured compute costs.

B0 is deterministic; it is repeated as the same comparator row rather than
pretended to have seed variation. These diagnostics do not vote on Q, but they
control what action is justified:

- `Q` directional but L0 does not beat B0 on physical/all-cycle or C1-20 views:
  record relative architecture advantage only; do not advance the correction;
- both L0 and I0 degrade against B0: stop this repair configuration even if Q
  favours L0;
- no valid Q advantage: reject only this exact shared configuration; do not add
  PCGrad, weights, seeds or data inside S04-E017;
- valid Q advantage plus coherent B0 diagnostics: independent evidence review
  may decide whether a separately designed follow-up is warranted.

Minimum decision evidence is an exact CSV plus a figure with all paired ratios,
B0-relative physical/C1-20 panels and fixed U0.115 C20 FEM/B0/L0/I0 raw fields
on common physical scales. A `README_analysis.md` must state the primary Q,
non-voting diagnostics, allowed conclusion and blocked conclusion.

## 7. Prerequisite result and present boundary

The deterministic read-only
`SENS_tensile/s04_d1_prerequisite_audit.py` completed in 2.2 s with status
`prerequisite_validated`. It checked the exact lock, mapping and four FEM payload
hashes, then inspected every admitted development target cell:

| Umax ID | cycles | damage decreases | alpha decreases | target bound failures |
|---|---:|---:|---:|---:|
| u011 | 121 | 0 | 0 | 0 |
| u0115 | 99 | 0 | 0 | 0 |
| u012 | 82 | 0 | 0 | 0 |
| u013 | 55 | 0 | 0 | 0 |

Damage increments are never negative. Minimum alpha increments are nonnegative
(0 to `4.77e-9`). Damage stays in `[0,1]`; alpha and raw remain nonnegative.
Raw receipt:
`local_archive/experiments/S04-E017/prerequisite_audit_20261015.json` in this
task worktree. No model, optimizer, GPU or confirmation state was run.

The audit also preserves the D0 warning: B0 damage has widespread tiny signed
tails down to `-2.80e-4` (and one maximum 1.0174), while B1 reached `-0.0956`
and 1.2681. Violation area without magnitude is not a sufficient diagnostic.

**Present next action:** finish the single-channel physical-raw design decision.
S04-E017 remains held and does not activate automatically. After that design is
confirmed, the user may separately decide whether to discuss S04-E017
implementation. No training is authorized.
