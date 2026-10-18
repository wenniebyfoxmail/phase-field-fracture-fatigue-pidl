---
storyline_id: S04
experiment_id: S04-E016
protocol_revision: v2
status: blocked_implementation_preflight
started_at: 2026-10-08
primary_storyline: S04
related_storylines: [S09]
scientific_verdict:
---

# Two additional Hard5 Umax trajectories

## Purpose

Add one development trajectory and one untouched confirmation trajectory after
S04-E015 showed that the frozen 99-feature ridge map did not transfer across the
existing three Umax trajectories.

## Roles

| Umax | Role | Permitted use before the next protocol is frozen |
|---:|---|---|
| 0.115 | development | qualification, feature/model development, training |
| 0.125 | sealed confirmation | integrity/schema checks only; no event or field inspection |

## Claim boundary

This is a data-acquisition experiment. Passing means only that two exact-family
synthetic FEM trajectories were produced with valid identity, timing, mesh,
field, event, and provenance evidence. It does not establish a successful Delta
network, FEM physical truth, PIDL improvement, or real-road validity.

## Frozen producer contract

- Producer: `CITPC12` Windows-FEM / GRIPHFiTH only.
- Source: exact Hard5 eta0 five-substep family used for U0.11/U0.12/U0.13.
- Intervention: Umax only.
- Cycle scope: first-hit search through c160, plus confirmation-only cycles
  first_hit+1..+3 (absolute ceiling c163); otherwise right censoring at c160.
- State: exact existing cycle export semantics—within-cycle maximum raw driver
  plus end-cycle committed damage/history/degradation, with frozen reductions.
- Common grid: native 86,408-element Q4 order.
- Channels: native `d`, `alpha_bar`, `f_alpha`, and peak raw tensile driver.
- Development/confirmation firewall: U0.125 result stays in a Windows-local
  non-OneDrive opaque archive; only its overall hash and aggregate QA booleans
  are public until the next predictive protocol and unsealing rule are frozen.
- Two phases: Windows first returns the source/state0/mesh/config/export/event
  hash lock and a U0.115 c1 smoke. Long runs require `LOCK_ACCEPTED_PROCEED`.
- Smoke comparison: recompute U0.115 c1 reductions from retained native state;
  do not compare U0.115 field values against U0.12. A c1 cyclemax=s4 check is
  not evidence that this equality holds at later cycles.

Full execution and acceptance contract:
`docs/handovers/windows_griphfith_request_31_u0115_u0125_peak_trajectories_20261008.md`.

## Primary acquisition criterion

Both trajectories must pass all nine Request 31 acceptance clauses. A failed or
unidentified clause makes acquisition `BLOCKED`; it cannot be rescued by model
training or by changing solver settings.

## Stop rule

Stop when the qualified U0.115 package and sealed U0.125 package are available.
Do not train or unseal within S04-E016. The next experiment must freeze the
Delta-model development protocol before U0.125 is opened.

## Status

- 2026-10-08: user approved both trajectories.
- 2026-10-08: Request 31 prepared for Windows-FEM dispatch.
- 2026-10-08: Phase A c1 smoke completed but v1 failed: cyclemax raw driver
  is not identical to s4 raw driver, and `alpha_elem` must be mapped explicitly
  to the actual `alpha_bar_elem` s5-committed field.
- 2026-10-08: independent ChatGPT review verdict `FAIL_HOLD`; no long run is
  authorised. Existing U0.115/U0.125 archives require reuse and contamination
  audits before the exact Phase B scope can be decided.
- 2026-10-08: v2 read-only repair completed. Existing U0.115 qualifies for
  read-only reuse/reseal without a new solve; U0.125 is
  `exposure_unknown_not_cleared`; the frozen metadata-only rule conditionally
  selects fresh U0.1175. Status is `AWAITING_CHATGPT_REREVIEW`; authorised long
  runs remain zero. See `request31_v2_readonly_audit_20261008.md`.
