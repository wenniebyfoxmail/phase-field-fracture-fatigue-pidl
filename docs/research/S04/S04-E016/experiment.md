---
storyline_id: S04
experiment_id: S04-E016
protocol_revision: v2
status: blocked_storage_preflight
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
