# Request 31 U0.1175 complete producer preflight

Date: 2026-10-09  
Producer: `CITPC12`  
Status: `BLOCKED_IMPLEMENTATION_PREFLIGHT`  
Long runs started: zero

## Decision

The storage blocker is cleared, and every available identity, qualification,
process, collision, loading, and capture-capability check passed. Launch remains
fail-closed because the frozen producer snapshot does not contain an executable
implementation of the reviewed U0.1175 scope.

This is an implementation-contract blocker, not a numerical result and not a
negative scientific verdict on U0.1175.

## Passed gates

| Gate | Evidence | Result |
|---|---|---|
| Storage | C: free `34,015,858,688` bytes = `31.679737 GiB`; required `28.75 GiB` including unchanged 15 GiB reserve | PASS |
| Competing process | zero MATLAB processes | PASS |
| Output collision | intended root and case root absent | PASS |
| Snapshot identity | clean commit `862992a60edc7f59335365beacb5c71fc8592a7a` | PASS |
| Snapshot manifest | `33443ef261ae529c6f57814d518fc4a5c905d94286bf835a83a06cd9733d522c` | PASS |
| Solver/export/event source | `82cf9d7f1d566c92cbb659c62d1a4ad6c41f827c1470d6f23bde6dd34ea2aad4` | PASS |
| Canonical state0 | `91b8f89ba3a211f08f1b79def5d2d50a973798e988deedc5c5c7e3b64a98ef11` | PASS |
| Native fatigue/history MEX | `cc9d673b44bfa6188aa269dbfd2c12829cbacd4d00de12103195731d13228494` | PASS |
| Native AMOR MEX | `ac9f5d5eacafa94434d5aab5bac3f3b2d003b9a540969122589d44ce9d095c63` | PASS |
| Qualification v5 | sealed manifest `b5c39464cd4091f67abff3944b23acf11a6d2cf7ada4be0e78c2de4c375fa33e`; passed/reference checked/capture neutral | PASS |
| Load contract | Umax `0.1175`; five nominal and effective displacements reproduced exactly | PASS |
| Export capability | audited source contains Contract A cycle summaries and Contract B same-state s4 nodal capture | PASS as code/audit capability only |

Frozen effective imposed displacements are:

```text
[0.0293748825, 0.0587498825, 0.0881248825, 0.1174998825, 0]
```

## Blocking gates

1. `build_hard5_new_stage0b_config.m` in the clean reviewed snapshot accepts
   only Umax `0.115` and `0.125`; it rejects `0.1175`.
2. `solve_fatigue_fracture.m` has confirmation-tail logic but no distinct
   first-hit search ceiling. Running with `max_cycle=163` would continue
   searching at c161–c163 when no hit occurred by c160, contrary to the frozen
   right-censoring rule. Running with `max_cycle=160` cannot retain a c160 hit's
   required c161–c163 confirmation tail.
3. No reviewed exact U0.1175 launcher/command/log contract exists on the
   Windows host. Searches found U0.1175 only in scope/metadata/preflight JSON,
   not in executable `.m` or `.ps1` launch code.

Creating or patching a launcher now would change claim-bearing execution code
after external review. Under the experiment gate it requires a minimal reviewed
implementation amendment and deterministic validate-only test before launch;
the old U0.115/U0.125 queue must not be repurposed silently.

## Windows receipt

```text
C:\q4runs\request31_u01175_preflight_20261009_v2\preflight_blocked.json
SHA256 F867E827DDAFB24BD7EDB0CD0B11BD83377C3F608FF74EBCDD23276059969409
```

Preflight implementation:

```text
C:\q4runs\request31_u01175_control_20261009_v1\run_u01175_complete_preflight.ps1
SHA256 BAA6427910EE46A1F4DF7C488BBB73DDB4DE1EB816DB84EC12B77F6A01A4CB35
```

No MATLAB/FEM process was started; PID, launch command, and log path remain
null. U0.115 remains read-only and U0.125 remains closed.

## Smallest next action

Prepare one minimal implementation amendment that:

- accepts only the fixed U0.1175 identity and run ID;
- preserves the clean snapshot physics and both A/B exports;
- implements `search through c160; if hit, run exactly three confirmation
  cycles; otherwise censor at c160`, with c163 as absolute ceiling;
- rejects all other amplitudes and second solves;
- passes validate-only/static tests and independent read-only review.

Only after that exact code is approved may the unchanged complete preflight be
rerun and the one authorised solve launched.
