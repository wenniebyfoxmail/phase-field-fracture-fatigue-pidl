# Field-Level Metric Results (2026-05-28)

Branch: `codex/field-level-metric-representation`

## What Was Run

Added and ran:

- `SENS_tensile/compute_field_level_score_v0.py`

Outputs:

- `SENS_tensile/field_level_score_v0_details.csv`
- `SENS_tensile/field_level_score_v0_summary.csv`

This is a v0 scorer over existing artifacts. It separates:

- strict same-probe comparisons: FEM projected to PIDL probes vs PIDL on the
  same probes;
- compact same-probe comparisons from the baseline/femAnchorBC audit;
- summary-level comparisons for adaptive sampling;
- partial summary comparisons for Exp18 tip-local runs.

Coverage caveat: **reverseBC FEM is the preferred working reference** for the
current evidence base, but the full reverseBC `u12` `.mat` handoff directory is
not present in this Mac checkout right now. The only reverseBC entry in the
available CSV artifacts is a partial summary row from an outbox note. Therefore
this v0 numeric table contains femAnchorBC strict scores but does **not yet**
contain reverseBC strict scores. That is a data-availability limitation, not a
change in reference choice.

## Key Numbers

Lower score is better. Log-ratio scores are absolute log errors unless noted.

| Method | Evidence | Rollup component | Mean score | Reading |
|---|---|---:|---:|---|
| reverseBC FEM reference | strict same-probe | pending | n/a | Preferred aligned reference, but full local `.mat` handoff is missing |
| femAnchorBC | strict same-probe available | strict field | 2.72 | Better than baseline, but not closed |
| baseline | strict same-probe available | strict field | 3.06 | Strong field mismatch |
| femAnchorBC | guardrail raw/log | V7/reaction | 0.35 | Clear guardrail improvement |
| baseline | guardrail raw/log | V7/reaction | 0.99 | Worse boundary/reaction behavior |
| v4 add-only adaptive sampling | summary-level | field summary | 0.90 | Small improvement over PIDL baseline |
| PIDL baseline | summary-level | field summary | 0.98 | Baseline summary mismatch |
| Exp18 mlp_s2_all | partial summary | field partial | 1.80 | Worse than adaptive/baseline summary |
| Exp18 fourier_s2_all | partial summary | field partial | 1.91 | Worse than adaptive/baseline summary |
| Exp18 siren_s2_all_adapthist_wr010 | partial summary | field partial | 1.96 | Worse than adaptive/baseline summary |
| Exp18 mlp_s1_alpha | partial summary | field partial | 2.05 | Worse than adaptive/baseline summary |

Important component-level results:

- Strict tip-driver mismatch remains enormous:
  - baseline strict `psi_plus` tip-driver mean: `12.61`;
  - femAnchorBC strict `psi_plus` tip-driver mean: `11.78`.
- Strict boundary-band score improves:
  - baseline: `1.31`;
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

0. **The reverseBC strict score is the missing P0 row.** The field-level
   conclusion should be read against reverseBC as the intended aligned reference,
   but this v0 table could only score femAnchorBC strictly because those CSVs
   exist locally. The next metric task is to sync or regenerate the reverseBC
   snapshots and run the same projection.

1. **BC alignment helped the guardrails and boundary band, but did not close the
   core field gap.** This supports keeping femAnchorBC as a secondary alignment
   diagnostic, but not treating it as a field-level solution.

2. **The dominant strict mismatch is still the tip driver.** The `psi_plus`
   tip-region log errors are about 12, meaning the model is still orders of
   magnitude away in the local driver on the same probes.

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

1. Sync or regenerate the full reverseBC `u12` handoff, then compute
   `alignment_mesh_probe_u012_reverseBC.csv` and add it to
   `compute_field_level_score_v0.py`.
2. Use **reverseBC FEM** as the primary working field-level reference for the
   current Phase-1 evidence base, because most existing PIDL evidence and
   montages are already organized against this aligned reference and FEM is fast
   enough to regenerate.
3. Keep **femAnchorBC PIDL** as a secondary diagnostic for the opposite alignment
   direction: it tells us whether moving PIDL toward the physical FEM anchor
   improves guardrails and field metrics.
4. Extend the strict same-probe metric to any new archive.
5. Try **FBPINN/domain-decomposed tip patch** as the next clean representation
   test.

Alternative if we want to revive the discontinuity path:

- restart from `alpha3-xfem-jump`;
- fix tip tracking first, likely by pinning the discontinuity to a physical or
  FEM-anchored crack-tip trajectory rather than PIDL alpha argmax;
- then run the same field-level metric before any production sweep.
