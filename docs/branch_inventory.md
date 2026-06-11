# Branch Inventory

This file records non-main branches and worktrees that are worth keeping or
reviewing. Use it to separate code/history value from bulky generated result
payloads.

## `worktree-sdf-discontinuity-embedding`

- Worktree path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/.claude/worktrees/sdf-discontinuity-embedding`
- Branch: `worktree-sdf-discontinuity-embedding`
- Remote tracking branch: `origin/worktree-sdf-discontinuity-embedding`
- Local archive path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/before_strict_setting_alignment/pidl_result/sdf_discontinuity_embedding/`
- Cleanup decision, 2026-06-11: keep branch/code; move ignored `hl_*` outputs to local archive; leave compatibility symlinks in the worktree.

Purpose:
SDF/discontinuity-ribbon embedding experiment for representation localization.
The branch tests whether localized SDF ribbon features and `uv_only` split
behavior can sharpen or explain crack/front localization.

Status at archival:

- Local branch was ahead of origin by 2 commits.
- Local-only commits:
  - `fa6e5b2 add: FEM-vs-PIDL comparison + Umax sweep analyzers (SDF v1)`
  - `1b538d8 add: FWHM band-width audit (Layer-2 morphology check)`
- Remote head: `b442dc3 plot_sdf_ribbon_N30_5panel: 2x3 grid layout for readability`
- New tracked analysis/render scripts in the local commits:
  - `SENS_tensile/analyze_fem_vs_pidl.py`
  - `SENS_tensile/analyze_fem_vs_pidl_umax.py`
  - `SENS_tensile/analyze_fwhm_band.py`
  - `SENS_tensile/plot_cross_umax_synthesis.py`
  - `SENS_tensile/render_fem_vs_pidl_alpha.py`

Credibility:
Use this branch as diagnostic / mechanism-discriminator evidence, not as final
strict-setting alignment evidence. The runs predate the later FEM-mesh state
timing and soft-hist0 strict alignment protocol, so conclusions should remain
qualified unless remapped by a later note.

Next decision:
Review whether the two local commits should be pushed, merged, or copied into
the main code path. The worktree checkout can be removed later if the code is
preserved and this inventory remains current.
