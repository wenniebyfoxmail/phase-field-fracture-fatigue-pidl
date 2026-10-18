# Cleanup Manifest

**Date**: 2026-07-06  
**Scope**: second-layer confirmation for the `quarantine` / `do-not-cite` queue in `docs/aligned_result_registry_2026-07-06.md`.  
**Action taken**: read-only scan plus index-first quarantine creation. No large
result folder was moved or deleted. The local quarantine folder stores only
README/INDEX files and symlinks back to original paths:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/quarantine_20260706/`.

## Aliases

```text
PROJECT=/Users/wenxiaofang/phase-field-fracture-with-pidl
UPLOAD=$PROJECT/upload code
LOCAL=$PROJECT/local_archive
GAP=$LOCAL/taobo_remote_gap_census_20260627
STRICT=$LOCAL/after_strict_setting_alignment
PRESTRICT=$LOCAL/before_strict_setting_alignment
```

## Action Labels

| Action | Meaning |
|---|---|
| `keep` | Keep as-is; evidence or code value remains active enough. |
| `move_to_quarantine` | Move later to a clearly named quarantine/archive folder, preserving provenance. |
| `delete_candidate` | Safe candidate for physical deletion after one final human confirmation. |
| `review_before_action` | Needs branch/provenance/checksum review before any filesystem action. |

## Executive Summary

| Group | Observed size | Recommended action | Reason |
|---|---:|---|---|
| Pre-strict archive root | `26G` | `move_to_quarantine` by default; selective `keep` for cited lineage | Not comparable to current strict soft-hist0/reverseBC claims. |
| Failed / predecessor `4905a70` precrack roots | `342M` total visible | mixed: empty roots `delete_candidate`; non-empty roots `move_to_quarantine` | Superseded by complete precrack fatigue-mask export and selected FEM packages. |
| Normalized-interface hard-alpha 8-step case | `16K` | `keep` as provenance, `do-not-cite` | Tiny; documents the aborted/misaligned interface. |
| Empty surrogate placeholder root | `0B` | `delete_candidate` | No evidence payload. |
| Metadata-only large-root census | `2.7M` | `delete_candidate` after confirming full raw copies | Duplicate metadata now superseded by full `raw_remote/` roots. |
| Historical worktrees | `.claude 362M`, `.codex 310M` | `review_before_action` | Code provenance may contain unmerged commits or diagnostic branches. |

Index-first quarantine status:

| Quarantine root | Size | Contents | Data moved? |
|---|---:|---|---|
| `$LOCAL/quarantine_20260706` | `8.0K` | `README.md`, `INDEX.md`, and `pointers/` symlinks | no |

## Detailed Manifest

### 1. Pre-Strict Archive

| Path | Size | Why not mainline | Replacement / surviving evidence | Suggested action |
|---|---:|---|---|---|
| `$PRESTRICT/pidl_result` | `26G` | Pre-strict settings are not directly comparable to the current strict soft-hist0/reverseBC/state-mapped evidence. | Current aligned evidence lives under `$STRICT` and shared docs such as `docs/aligned_result_registry_2026-07-06.md`. | `move_to_quarantine` |
| `$PRESTRICT/pidl_result/upload_code` | `24G` | Large archived generated PIDL/result payloads from earlier shared-code state. | Use tracked `UPLOAD` docs/code plus strict local archives for current claims. | `move_to_quarantine`; split only if a cited figure depends on it. |
| `$PRESTRICT/pidl_result/sdf_discontinuity_embedding` | `1.9G` | Legacy SDF/discontinuity lineage predates later strict setting alignment. | Strict-ish endpoint is `discontinuity_sdf_xfem_uvonly_f17e77e_20260601` in the gap census plus `docs/branch_inventory.md`. | `keep` for now as lineage until the two local branch commits are resolved. |
| `$PRESTRICT/fem` | `300M` | FEM state is pre-strict and not the current reference package. | Use Windows-FEM Requests 21-23 and selected-state package. | `move_to_quarantine` |
| `$PRESTRICT/pidl_result/Alignment_check_monotonic` | `96M` | Pre-strict monotonic check; current monotonic semantics are covered by latest-code on/off pair. | `$STRICT/pidl_result/Alignment_check2_monotonic/PIDL_mono_onoff_latest_ddc22eb_20260627_234645/`. | `move_to_quarantine` |
| `$PRESTRICT/fem/Alignment_check_monotonic` | `38M` | Pre-strict monotonic FEM evidence. | Current load-value comparisons use strict monotonic notes and Windows-FEM semantic exports. | `move_to_quarantine` |
| `$PRESTRICT/pidl_result/manav_reproduction_8seed_20260621` | `44K` | Before strict alignment; useful only as backbone sanity lineage. | Later analysis exists under strict archive family and inventory rows. | `keep` because tiny and may preserve intent/provenance. |

### 2. Failed / Superseded `4905a70` Precrack Roots

| Path | Size | Why not mainline | Replacement / surviving evidence | Suggested action |
|---|---:|---|---|---|
| `$GAP/raw_remote/pf_precrack_fatigue_mask_4905a70_20260608_191639` | `0B` | Empty predecessor root. | Complete export: `$STRICT/pidl_result/Alignment_check2_cyclic/PIDL cyclic 012/cases/precrack_fatigue_mask_complete_export_630111c_20260609/`; Windows-FEM Requests 22/23. | `delete_candidate` |
| `$GAP/raw_remote/pf_precrack_fatigue_mask_clean_4905a70_20260608_192047` | `0B` | Empty failed clean attempt. | Same as above. | `delete_candidate` |
| `$GAP/raw_remote/pf_precrack_fatigue_mask_clean_4905a70_20260608_192103` | `90M` | Failed/path-length predecessor. Contains provenance/log/code, not a complete aligned result. | Later successful `ad085f3` predecessor and complete `630111c` export. | `move_to_quarantine`; preserve `JOB_RECORD.txt`, `RUN_PROVENANCE.txt`, and log first if deleting payload later. |
| `$GAP/raw_remote/pf_precrack_fatigue_mask_rsync_4905a70_20260608_191824` | `252M` | Rsync/package state with older mixed logs; not a clean single experiment. | Complete `630111c` export and selected-state FEM package. | `move_to_quarantine`; delete only if no unique script/log is cited. |

### 3. Hard-Alpha U0 Recovery Eight-Step Cases

| Path | Size | Why not mainline | Replacement / surviving evidence | Suggested action |
|---|---:|---|---|---|
| `$STRICT/pidl_result/Alignment_check2_cyclic/PIDL_cyclic_012/cases/hard_d1_u0_recovery_8step_cyclic_85125d5_20260629` | `16K` | Normalized-interface 8-step diagnostic was intentionally aborted after protocol mismatch; absolute displacement is the valid interface. | `$STRICT/pidl_result/Alignment_check2_cyclic/PIDL_cyclic_012/cases/hard_d1_u0_recovery_8step_absdisp_b6d5610_20260629`; `memory/successor_handoff.md`. | `keep` as tiny provenance, marked `do-not-cite`. |
| `$STRICT/pidl_result/Alignment_check2_cyclic/PIDL_cyclic_012/cases/hard_d1_u0_recovery_8step_absdisp_b6d5610_20260629` | `16K` | Not a replacement for five-substep baseline unless FEM exports same eight-step schedule. | Use as unload-path ablation only. | `keep` |
| `$STRICT/pidl_result/Alignment_check2_cyclic/PIDL_cyclic_012/cases/hard_d1_u0_recovery_cyclic_e9dc263_20260629` | `20K` | Diagnostic rather than primary field-closure evidence. | Five-substep strict baseline context in successor handoff. | `keep` |

### 4. Surrogate Smoke Roots

| Path | Size | Why not mainline | Replacement / surviving evidence | Suggested action |
|---|---:|---|---|---|
| `$GAP/raw_remote/pf_surrogate_smoke_fee0ccf_20260626_051135` | `0B` | Empty placeholder; no payload. | Non-empty tooling smokes: `pf_surrogate_smoke_fee0ccf_rsync_20260625_221322` and `pf_surrogate_smoke_ecafe0e_archive_20260625_221509`. | `delete_candidate` |
| `$GAP/raw_remote/pf_surrogate_smoke_fee0ccf_rsync_20260625_221322` | `7.5M` | Tooling smoke only; cannot support physics claims. | Use only as code-path smoke provenance. | `keep` because small. |
| `$GAP/raw_remote/pf_surrogate_smoke_ecafe0e_archive_20260625_221509` | `7.5M` | Tooling smoke only; cannot support physics claims. | Use only as code-path smoke provenance. | `keep` because small. |

### 5. Metadata-Only Roots Superseded By Full Downloads

| Path | Size | Why not mainline | Replacement / surviving evidence | Suggested action |
|---|---:|---|---|---|
| `$GAP/metadata_large` | `2.7M` | Earlier metadata-only census for roots that now have fuller `raw_remote/` copies. | Full or larger copies under `$GAP/raw_remote/`, especially `phase-field-pidl-adapthist-af5a533`, `phase-field-pidl-hardirr-6525a9f-runs`, and `pidl-allfemmesh-fb06879-runs`. | `delete_candidate` after confirming no metadata-only file is missing from full copies. |

Relevant full-copy sizes:

| Full raw root | Size | Current stance |
|---|---:|---|
| `$GAP/raw_remote/phase-field-pidl-adapthist-af5a533` | `2.2G` | `negative`; keep only if checkpoint/figure forensics needed. |
| `$GAP/raw_remote/phase-field-pidl-hardirr-6525a9f-runs` | `2.0G` | `negative`; candidate for later payload thinning after preserving decision/logs. |
| `$GAP/raw_remote/pidl-allfemmesh-fb06879-runs` | `1.1G` | `negative/diagnostic`; keep until strict FEM-mesh representation-control notes are stable. |
| `$GAP/raw_remote/phase-field-pidl-hardirr-41e0bf1-runs` | `511M` | `negative`; likely payload-thinning candidate later. |

### 6. Historical Worktrees

| Path | Size | Why not mainline | Replacement / surviving evidence | Suggested action |
|---|---:|---|---|---|
| `$UPLOAD/.claude/worktrees` | `362M` | Many historical or detached worktrees; code provenance, not result evidence. | `docs/branch_inventory.md` currently documents only `sdf-discontinuity-embedding`. | `review_before_action` |
| `$UPLOAD/.codex/worktrees` | `310M` | Active/diagnostic worktrees include history-driver, state-timing, and discontinuity-jump-head. | Some correspond to protocol experiments in `docs/pidl_experiment_inventory.md`. | `review_before_action` |
| `$UPLOAD/.claude/worktrees/exp` | `288M` | Largest Claude worktree group; may contain branch-specific code. | Must inspect branch/commit status before removal. | `review_before_action` |
| `$UPLOAD/.codex/worktrees/pidl-state-timing-diagnostic` | `213M` | Protocol worktree referenced in memory for state-timing diagnostics. | Keep until its experiment folders are fully represented in shared docs. | `keep` for now |

## Immediate Safe Candidates

These are the only entries that look safe enough for a later physical deletion
step, pending explicit human confirmation:

| Candidate | Size |
|---|---:|
| `$GAP/raw_remote/pf_precrack_fatigue_mask_4905a70_20260608_191639` | `0B` |
| `$GAP/raw_remote/pf_precrack_fatigue_mask_clean_4905a70_20260608_192047` | `0B` |
| `$GAP/raw_remote/pf_surrogate_smoke_fee0ccf_20260626_051135` | `0B` |
| `$GAP/metadata_large` | `2.7M` |

Total immediate disk recovery is tiny (`~2.7M` plus empty dirs). The meaningful
disk recovery requires a deliberate archive/quarantine pass over pre-strict
payloads (`26G`) and older negative large roots (`~5.8G` listed above).

## Recommended Next Pass

1. Use `$LOCAL/quarantine_20260706/` as the findability-first quarantine entry.
2. Only after citation checks, move, not delete, the pre-strict root groups that are not cited by current figures.
3. For worktrees, expand `docs/branch_inventory.md` to cover every listed worktree before removal.
4. For large negative raw roots, preserve `decision.md`, `RUN_PROVENANCE.txt`, `JOB_RECORD.txt`, logs, and small tables first; only then delete bulky checkpoints/figures if disk pressure demands it.
