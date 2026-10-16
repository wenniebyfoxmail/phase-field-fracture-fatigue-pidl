# Stage-0A decoder independent Code Ready review, round 3 — 2026-10-16

## Identity and verdict

- surface: Haofan ChatGPT Pro account, Pro model;
- conversation:
  `https://chatgpt.com/c/6ad1faaa-2c0c-832a-88bb-ac744fa5532c`;
- reviewed commit: `856cbf2010118b1ed32653cba372ccd31e3318ee`;
- packet SHA256:
  `c8b40802a8334b3c375acf0c5b5b98357988c51098c531596b88322768ca98fe`;
- verdict: `REVISE_AND_REREVIEW` after 11m31s;
- status: `C1 CLOSED`, `C3 PARTIAL`, `C2/C4/C5 no regression`.

The reviewer matched all ten snapshot files, ran 18 included tests, six syntax
checks and 40 directed synthetic checks. Four checks reproduced the two
remaining defects. It did not access the real archive, run FEM, train a model
or execute an optimiser step.

## What closed

- Native nodal and GP weights are now derived internally from the exact hashed
  static bytes. Independent distorted-Q4, nondefault-GP-order, nonunit-
  thickness and object-reference probes agreed with scalar reference
  calculations. The former caller-authored weight route is gone.
- All 366 physical states are decoded after the all-file hash preflight. All
  six substeps receive support/dtype/value checks; 438 logical bindings and 73
  internally assembled endpoint transitions were observed. Sentinel probes
  found no endpoint off-by-one, channel transpose or unfilled-buffer error.
- C2, C4 and C5 showed no regression.

## Remaining C3 defect

For a logical alias row, the binding checked the physical source and payload
hash but copied `imposed_displacement` into the receipt without verifying that
it was finite and exactly equal to the decoded physical prior-s05 value. A
synthetic c0002_s00 value of `0.75` or `NaN` therefore still produced
`FULL_TRAJECTORY_DECODE_QUALIFIED` and `P1_CONTRACT_FROZEN`.

Minimum repair: parse every logical-row displacement, require finiteness and
exact equality with its decoded physical binding before receipt creation or P1
freeze.

## New D1 defect

The static parser extracted `thickness_raw.reshape(-1)[0]` without first
requiring a scalar. Synthetic `[2.5, 5.0]` and `[2.5, NaN]` thickness datasets
silently used `2.5`. Minimum repair: require the frozen scalar shape and check
the complete array for finiteness before extraction.

## Repair implemented after this verdict

- every logical binding now requires a finite displacement exactly equal to
  the decoded physical state;
- static thickness must be stored float64 with exact `(1, 1)` shape, be wholly
  finite and have a positive scalar value;
- regression tests cover mismatched/NaN alias loads and multi-element,
  partly-NaN and empty thickness arrays.

These are code/synthetic repairs pending another exact-commit review. This
verdict does not authorise a real scientific data-capability audit or training.

## Decision boundary

Only these two repairs, synthetic tests and exact-commit rereview are allowed.
The result does not establish FEM truth, capture neutrality, independent
teacher validity, damage-evolution prediction, rollout, generalisation or PINO
benefit.
