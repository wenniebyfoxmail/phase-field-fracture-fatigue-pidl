# Request 31 U0.1175 launcher v7 review request

## Requested verdict

Return one read-only verdict for this exact immutable candidate:

- `PASS_REQUEST31_U01175_LAUNCHER_V7`
- `MODIFY_AND_REREVIEW`
- `FAIL_HOLD`

This review cannot create approval/preflight or start production.

## Single v7 change

The v6 verdict was `MODIFY_AND_REREVIEW` on one remaining launcher identity
boundary. Descendant/creation-time/leaf checks were not sufficient because a
same-named executable could otherwise vote. v7 additionally requires the
candidate engine's normalized `ExecutablePath` to equal, using ordinal
case-insensitive comparison, exactly:

`C:\Program Files\MATLAB\R2025b\bin\win64\MATLAB.exe`

Missing `ExecutablePath` or a snapshot containing only
`C:\Program Files\MATLAB\R2025b\bin\matlab.exe` remains waiting and cannot
report `RUNNING`. Scientific code, Umax, event policy, physics, state0, MEX,
tolerances, update order and Contract A/B are unchanged.

## Candidate identity

- Windows root:
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v7`
- review root:
  `C:\q4runs\request31_u01175_launcher_review_20261009_v7`
- files: 18, excluding manifest
- manifest SHA256:
  `8a30ce48dfa4be30ba196a8d54a7177f74d0b79206fe292539eecce9f684f742`
- diff-contract SHA256:
  `26db5432dd41f93c2a7c443edc74e68a035c13e20b36f9b791e0a75ca27d8861`
- parent commit:
  `862992a60edc7f59335365beacb5c71fc8592a7a`
- parent snapshot manifest SHA256:
  `33443ef261ae529c6f57814d518fc4a5c905d94286bf835a83a06cd9733d522c`
- run ID:
  `hard5_u01175_stage0b_43d36a6de8a9431a803a17ad019a5bb9`

## Authoritative harmless probe

The real Windows R2025b process chain was observed as:

```text
PowerShell worker PID 45668
  -> bin\matlab.exe launcher PID 36032
     -> bin\win64\MATLAB.exe engine PID 16160
```

- engine creation time: `2026-10-09T02:05:13.1711990+00:00`;
- engine `ExecutablePath`:
  `C:\Program Files\MATLAB\R2025b\bin\win64\MATLAB.exe`;
- handshake: `PASS_LIVE_OWNED_WORKER_MATLAB_HANDSHAKE`.

The deterministic snapshot tests separately establish that unrelated MATLAB,
wrong-parent MATLAB, launcher-only, and missing-path candidates cannot vote.
The complete launcher-to-engine chain with the exact frozen engine path is
accepted.

## Exact no-solve results

- MATLAB implementation regression: **11/11 PASS**
  - receipt SHA256:
    `2888ccf0f242c0520d20d4b37e19cb2b36167381b65a085bf52e9f139c80eafc`
  - stdout SHA256:
    `db885fe0211b5952ccb4fcd9fd0c1a6e05f18a6d5f5badd9b82ae863f835491c`
- authorization regression: **10/10 PASS**
  - receipt SHA256:
    `ba5925e8352c97a8448436ceec6f6dad97a9d660acb375bece86ba7cce7ba21c`
  - stdout SHA256:
    `7ee5a7e0a96cfeca2a150107acee08ac9a24d8be5abc03615e84285d5d2cdc4d`
- spawn-contract regression: **13/13 PASS**
  - receipt SHA256:
    `35614e89433e13efb6aba7484af9a53ac766cc4c4ae4c4156ac31b534386e420`
  - stdout SHA256:
    `7f465e48330e5d157b6d38c5076392b088a1dd64a86efea3fe82bc9d64bd5474`
- real missing-MATLAB terminal receipt SHA256:
  `859307d8cbb261c95a20f1271794c77e25281ac004eb1921184fbc857f03a36f`;
- authoritative launcher validate-only exit: `0`;
- all authoritative stderr logs are empty, SHA256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The harmless probe called neither Request 31 nor the solver and created no
scientific payload.

## Final safety state

- parent snapshot manifest remains unchanged;
- MATLAB process count: `0`;
- production output root: absent;
- approval: absent;
- production preflight: absent;
- production retry: `false`.

A review PASS would establish launcher code readiness only; it would not
authorise production.

## Raw evidence

`local_archive/experiments/S04-E016/request31_u01175_launcher_review_20261009_v7/`

Bind any verdict to manifest
`8a30ce48dfa4be30ba196a8d54a7177f74d0b79206fe292539eecce9f684f742`
and the frozen run ID above.