- 2026-10-08: external v2 review returned `PASS_ONE_U01175_LAUNCH` and issued
  `LOCK_ACCEPTED_PROCEED` for exactly one fresh U0.1175 run. Producer preflight
  then failed closed on storage before MATLAB start: C: had 20.194 GiB free,
  versus 13.75 GiB estimated c163 output plus the unchanged 15 GiB reserve
  (28.75 GiB required; 8.556 GiB deficit). No second qualified writable volume
  exists and U: is unavailable. Long runs started: zero. U0.115 was resealed
  by read-only reference; U0.125 remained closed. Receipt:
  `C:\q4runs\request31_u01175_preflight_20261008_v1\launch_preflight_blocked.json`.
- 2026-10-09: read-only CITPC12 storage-recovery audit completed. Live C: free
  space was 22.013 GiB; MATLAB count was zero and the intended output root was
  absent. The unchanged 28.750 GiB gate therefore still fails by about
  6.737 GiB. A 9.675 GiB low-risk candidate pair was identified in the July
  U0.11/U0.12/U0.13 canonical roots and verified against the Mac/OneDrive
  mirror across all 459 files with identical tree SHA256
  `52d546a498c946eb9c0edbb568e5a962c3261159aea1d7762509bdde58a4468f`.
  No deletion, move, compression, MATLAB start, or FEM run occurred. Explicit
  human storage-mutation approval and a fresh unchanged preflight remain
  mandatory. See `request31_citpc12_storage_recovery_audit_20261009.md`.
- 2026-10-09: user authorised release of exactly
  `C:\q4runs\hard5_umax_20260729_v1` and
  `C:\q4runs\hard5_formal_20260727_v1`. Before release, the three canonical
  case trees were revalidated as 459 files / 10,388,657,995 bytes with the
  same complete-tree SHA256 above; the full two-root delete scope was 463
  files / 10,388,660,792 bytes, including four separately hash-matched queue
  provenance files. Post-action check at `2026-10-09T00:46:53+01:00` confirms
  both exact paths absent and C: free at 31.716698 GiB. Recovery is from the
  verified Mac/OneDrive July canonical mirror. MATLAB count remained zero and
  the U0.1175 output root remained absent. Storage capacity now exceeds the
  frozen 28.750 GiB threshold, but a fresh full producer preflight remains
  required before any launch.
- 2026-10-09: complete frozen producer preflight rerun after storage recovery.
  Storage (31.679737 GiB free versus 28.75 GiB required), zero-process,
  output-collision, clean snapshot/commit, snapshot manifest, solver, state0,
  both MEX binaries, qualification-v5, exact U0.1175 load values, and A/B
  capture-capability gates passed. Launch failed closed because the reviewed
  snapshot builder accepts only U0.115/U0.125, the frozen solver has no c160
  first-hit-search ceiling with conditional c161–c163 confirmation tail, and no
  reviewed exact U0.1175 launcher/log contract exists. MATLAB/FEM starts: zero;
  PID/command/log: null. Status is `BLOCKED_IMPLEMENTATION_PREFLIGHT`, not a
  scientific negative. See `request31_u01175_complete_preflight_20261009.md`.
