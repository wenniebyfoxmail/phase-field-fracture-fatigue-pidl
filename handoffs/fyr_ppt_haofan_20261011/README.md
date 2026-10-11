# First Year Report PPT handoff for Haofan

Prepared: 2026-10-11

This package accompanies the First Year Report Overleaf project already shared
with Haofan. It is a presentation handoff, not a new experiment and not a
replacement for the Overleaf manuscript.

## Frozen identities

- Overleaf version visible at preparation time:
  `f0675a56cff1c6ca31a917426f3a38ecde589b65`
- GitHub code branch base:
  `389f618b7a042e0a4e4d11a3ab24a7164f6902cc` (`origin/main`)
- Historical FYR code/result review package prepared on 2026-06-10.
- Current reporting correction: `current_claim_boundary/BENCHMARK_STATE_CONTRACT.md`
  dated 2026-09-29.

## Start here

1. Use the shared Overleaf project for the report narrative, equations and
   references.
2. Use `report_snapshot/thesis.pdf` as the frozen visual reference for this
   package.
3. Read `REPORT_TO_CODE_MAP.md` before editing or recreating any figure.
4. Read `current_claim_boundary/BENCHMARK_STATE_CONTRACT.md` before stating
   FEM/PIDL event-cycle agreement.
5. Use the PDF figures in `report_snapshot/Chapter3/Figs`,
   `report_snapshot/Chapter4/Figs` and `report_snapshot/Chapter5/Figs` directly
   in the PPT whenever no scientific change is required.

## Package contents

- `report_snapshot/`: the exact report PDF, Chapter 3--5 LaTeX, figures and
  figure-generation scripts from the frozen Overleaf remote commit.
- `code_snapshot/`: the historical minimal PIDL and GRIPHFiTH/FEM code snapshot
  prepared for FYR review.
- `alignment_evidence/`: compact CSV/JSON evidence, provenance notes and
  analysis scripts from the FYR alignment package. Large checkpoints and raw
  simulation arrays are intentionally absent.
- `current_field_evidence/`: compact tables, manifests and the analysis script
  behind the projected residual figures. Full projected `.npz` arrays remain
  in the local research archive and are not stored in Git.
- `historical_plot_scripts/`: best-available historical plotting scripts for
  the pre-alignment Chapter 4 figures. Their provenance limitations are stated
  in `REPORT_TO_CODE_MAP.md`.
- `current_claim_boundary/`: the later state/event reporting correction that
  must constrain PPT wording.
- `SHA256SUMS`: content hashes for every file in this handoff.

## What Haofan may safely do

- Reuse the frozen PDF/PNG figures in the PPT.
- Restyle a figure from the included compact tables, while retaining the same
  values, labels and claim boundary.
- Convert conceptual diagrams into PowerPoint-native shapes without changing
  their scientific meaning.
- Ask Wennie for a particular raw field archive if a genuine re-analysis is
  needed.

## What this package does not authorize

- Do not rerun PIDL training on a laptop or silently substitute a newer run.
- Do not describe the historical FEM and PIDL event cycles as exact agreement.
- Do not relabel historical eight-step/Five-step field plots as the canonical
  Hard-5 benchmark.
- Do not treat a generated figure, table, or matching scalar `N_f` as proof of
  solver equivalence or experimental validation.

## Current event wording for the PPT

For `Umax=0.12`, the current reporting contract distinguishes:

- canonical Hard-5 FEM: first detect `c83`, confirmation `c86`;
- historical eight-step FEM: first detect `c86`, confirmation `c89`;
- PIDL: first detect at step 444 (`c89` peak), confirmation at step 447
  (`c90`, within-cycle substep 2).

The report's older numerical figures remain historical diagnostic evidence.
They were not recomputed under the later canonical contract.

## Environment

The historical PIDL dependency list is at
`code_snapshot/PIDL/requirements_parent.txt`. Plot-only work generally needs
Python, NumPy, pandas and Matplotlib. Training is not required for PPT work.

## Data policy

This Git branch includes compact analysis inputs and summaries needed to audit
the report. It excludes model checkpoints, full raw FEM `.mat` files, training
archives and projected full-field `.npz` arrays. Those assets are large,
machine-specific research archives rather than presentation inputs. Their
omission is explicit, not evidence that they never existed.

