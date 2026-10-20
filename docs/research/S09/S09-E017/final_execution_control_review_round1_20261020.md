# S09-E017 final execution-control review round 1

## Binding and verdict

- Candidate commit: `64d293742bf9e57e515fe719cdf875b66c9a5ab5`
- Review manifest SHA256:
  `7ea3b80170cbd6efdfc300a32c8ff5128582a863efe9ee57344f340da0c7c971`
- Package ZIP SHA256:
  `b1058525629d9b10277e26f28164782678f40cb0492f84538e08a7a254048093`
- Verdict: `E017_FINAL_EXECUTION_CONTROL_REVISE`

This review did not revoke the earlier real-adapter Code Ready conclusion. It
reviewed only the new execution-control diff and granted no execution authority.

## Blocking counterexamples

1. `validate_runtime_control` reconstructed its expected value from the
   supplied resolved config. Changing `producer.wall_time_cap_seconds` to
   `999999` therefore still passed.
2. A failed admission did not consume the only attempt because the runner did
   not reject an existing `admission_failure_receipt.json`.
3. Candidate/archive/authority and CLI-path failures occurred outside the
   admission receipt boundary. Resource-snapshot failure could also prevent the
   minimal first-stop receipt.
4. The disabled authority template and nested candidate contracts did not fix
   every field. Retry/network/grant fields, ordered checks, receipt fields and
   paths, the local network observation and extra launch keys could drift.

## Required repair and scope

Bind the resolved config to the exact frozen base-package bytes, consume the
single attempt through an exclusive token, put all post-token checks inside one
independent first-stop boundary, and compare the complete nested candidate and
disabled-template contracts. Add fixture counterexamples for each item, then
freeze a new commit and repeat only this focused review. No remote access,
scientific assets, runtime construction or training is part of the repair.
