---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
record_type: deployment_state_acceptance
status: ACCEPTED_AS_CURRENT_DEPLOYMENT_STATE_NO_EXECUTION_AUTHORITY
date: 2026-10-20
---

# Accepted E017 deployment state

The user explicitly acknowledged the authorization-provenance incident recorded
at owner commit `ed166975ff6e4709561321aa644e75e099a74ee2` and accepted the
already verified archive as the current deployment state.

This acceptance binds only the following observed state:

- remote archive path:
  `/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/control/code.tar.gz`;
- archive size: `14,359,316` bytes;
- archive SHA256:
  `4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22`;
- archive source and embedded code identity:
  `2002538d9a30c8d4006ccaff5959cd214958fc82`;
- accepted machine-state evidence: all 28 content-addressed chunks verified and
  the published archive reverified against the frozen Git archive identity.

The acceptance does not retroactively validate the invalid second deployment
authority. It does not authorize SSH, a remote probe, resolver, admission,
scientific asset access, CUDA, a producer, training, cleanup, retry or any new
authority. The old failure and provenance records remain unchanged.

The state above is the last recorded observation, not a live refresh. Any later
authorized control attempt must revalidate it inside its one permitted attempt.
