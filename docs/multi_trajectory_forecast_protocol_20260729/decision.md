# Decision: multi-trajectory forecast reassessment framework

## Verdict

The protocol/adapter readiness stage passes as tooling, but the producer gate is
closed:

    not_ready_no_training

No forecast training was launched. Agent/FEM task2 has not yet published the
signed trajectory bundle contract, per-bundle hashes or locked
leave-one-combination-out split. Agent3 therefore has zero countable
trajectories, even though the candidate 2x2 source directory exists.

## What is sealed

Three tasks are separate and cannot be pooled into one headline result:

1. observed-state, same-regime h1-h3 field propagation;
2. autonomous transition warning;
3. observation-reset conditional h1-h3 propagation.

Markov graph is the formal matched baseline. TCN and Transformer are the only
ranking-eligible candidates. Diagonal SSM is retained as a separately reported
conditional-propagation reference. GRU, LSTM, current_multiscale and new
architectures are excluded.

Every formal comparison uses seeds 1/2/3, 3000 fixed steps, the same optimizer,
loss, origin, masks, future scenarios and a road-aware parameter-count
tolerance of one percent. Context is fixed before producer data are opened:
Markov 1; TCN, Transformer and diagonal SSM 3.

## Trajectory split

The candidate source is:

    Umax_012_all_versions_20260729

It contains the hard/soft initial-tip x 5/8-step loading-history 2x2 factorial.
Presence was checked, but Agent3 did not audit mechanism completeness or infer a
producer schema.

Training becomes eligible only after Agent2 validates and signs all four
combinations and freezes leave-one-combination-out. Every cycle, reset and
normalization statistic belonging to the held-out combination remains outside
training. Multiple cycle windows from one combination never count as multiple
trajectories.

Passing this split would support only within-Hard5 factorial numerical-trajectory
assessment. It would not establish independent-road, road-section, geometry or
material generalisation.

## FEM-centred evaluation

Every held-out trajectory is reported individually before aggregation against
the same-seed Markov control. FEM eta0 remains the physical numerical reference.
The required suite includes:

- damage linear MAE/RMSE/correlation;
- history, raw-driver and active-driver log10 MAE/RMSE/correlation;
- area-weighted FEM absolute-p99 and own-p99 support IoU;
- absolute support-area ratio, centroid offset and width error;
- producer-declared event phase, warning lead, false warning and missed transition;
- interval coverage/width, Brier score, calibration error and NLL when eligible.

Unavailable uncertainty remains unavailable. Own-p99 measures localisation only
and cannot be cited as amplitude recovery.

## Long horizon

Field output is rolling h1-h3 after each new observed/assimilated state.
Longer-horizon output is scenario-conditioned transition hazard and RUL
availability. Hazard/RUL remains unavailable unless every outer training fold
contains both event and right-censored trajectories and uncertainty is
calibrated. Unlimited free rollout is a stress diagnostic, not road prediction.

## Exact training release gate

Training may start only when all are true:

1. Agent2 signed contract, split, schema id and SHA256 inventory are frozen.
2. A reviewed Agent3 adapter verifies every bundle path/hash and emits four
   unique within-Hard5 independence groups.
3. All four trajectories cover all three sealed tasks and use compatible
   observation/scenario contracts.
4. Leave-one-combination-out folds pass leakage tests.
5. The road-aware Markov/TCN/Transformer parameter manifest passes one percent;
   diagonal SSM remains a non-promotable conditional reference.
6. Seeds, fixed steps, optimizer, loss, origins, masks and scenarios are frozen.
7. No held-out combination is used for normalization, checkpoint, context or
   threshold selection.

Until then, this package authorises only adapter/validator maintenance.
