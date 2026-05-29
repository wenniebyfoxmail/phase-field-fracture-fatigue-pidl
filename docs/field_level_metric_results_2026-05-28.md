# Field-Level Metric Results (2026-05-28)

Branch: `codex/field-level-metric-representation`

## What Was Run

Added and ran:

- `SENS_tensile/compute_field_level_score_v0.py`

Outputs:

- `SENS_tensile/field_level_score_v0_details.csv`
- `SENS_tensile/field_level_score_v0_summary.csv`
- `SENS_tensile/alignment_mesh_probe_u012_reverseBC.csv`
- `docs/fem_pidl_element_nodal_definitions_2026-05-28.md`

This is a v0 scorer over existing artifacts. It separates:

- strict same-probe comparisons: FEM projected to PIDL probes vs PIDL on the
  same probes;
- compact same-probe comparisons from the baseline/femAnchorBC audit;
- summary-level comparisons for adaptive sampling;
- partial summary comparisons for Exp18 tip-local runs.

Update after Windows-FEM handoff `5c9c0e5`: the reverseBC P0 combined handoff
was synced from OneDrive and scored. The strict row is now present as
`baseline_vs_reverseBC`, meaning baseline PIDL evaluated against the reverseBC
FEM reference on common PIDL probes.

Update after the FEM/PIDL definition audit: the old `psi_plus` label was
ambiguous. FEM exports raw peak `psi_elem`; older PIDL diagnostics stored
`g(alpha) * psi+_0`. The mesh-probe script now reports both `psi_plus_raw` and
`psi_plus_active`.

## Key Numbers

Lower score is better. Log-ratio scores are absolute log errors unless noted.

| Method | Evidence | Rollup component | Mean score | Reading |
|---|---|---:|---:|---|
| baseline_vs_reverseBC | strict same-probe available | strict field | 0.71 | Preferred aligned reference; better than original/femAnchorBC rollup but not closed |
| femAnchorBC | strict same-probe available | strict field | 1.01 | Better than baseline, but not closed |
| baseline | strict same-probe available | strict field | 1.25 | Strong field mismatch |
| femAnchorBC | guardrail raw/log | V7/reaction | 0.35 | Clear guardrail improvement |
| baseline | guardrail raw/log | V7/reaction | 0.99 | Worse boundary/reaction behavior |
| v4 add-only adaptive sampling | summary-level | field summary | 0.90 | Small improvement over PIDL baseline |
| PIDL baseline | summary-level | field summary | 0.98 | Baseline summary mismatch |
| Exp18 mlp_s2_all | partial summary | field partial | 1.80 | Worse than adaptive/baseline summary |
| Exp18 fourier_s2_all | partial summary | field partial | 1.91 | Worse than adaptive/baseline summary |
| Exp18 siren_s2_all_adapthist_wr010 | partial summary | field partial | 1.96 | Worse than adaptive/baseline summary |
| Exp18 mlp_s1_alpha | partial summary | field partial | 2.05 | Worse than adaptive/baseline summary |

Important component-level results:

- Strict raw tip-driver mismatch is now small after separating raw/active
  definitions:
  - baseline_vs_reverseBC strict `psi_plus_raw` tip-driver mean: `0.09`;
  - femAnchorBC strict `psi_plus_raw` tip-driver mean: `0.13`;
  - baseline strict `psi_plus_raw` tip-driver mean: `0.16`.
- Strict active/degraded tip-driver mismatch remains large:
  - femAnchorBC strict `psi_plus_active` tip-driver mean: `2.14`;
  - baseline_vs_reverseBC strict `psi_plus_active` tip-driver mean: `2.62`;
  - baseline strict `psi_plus_active` tip-driver mean: `2.97`.
- Strict boundary-band score improves:
  - baseline: `1.31`;
  - baseline_vs_reverseBC: `0.02`;
  - femAnchorBC: `0.82`.
- V7 guardrail improves strongly:
  - baseline raw V7 mean: `0.83`;
  - femAnchorBC raw V7 mean: `0.12`.
- Adaptive v4 is a small summary-level improvement:
  - PIDL baseline summary rollup: `0.98`;
  - v4 add-only adaptive sampling: `0.90`.
- Exp18 partial morphology remains poor:
  - representative partial morphology scores: `2.24-2.48`.

## Interpretation

0. **The reverseBC strict score is now the primary row.** The field-level
   conclusion should be read against `baseline_vs_reverseBC`: boundary-band and
   overall scores improve relative to the original FEM reference, but the
   tip-driver error remains orders of magnitude large.

1. **BC alignment helped the guardrails and boundary band, but did not close the
   core field gap.** This supports keeping femAnchorBC as a secondary alignment
   diagnostic, but not treating it as a field-level solution.

2. **The dominant strict mismatch is still the tip driver.** The `psi_plus`
   audit changes the diagnosis: raw peak `psi+` in the tip region is close for
   reverseBC on common probes, but the active/degraded driver `g(alpha) * psi+`
   is still orders of magnitude off. The remaining gap is therefore tied more
   to damage localization/degradation coupling than to raw elastic driver
   amplitude alone.

3. **Adaptive/refinement is not the missing field mechanism.** It improves the
   summary score slightly, but not enough to change the research direction.

4. **Exp18 tip-local heads should remain closed as a field-closure route.** The
   partial score is weaker than adaptive/baseline summary and the montage already
   showed centerline/right-boundary morphology.

5. **The score is v0, not final.** Exp18 is only partial because its current
   artifact is not projected to the same FEM/PIDL probes. Before publication,
   the strict metric should be extended to any candidate archive we want to
   compare seriously.

## SDF / Discontinuity Audit

The project already tried a discontinuity-style representation:

- branch recorded in logs: `claude/exp/alpha3-xfem-jump`;
- added `source/xfem_jump_network.py`, `source/construct_model.py` changes,
  `source/model_train.py` hook, and `SENS_tensile/run_alpha3_umax.py`;
- architecture: continuous head + jump head + soft Heaviside at moving `x_tip`;
- T2 1-cycle Deep Ritz passed;
- T3 10-cycle fatigue smoke completed;
- T4 stationarity was marginal: modal stationarity `0.50`, not the planned
  `>= 0.95` gate;
- `alpha_bar_max` at cycle 9 was about `3.04`, better than some early variants
  but far below the production gate of `>= 12`.

So the correct statement is:

> A Heaviside/XFEM jump-head discontinuity embedding was tried and partially
> helped early anchoring, but it did not produce stable field closure.

## Architecture Decision

Given this audit, the next architecture discriminator should not be a naive
repeat of SDF/discontinuity embedding.

Recommended next step:

1. Use **reverseBC FEM** as the primary working field-level reference for the
   current Phase-1 evidence base, because most existing PIDL evidence and
   montages are already organized against this aligned reference and FEM is fast
   enough to regenerate.
2. Keep **femAnchorBC PIDL** as a secondary diagnostic for the opposite alignment
   direction: it tells us whether moving PIDL toward the physical FEM anchor
   improves guardrails and field metrics.
3. Extend the strict same-probe metric to any new archive.
4. Try **FBPINN/domain-decomposed tip patch** as the next clean representation
   test.

Alternative if we want to revive the discontinuity path:

- restart from `alpha3-xfem-jump`;
- fix tip tracking first, likely by pinning the discontinuity to a physical or
  FEM-anchored crack-tip trajectory rather than PIDL alpha argmax;
- then run the same field-level metric before any production sweep.