- 2026-10-09: a minimal derived execution overlay was built without modifying
  the canonical snapshot. Authoritative candidate v3 is sealed at
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v3`, manifest SHA256
  `fbe2b9cc2fb8d71c01b5a58b0af50e09dd6f0084df0873278406992f55e17de5`.
  Validate-only/static review tests passed 9/9, including exact U0.1175-only
  admission, c160 right-censor, c160-hit-to-c163 confirmation, late-hit
  rejection, Contract A/B timing, and overlay path precedence. Status is now
  `READY_FOR_CHATGPT_IMPLEMENTATION_REREVIEW`; long FEM runs remain zero and
  production launch remains forbidden pending an independent verdict plus a
  fresh manifest-bound producer preflight. Review request:
  `docs/reviews/request31_u01175_implementation_review_request_20261009.md`.
- 2026-10-09: independent review returned `MODIFY_AND_REREVIEW` for v3 because
  production parent-path initialization could supersede the reviewed event
  policy and the approval/preflight contract lacked complete run-ID, nonce and
  freshness binding. v3 is superseded. Immutable v4 at
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v4` repairs only those
  implementation gates; manifest SHA256
  `72fbb67d9e052c5b1ee451c80e3ad82224e4a1e31386510e7f588048e55e49ce`.
  MATLAB validate-only tests passed 11/11 and PowerShell authorization tests
  passed 10/10. Canonical parent remained clean and unchanged; MATLAB count is
  zero and production output is absent. Status remains
  `READY_FOR_CHATGPT_IMPLEMENTATION_REREVIEW`; no approval, production
  preflight, c1 solve or long run is authorised. Review request:
  `docs/reviews/request31_u01175_implementation_v4_review_request_20261009.md`.
- 2026-10-09: independent v4 review passed, and a manifest/run-ID/nonce-bound
  approval plus fresh full producer preflight passed. The reviewed production
  launcher was invoked exactly once at `2026-10-09T01:09:03.9824443Z`, recording
  PID `30656`. The immediate health check found that PID absent, MATLAB count
  zero, both production logs empty and the output root absent. Authoritative
  status is `START_FAILED_NOT_RUNNING`, not `RUNNING`; no scientific payload or
  result exists. No second launch was attempted. The preflight receipt was
  renamed to `production_preflight_consumed_start_failed.json` so it cannot be
  reused. A retry requires reviewed launcher repair, new approval/nonce and new
  full preflight. See `request31_u01175_v4_launch_attempt_20261009.md`.
- 2026-10-09: read-only launcher diagnosis and immutable v5 candidate completed.
  Evidence confirms the v4 direct `Start-Process matlab.exe` attempt was not an
  observable persistent launch on this host, but does not isolate quoting,
  MATLAB launcher behaviour or process lifetime as the unique sub-cause. v5
  replaces only that boundary with `Start-Process PowerShell worker -> call
  operator MATLAB` plus a worker/MATLAB/heartbeat handshake before `RUNNING`.
  The harmless no-solve probe and failure branches passed: MATLAB 11/11,
  authorization 10/10, spawn-contract 6/6. Candidate manifest is
  `2f14fd5ad90a629ae88890b88e251b2653167928e0d20d0819ce6135873453c1`;
  canonical parent remains clean, MATLAB=0 and production output absent.
  Status is `READY_FOR_CHATGPT_LAUNCHER_REREVIEW`; no v5 approval, preflight or
  production attempt exists. Review request:
  `docs/reviews/request31_u01175_launcher_v5_review_request_20261009.md`.
- 2026-10-09: v5 was superseded before external review after a cross-check
  found its preflight writer and launcher targeted different review roots. No
  approval, preflight or production occurred. Immutable v5b aligns both paths
  and adds an explicit regression gate. Authoritative manifest is
  `14e96779d0ea83bdc8a7f7e351f988740708feb7d3a5949cbf39c2c4ffb2a219`;
  MATLAB 11/11, authorization 10/10 and spawn-contract 7/7 all pass. Parent is
  clean, MATLAB=0, output absent, and v5b approval/preflight are absent. Status
  remains `READY_FOR_CHATGPT_LAUNCHER_REREVIEW`. Review request:
  `docs/reviews/request31_u01175_launcher_v5b_review_request_20261009.md`.
