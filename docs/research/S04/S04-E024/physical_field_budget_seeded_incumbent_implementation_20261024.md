# E024-D014 implementation: verified seed and incumbent retention — 2026-10-24

## What changed

This implements the narrowly scoped repair identified by the completed D013 r3 run. The current runner now:

1. pins a saved D012 head by archive-manifest, file and quantized-array hashes;
2. reconstructs it through the frozen raw producer path and qualifies it with all 13 protections and E023-centred `Q <= .1`;
3. selects it only if that actual field has a strictly better deterministic key than E023: full-domain UV squared error, Q, source ordering, head digest;
4. emits a first `initialization` event and stores the selected initial head separately from the immutable E023 `original_head`;
5. retains the last actual-feasible incumbent if a later proxy returns no feasible direction or all finite candidates fail; and
6. recomputes qualification during replay, rejecting altered seed provenance, qualification, selected head, centre, trajectory or final receipt.

The four physical-change scales, all 13 ceilings, D, BC, compact window, masks, FEM reference and frozen history/fatigue remain anchored to each state’s own E023. A seed is not counted as an optimizer step, a trial, a new correction, a replacement baseline or a global full-head optimum. The summary now reports initial and final incumbent source so a retained D012 point cannot be misreported as a new D014 gain.

The contract is [D014 plan](physical_field_budget_seeded_incumbent_plan_20261024.md) SHA-256 `8b02d002476a07fe38264b23018f230c6a13382e73c9b95e4c63e6422d27730a` and [D014 contract](physical_field_budget_seeded_incumbent_contract_20261024.json) SHA-256 `7fb76a2264faaa15192cff5668714e0d477f8040622efefdb7e2e9b65797af24`. D013’s historical source and result remain unchanged.

## Fixed nontraining check

The sole representative check was:

```text
/Users/wenxiaofang/miniconda3/bin/python3 -m pytest tests/test_s04_e024_field_budget.py -k seeded_incumbent_is_strictly_qualified_retained_and_replay_bound -q -p no:cacheprovider
```

It passed: `1 passed, 50 deselected in 0.33s`.

The artificial ScalarAdapter benchmark verifies one qualified seed retained after a deliberately unresolved proxy, one over-budget seed that falls back to E023, a profile replay that rebuilds the seed qualification, receipt-level state replay, and rejection of a tampered selected head. It loads no real checkpoint or FEM asset, performs no scientific SLSQP solve or candidate forward, does not train, and writes no original checkpoint. A direct source-text compilation check of the five modified Python modules also passed.

## Status

This is implementation evidence only. It does not re-qualify the real c60 saved head in this D014 source, produce any c20/c60/c83 result, or establish that a seed will improve after a new local solve. The expected real qualification remains: c60 may be eligible under the prior D013 evidence; c20 and c83 must remain E023 unless the future raw all-13 check succeeds.

No scientific execution, remote action, training, history/fatigue update, external send or new independent Code Ready review was run. A future D014 run needs a new exact-source Code Ready/nontraining package and a separately approved final execution receipt.
