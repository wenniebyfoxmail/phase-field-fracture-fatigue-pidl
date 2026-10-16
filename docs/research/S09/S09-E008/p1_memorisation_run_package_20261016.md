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
exercise only synthetic/local no-training tests, lock a Git commit and packet
identity, and obtain an independent Code Ready review of the runner, resolved
config, data lock, update algebra and output contract. Any material change after
that review requires a new exact-commit review.
