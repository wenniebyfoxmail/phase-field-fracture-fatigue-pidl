# PIDL/FEM Clear Comparison Board

**Date**: 2026-07-07  
**Current main pair**: PIDL hard recovery c89 vs FEM SENS recovery `N_f=89`.

This is the current main comparison for the final aligned story. The older c69
soft-hist0 comparison remains useful as a diagnostic/reference-tier history, but
it is not the final event-scale comparison for the hard-recovery result.

## Pair

| Side | Package | Role |
|---|---|---|
| PIDL | `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/hard_d1_u0_recovery_5step_0630_formal` | Formal 2026-06-30 five-substep hard-damage `U=0` recovery cyclic PIDL run. |
| FEM | `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/extracted/SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4` | Closest FEM recovery comparator: SENS brittle-base hard crack line, state0 recovery, fatigue on, PIDL-style right-layer stop. |
| FEM state0 companion | `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/extracted/SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4__state0_recovery_from_driver_folder` | Required recovered state0 payload for the SENS comparator. |

Primary local source note:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/COMPARISON_TO_hard_d1_u0_recovery_5step_0630.md`

Primary analysis tables:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/tables/`

## Event Claim

| Quantity | FEM SENS recovery | PIDL hard recovery |
|---|---:|---:|
| Event scale | confirmed terminal/exported cycle `89`; first detection inferred at `N=86` by three-cycle confirmation logic | first boundary hit at `c89_peak`, step `444`; confirmed at step `447` |
| State0 damage energy | `Ed = 0.0050587345` | step0 `sum(E_d_elem)=0.00505321` |
| Event damage energy | available through FEM fields; final `int_d=0.0137382` in comparison note | step444 `sum(E_d_elem)=0.0209234`; step447 `0.0213736` |

Clean event wording:

> The hard-recovery PIDL run is aligned with the FEM recovery comparator at the
> event-window scale: FEM has confirmed terminal/exported evidence at cycle
> `89` with first detection inferred at `N=86`, while PIDL first hits at
> `c89_peak/step444` with confirmation at step447. This is not a
> first-hit-to-first-hit match.

## Mapping

PIDL step0 is the zero-load hard-alpha recovery state. After that:

```text
cN_peak     -> 1 + 5*(N-1) + 3
cN_unloaded -> 1 + 5*(N-1) + 4
```

Selected mapping:

| State | FEM cycle/state | PIDL peak | PIDL unload | Meaning |
|---|---:|---:|---:|---|
| state0 recovery | state0 recovery companion | 0 | 0 | zero-load recovered initial state |
| c1 | 1 | 4 | 5 | early comparison |
| c20 | 20 | 99 | 100 | early/mid fatigue |
| c40 | 40 | 199 | 200 | middle |
| c60 | 60 | 299 | 300 | late-middle |
| c69 | 69 | 344 | 345 | legacy diagnostic reference only |
| c89 | 89 | 444 | 445 | main event-scale comparison |

Important caution: FEM SENS uses `8` substeps per cycle, while PIDL uses one
recovery state plus five retained cyclic substeps. Compare labelled states
(`state0_recovery`, `c89_peak`, `c89_unloaded`), not raw substep indices.
The FEM semantics certificate verifies that `_008` VTK files are unloaded
end-of-cycle/post-cycle states. FEM peak raw-driver evidence comes from
`psi_fields/cycle_XXXX.mat:psi_elem`, not from a peak VTK; no
`fields_000089_004.vtk` peak-field export is available for this run.

## Field Claim

The event timing is aligned, but the field mechanism is not.

At `state0_recovery`, the damage energy is nearly identical:

| Metric | FEM SENS state0 | PIDL step0 |
|---|---:|---:|
| damage mean | `0.0197170` | `0.0391929` |
| damage p99 | `0.721765` | `0.887618` |
| `E_d` sum | `0.0050587345` | `0.0050532100` |
| fatigue history | `0` | `0` |
| fatigue factor | `1` | `1` |

At the event comparison (`c89`), note the mixed FEM state semantics: FEM
damage/history/fatigue fields are unloaded/post-cycle summaries from
`fields_000089_008.vtk` or matched element exports, while FEM `psi_elem` is a
cycle-peak raw undegraded tensile driver summary from
`psi_fields/cycle_0089.mat`.