- 2026-10-09: v5b external review returned `MODIFY_AND_REREVIEW`. Immutable v6
  adds worker-descendant/creation-time MATLAB attribution, guaranteed terminal
  receipts after worker start, a real missing-executable failure probe, and
  exclusive UTF-16LE native logs with decode validation. Windows R2025b was
  observed as worker -> MATLAB launcher -> MATLAB engine, so v6 selects the
  unique owned MATLAB leaf rather than rejecting the healthy two-level chain.
  Authoritative manifest is
  `61725acf0a07caa9c7b0e622c81f30d496f0f2d184cf0abaad419a5bba6e0d53`;
  MATLAB 11/11, authorization 10/10 and spawn-contract 12/12 all pass. The
  live probe recorded worker PID 27552, engine PID 49732, parent launcher PID
  25640 and engine creation time `2026-10-09T01:56:26.4540870+00:00`.
  MATLAB=0, output/approval/preflight absent, and no scientific payload exists.
  Status remains `READY_FOR_CHATGPT_LAUNCHER_REREVIEW`; no production retry is
  authorised. Review request:
  `docs/reviews/request31_u01175_launcher_v6_review_request_20261009.md`.
- 2026-10-09: v6 review returned `MODIFY_AND_REREVIEW` on one remaining
  launcher-only identity boundary. Immutable v7 requires the worker-owned,
  post-start MATLAB engine leaf to have normalized `ExecutablePath` exactly
  equal to the frozen R2025b
  `C:\Program Files\MATLAB\R2025b\bin\win64\MATLAB.exe`. Missing-path and
  launcher-only snapshots remain waiting and cannot report `RUNNING`.
  Authoritative manifest is
  `8a30ce48dfa4be30ba196a8d54a7177f74d0b79206fe292539eecce9f684f742`;
  MATLAB 11/11, authorization 10/10 and spawn-contract 13/13 all pass. The
  harmless live probe recorded worker PID 45668, engine PID 16160, launcher
  parent PID 36032, exact engine path and creation time
  `2026-10-09T02:05:13.1711990+00:00`. Parent manifest remains unchanged;
  MATLAB=0 and output/approval/preflight are absent. No production retry or
  scientific payload exists. Status is `READY_FOR_CHATGPT_LAUNCHER_REREVIEW`.
  Review request:
  `docs/reviews/request31_u01175_launcher_v7_review_request_20261009.md`.
- 2026-10-09: independent v7 review passed. A new manifest/run-ID/nonce-bound
  approval and fresh full producer preflight passed all canonical identity,
  exact evaluator, state0, MEX, qualification, load, A/B, engine prerequisite,
  zero-process, output-collision and storage gates. The exactly-one authorised
  production retry captured the reviewed worker -> launcher -> exact R2025b
  engine chain, but the post-launch health check found all three PIDs absent,
  heartbeat stopped at `matlab_call_operator_begin`, native logs empty, no
  terminal worker receipt and no output root. Authoritative status is
  `START_FAILED_NOT_RUNNING`, not `RUNNING`; scientific result is none. The
  preflight was consumed, no second retry is permitted, MATLAB=0 and output
  remains absent. See
  `request31_u01175_v7_launch_attempt_20261009.md`.
- 2026-10-09: v8 launcher-only diagnosis supports the OpenSSH process-lifetime
  hypothesis. A WMI-created Session-0 worker survived the creator SSH
  disconnect, and a second SSH connection observed worker PID 26892 -> MATLAB
  launcher PID 36376 -> exact R2025b engine PID 34688 during a 20-second
  no-solve probe; terminal exit was zero, MATLAB returned to zero and output
  remained absent. Immutable v8 manifest is
  `e80c4b835d68ccff941c5eccc95ab5f8a3aea5a40ab2462b8ac7cb3d81bfa74a`.
  MATLAB 11/11, authorization 10/10, spawn 13/13 and detachment 8/8 pass.
  Canonical parent remains clean. Status is
  `READY_FOR_CHATGPT_DETACHED_LAUNCHER_REREVIEW`; approval/preflight are absent
  and production was not started. See
  `request31_u01175_v8_detached_launcher_candidate_20261009.md`.
