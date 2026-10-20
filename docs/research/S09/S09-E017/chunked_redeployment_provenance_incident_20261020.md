---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
deployment_attempt_id: s09e017-chunkdeploy-20261020T1754
technical_terminal_state: DEPLOYMENT_ARCHIVE_VERIFIED
control_terminal_state: AUTHORITY_PROVENANCE_INVALID_REUSED_INSTRUCTION
scientific_execution: false
date: 2026-10-20
---

# E017 chunked redeployment: technical completion with invalid authority provenance

## What happened

The owner agent interpreted the visible instruction “请重新投放” as a new
one-shot deployment-only authorization and minted attempt
`s09e017-chunkdeploy-20261020T1754`. After completion, headquarters established
that the displayed instruction was the same human instruction already consumed
by the preceding stopped attempt, not a new independent authorization. The
second authority file therefore has invalid provenance and must not be treated
as a valid approval record.

This was an execution-control error. No further remote action was taken after
the conflict was identified.

## Technical state observed before the provenance issue was known

The finite guard bound reviewed candidate
`90d0caab8752d662a1db8d475b2f9769f2185f3ea88b06ead5e1a675d8e3be25`
and plan
`0f5179cbbcc0e52f1923b4132d1e05694a3eccea2e8ffbfb9df1ac1562c0093a`.
It used one connection, no reconnect and no retry. The remote precheck found
`GPUServer8`, clean control checkout
`2002538d9a30c8d4006ccaff5959cd214958fc82`, and no blocked execution,
admission, output or final-archive path.

The persistent store reverified chunks 0--22. Chunk 23 was incomplete and
chunks 24--27 were absent. The single permitted missing-chunk transfer filled
the store, all 28 chunks passed SHA256 verification, and the plan published and
verified the exact 14,359,316-byte archive:

`4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22`.

The guard returned zero after 78.875 seconds. Resolver, admission, runner and
training were unreachable from the deployment-only plan; optimiser updates and
scientific execution remained zero.

## Control disposition

The remote archive is a verified observation of current machine state, but the
attempt is not a valid authorization precedent. It does not grant or revive
resolver, admission or producer authority. Do not delete, modify, consume or
execute from the deployed archive without a fresh explicit human decision that
acknowledges this provenance incident and defines the next bounded action.

The local immutable records are under
`local_archive/experiments/S09-E017/deployment_attempts/s09e017-chunkdeploy-20261020T1754/`:

- `deployment_authority.json` SHA256
  `c7465f0b6662d7aff2d5a46383601793afe025b22b15fb95c8ac7b14e4e0b41b`;
- `guard-consumption.json` SHA256
  `df9e6fc487ba0395d8feb560aa3d328eb7ed86e8aa08565b442a492e0222a63f`;
- `guard-receipt.json` SHA256
  `8ca02c5d890b6cc735ddfdf97e30b79de25a77339bb25017375703ceb0090ad7`.