| Metric | FEM SENS c89 output | PIDL c89 peak/step444 | Interpretation |
|---|---:|---:|---|
| damage mean | `0.0452642` | `0.251123` | PIDL damage is much more saturated/spread. |
| damage p99 | `0.912786` | `1.000510` | PIDL field is near-clipped at high quantile. |
| history mean | `0.442738` | `0.332604` | PIDL carries less fatigue/history on average. |
| history max | `14.3668` | `2.86897` | PIDL does not reproduce FEM's high history peak. |
| fatigue min | `0.0230954` | `0.0881062` | PIDL fatigue degradation is weaker at the strongest point. |
| FEM cycle-peak raw `psi` mean / PIDL active `psi` mean | `14.5008` | `7.55e-05` | PIDL active driver collapses relative to FEM peak raw driver. |
| FEM cycle-peak raw `psi` max / PIDL active `psi` max | `4791.24` | `0.0986513` | Same active-driver mismatch at max scale. |
| PIDL raw `psi` max | n/a | `43617.3` | Raw stress/energy exists, but is suppressed by degradation into a tiny active driver. |

Clean field wording:

> Event-window timing is aligned well enough for the main archived comparison,
> but the field mechanism is still mismatched: PIDL reaches the event through a
> much more saturated damage field and a severely collapsed active driver, while
> FEM retains a stronger cycle-peak raw driver/history structure near the event.

## What Not To Use As The Final Comparison

- Do not use `SENT_AB_nf69...` as the final event comparator for this hard
  recovery PIDL run. It is a useful control/diagnostic, not the main pair.
- Do not keep calling c69 the final fracture comparison. In this hard-recovery
  mainline, c69 is a legacy diagnostic state; c89 is the event-scale comparison.
- Do not compare raw substep indices between FEM and PIDL because the schedules
  differ.

## Baseline Provenance Audit

The baseline case audit is now closed as a local archive endpoint:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/baseline_case_audit_20260709/decision.md`

The FEM semantics certificate is copied into the same endpoint:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/baseline_case_audit_20260709/fem_semantics_certificate_SENS_recovery_u012_20260709.md`

It accepts the pair as the main certificate-verified archived-output event-scale
baseline and records the remaining source/provenance limits:

- FEM `_008` VTK files are unloaded end-of-cycle/post-cycle states, not peak
  states.
- FEM `psi_fields/cycle_0089.mat:psi_elem` is the cycle-wise peak raw
  undegraded tensile strain-energy driver, averaged over element Gauss points.
- FEM `N_f=89` is the confirmed terminal/exported cycle; first detection is
  inferred at `N=86` by the three-cycle confirmation logic, but the console
  first-detection message was not persisted.
- PIDL `step447` confirmation is three raw PIDL steps after `step444`, not
  three full physical cycles.

The state0 sanity table strengthens the baseline: projected state0 damage mean
diff is about `3.4e-4`, history/fatigue match exactly, and total damage-energy
diff is about `5.5e-6`.

Use this wording:

> The archived FEM output package and archived PIDL output package are aligned
> at the event-window scale and show field-mechanism mismatch. FEM `_008` VTK
> fields are unloaded/post-cycle states; FEM `psi_elem` is a cycle-peak raw
> driver summary. This is not yet a fully source-reproducible strict
> setting-identical benchmark because the full FEM source snapshot is not stored
> in this local archive.

The compact event-window field diagnosis is now closed as a local archive
endpoint:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/event_window_field_diagnosis_20260707/decision.md`

It covers `state0`, `c69`, and `c89`, and includes:

- `tables/event_window_scalar_summary.csv`
- `figures/event_window_residuals_state0_c69_c89.png`
- `figures/event_window_driver_raw_vs_active_c69_c89.png`
- `figures/event_window_scalar_diagnosis.png`
- projected raw/active driver arrays for `c69` and `c89`

Decision wording:

> The hard-recovery PIDL run aligns with the FEM recovery comparator in event
> timing, but not in the field mechanism: the event is reached through a more
> saturated PIDL damage field and a collapsed active driver rather than the
> FEM-like process-zone/history-driver structure.

Next work should start from a PIDL Experiment Gate for the
active-driver/process-zone mismatch; matching `N_f` alone is no longer enough.

## Second-Stage Mechanism Diagnosis

The active-driver collapse diagnosis is now closed as a local archive endpoint:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/active_driver_collapse_diagnosis_20260709/decision.md`

It reuses the existing FEM-grid polygon-overlap projection and decomposes the
c89 active-driver failure into raw-driver support, degradation suppression, and
spatial overlap. The first percentile-only `top 5% FEM psi` mask is quarantined
because FEM `psi` is extremely sparse; the revised verdict uses
denominator-safe masks such as `top1_clean`, `FEM psi >= 1200`,
`FEM psi >= 2400`, and `FEM psi >= 2900`.

Refined diagnosis:

> The c89 active-driver mismatch is degradation-collapse dominated with
> raw-amplitude under-support relative to the FEM cycle-peak raw `psi` output.
> In the denominator-safe c89 event core, projected PIDL raw driver is not
> absent, but PIDL damage is already saturated and the active/raw term collapses
> by about six orders of magnitude, so the active driver is suppressed before it
> can reproduce the FEM process-zone driver.

Next work should target bounded-degradation/history-update diagnostics while
keeping raw-driver amplitude as a secondary audit. Do not launch another full
production run just to chase `N_f`.

## Third-Stage Mechanism Diagnosis

The bounded-degradation/history-update diagnostic is now closed as a local
archive endpoint:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/bounded_degradation_history_update_diagnostic_20260709/decision.md`

It uses only existing c69/c89 projected fields from the active-driver collapse
package. No PIDL/FEM production run was launched. Primary evidence stays on the
denominator-safe c89 masks: `fem_top1_clean`, `fem_pz_1200`, and
`fem_core_2400`; the older top5 FEM-psi mask remains quarantined as primary
evidence.

Refined diagnosis:

> The c89 active-driver collapse is bounded-degradation dominated. In two of
> three primary high-FEM masks, the declared empirical g-floor counterfactual
> raises active/FEM by at least three orders of magnitude, while PIDL alpha is
> already saturated or slightly above one over much of the event core. The
> c69-to-c89 transition gives partial history-update support: the fixed c89
> regions are already substantially damaged at c69, but overshoot grows and
> active/raw drops by about 2.7-2.9 log10 units by c89. Raw-driver amplitude
> remains a real secondary gap, not the next primary branch.

Next work should be a small source-level or micro-run diagnostic for bounded
alpha/degradation handling and history-update ordering. It must pass PIDL
Experiment Gate again; do not start a new full production run from this result.

## Fourth-Stage Micro-Diagnostic

The bounded-alpha/history-order micro-diagnostic is now closed as a local
archive endpoint:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/bounded_alpha_history_order_microdiagnostic_20260709/decision.md`

It projects existing PIDL native element diagnostics for steps
`344/345/444/445/446/447` onto the FEM grid and ranks four source-level next
branches: residual/degradation floor, alpha cap, history-ordering/lagged driver,
and raw-driver amplitude. No production run was launched.

Refined branch decision:

> The cleanest next intervention is a residual-stiffness/degradation-floor
> micro-run. A `g` floor of `1e-3` raises median active/FEM by roughly three
> orders in the c89 primary masks without changing the raw field. Alpha caps
> below one also help, but mainly by acting as an implicit degradation floor.
> Lagged `hist_alpha` driver is not supported as a fix by the existing export,
> and raw amplitude remains secondary. Existing `psi_plus_prev_elem` appears
> synchronized in the exported diagnostics, so pre-refresh history ordering
> needs an explicit pre-refresh export or a tiny code-path micro-run.

Next work should be a PIDL Experiment Gate proposal for a tiny
`residual_stiffness_or_degradation_floor` code-path micro-run/export. Success
must be measured on denominator-safe c89 active-driver support, not scalar
`N_f`.

External review follow-up captured at `2026-07-09T23:59:03+0100 BST`:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/_pidl_attempt_ledger/attempts/20260709_chatgpt_review_residual_floor_next_step_v1/chatgpt_review.md`

The external audit agrees with the local branch decision: launch only a tiny
residual-stiffness/degradation-floor code-path validation, not a full production
run. Adopted gates are active/raw algebra, active/FEM lift at
`residual_stiffness=1e-3`, raw/FEM staying secondary, alpha-saturation
reporting, and no false production claim.

## Residual-Floor Code-Path Gate

The residual-stiffness code-path gate is now accepted after a closed
ChatGPT-audited loop: code audit, Codex action, Mac-safe checks, and
post-action result audit.

Local endpoint:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/residual_stiffness_code_path_gate_20260710/decision.md`

Implemented code path:

- `run_fem_mesh_probe_driver_umax.py` now exposes `--res-stiffness`, default
  `0.0`, so the archived formal baseline remains unchanged unless eta is
  explicitly supplied.
- `model_settings.txt` will record residual stiffness, runner git/sha
  provenance, the `Edegrade` formula, and diagnostic raw-export semantics.
- Element diagnostics now preserve legacy `psi_raw_elem=psi_active/g_alpha`
  while also exporting `psi_raw_from_g_alpha_elem`,
  `psi_raw_from_g_solver_elem`, and `g_solver_override_active`.
- `PFFModel.Edegrade`, `compute_energy`, and the history-update logic were not
  changed.

Mac-safe checks passed with the project Python; no Mac PIDL training was run.
Next work is a producer-side tiny `residual_stiffness=1e-3` dispatch note, not a
full production run and not a replacement final baseline.
