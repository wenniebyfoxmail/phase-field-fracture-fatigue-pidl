# S09-E008 P1 bounded memorisation run package — prepared, not authorised

## Decision enabled by A002

The A002 receipt passed an independent Evidence Ready review. The next action is
therefore limited to preparing this P1 package. `execution_authorized=false` in
the machine-readable config is deliberate: no trainer, packet-export route or
training commit has yet received exact-commit Code Ready review.

The planned learned map is

\[
\mathcal T^{peak}_\theta:
(d_k^{s00},[H,\bar\alpha,q_{prev},f]_k^{s00},\mathbf U_k)
\mapsto
(d_k^{s04},[H,\bar\alpha,q_{prev},f]_k^{s04},u_k^{s04}).
\]

It is a mixed nodal/GP, pre-cycle-to-peak transition. It cannot produce the
post-cycle `s05` state and is not an autonomous rollout operator.

## Frozen data and model scope

- development trajectory: sealed U0.125 only;
- cycles: `[1,2,3,4,21,29,41,46,48,58,60,69,70,71,72,73]`;
- native supports: 86,756 nodes and 86,408 Q4 elements × 4 GP;
- architecture: width 32, rank 8, two local blocks and one coarse block;
- seed: 20261016; dtype: float64; one example per update;
- exactly 1,000 successful updates, with the listed cycle order repeated;
- producer: Taobo GPU under a fresh `/mnt/data2/drtao/wennie/` run root;
- CSD3 is not a fallback.

The A002 damage, four history and two displacement scales are frozen verbatim in
`p1_memorisation_run_config_20261016.json`. The equilibrium scale must be
computed from the selected training set before model construction using the
declared affine-boundary/free-DOF-force formula, then written into the resolved
config. It cannot change after initial metrics are visible.

The scale interface has one fixed interpretation. The raw output heads consume
the damage scale and the first three history scales in the order
`H, alpha_bar, q_prev`; `f` is derived from `alpha_bar` and has no independent
raw head. The history data loss and `L_judge` consume all four history scales,
including the frozen `f` scale. Every model scale buffer is constructed directly
from the JSON value as `torch.float64`; no value may pass through float32 first.
The later Code Ready suite must compare every buffer with the configured
binary64 value exactly.

## Multi-objective update

The three update objectives are kept separate:

1. nodal state data plus raw nodal damage-increment supervision;
2. GP history data plus raw H/alpha/q increment supervision;
3. peak free-DOF mechanical equilibrium.

For each update, the runner must obtain three separate gradients, equalise
positive norms to their median, project conflicts in the fixed cyclic order
shown in the JSON config, average, and apply one global norm cap of 1.0 before a
single AdamW step. Raw objectives, scaled objectives, gradient norms, pairwise
cosines, projection count, zero-gradient count and effective merged direction
must be logged. Adaptive objective handling never enters `L_judge`.

Each objective gradient is represented in one frozen `model.named_parameters()`
order. A parameter not connected to a particular objective contributes an exact
zero block of the correct shape; its name is logged for that objective. Omitting
a block, changing order, or failing to record a parameter is a stop condition,
not a zero gradient. The whole objective direction is zero only when its full
vector norm is at most `1e-12`.

`1e-12` is a norm threshold throughout: an immutable projection reference is
skipped only when its squared norm is at most `1e-24`. The positive-norm
reference uses `torch.median`, hence the lower median for an even count. Cyclic
projection uses immutable balanced references; all three resulting directions,
including zero directions, are averaged before the single global clip. These
choices are method definitions and cannot be changed after metrics are seen.

The raw increment terms are paired with their matching data objective so hard
projection cannot hide a learnable negative proposal. They are not additional
voting criteria.

## Result definition without all-or-nothing information loss

The frozen scientific P1 verdict retains all necessary clauses from the
reviewed protocol. A full P1 development pass requires the capacity, growth,
near-stagnant and validity clauses together. A failure is also decomposed into
the following evidence buckets:

| Bucket | Question answered |
|---|---|
| Execution integrity | Did the exact packet/config/code complete 1,000 valid updates? |
| Architecture wiring | Were forward/backward, supports and hard constraints valid? |
| Overall capacity | Did `L_judge` reach 20% of its initial value? |
| Growth skill | Did predicted damage increments beat persistence on growth cases? |
| Stagnant control | Was false growth at or below `0.25 D`? |
| Objective behaviour | Which data/physics losses improved, conflicted or became inactive? |
| Claim boundary | What remains development-only and untested? |

This decomposition prevents one missed threshold from erasing successful
wiring or useful learning behaviour. It does not allow secondary diagnostics to
rescue the frozen P1 verdict.

## Hard-constraint validity contract

Hard constraints are checked on the projected forward output before every
loss/metric use, at initial and final evaluation, and on every update. Damage
irreversibility and its upper bound, and alpha irreversibility, use exact
comparisons because the forward projection constructs them exactly. Pre-state
and output Carrara identities use
`abs(error) <= 1e-12 + 1e-10*abs(reference)`. Monotone fatigue uses
`f_peak - f_pre <= 1e-12 + 1e-10*abs(f_pre)`. Prescribed peak boundary DOFs use
the same absolute/relative tolerance against the affine lifted value.

The pre-state Carrara check is an input qualification check. Failure stops before
model construction and teacher `f` is never rewritten. Raw damage/alpha proposal
clipping or saturation is logged as a separate diagnostic; it is not counted as
a violation when the projected output satisfies the frozen predicate. The exact
machine-readable predicates and check times are in the JSON config.

## Stop rules and outputs

Identity drift, nonfinite values, a hard-constraint violation, missing gradient
records, an invalid write root, GPU/disk preflight failure or an update-count
mismatch stops the run without retrying under the same Run ID. There is no
early-success stop and no post-result increase in width, seed count or budget.

The minimum output list is frozen in the JSON config and includes exact run and
input identities, initial/final judgement files, per-update loss/gradient logs,
the final checkpoint, decision metrics, and a decision-facing figure with a
README. Execution health and each scientific bucket must be reported
separately.

## Remaining gate

Before any training, implement the exact 16-cycle packet exporter and trainer,
exercise only synthetic/local no-training tests, freeze the candidate Git
commit, and obtain an independent Code Ready review of that exact code, the
configuration-resolution rules, the packet/data-lock generation and validation
rules, the update algebra, and the output contract. The actual packet identity,
data lock, GPU/environment, equilibrium normaliser and resolved config are then
produced in the fixed order below and checked by the final execution gate while
remaining bound to the same approved commit. Any material code or rule change
after Code Ready requires a new exact-commit review.

The resolution order is fixed. Package review precedes implementation. The
candidate trainer commit is frozen before Code Ready submission, and the same
commit must be the one approved. Only then may the reviewed exporter bind the
packet bytes/hash/data lock. A read-only Taobo preflight then locks GPU and
environment. The equilibrium normaliser is calculated with the same reviewed
physics implementation, checked finite and positive, and frozen before model
construction. The resolved config and final execution gate still precede every
optimiser step. None of these placeholders may be selected after initial metrics
are visible, and failure never falls back to CSD3.
