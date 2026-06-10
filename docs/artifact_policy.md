# Artifact Policy

This repository should stay useful as a shared code and research-control repo.
It should not become the storage location for full training archives or FEM
handoff packages.

## Keep In Git

Commit files that another machine or future session needs in order to reproduce
or understand the work:

- Source code under `source/`.
- Runner, diagnostic, plotting, and analysis scripts under `SENS_tensile/`.
- Workflow rules, protocols, handovers, and result summaries under `docs/`.
- Small canonical CSV/JSON/Markdown tables when they are the reviewed summary,
  not raw exported state.
- Selected figures when they are directly referenced by a result-summary doc and
  are small enough for normal Git review.
- Templates and lightweight manifests that explain where larger artifacts live.

## Keep Out Of Git

Do not commit generated artifacts that are large, machine-local, or replaceable:

- Training archives named `hl_*/`.
- Model checkpoints and arrays: `*.pt`, `*.npy`, `*.npz`.
- FEM or MATLAB field dumps: large `*.mat` packages.
- TensorBoard event files and run logs.
- Full Taobo project snapshots or copied remote trees.
- OneDrive/Downloads handoff packages.
- Local result roots such as `result/`, `experiment/`, and `fem_result/`.
- Local-only references, private PDFs, temporary analysis folders, and tool
  worktrees.

If a generated artifact is needed for traceability, record its path, producer,
commit SHA, and short description in `docs/artifact_index.md` or the relevant
handover file instead of committing the payload.

## Canonical Summary Pattern

For each important result package, prefer this shape:

```text
docs/<result_summary>.md          # interpretation and key metrics
docs/figures/<small_summary>.png  # optional selected review figure
docs/artifact_index.md            # location of raw data and full package
```

For protocol-style experiments, keep the folder lightweight:

```text
_analysis_*/experiments/<run_id>/
  1_analysis/result_check.md
  2_figures/<small_summary>.csv
```

Raw sync folders, state dumps, checkpoints, TensorBoard logs, and full field
exports should stay local or remote.

## Promotion Checklist

Before adding any artifact to Git, ask:

1. Is this needed by another machine to run the code or understand a reviewed
   result?
2. Is it small enough for normal diff/review?
3. Is it a summary rather than a raw payload?
4. Can it be regenerated from a documented raw package?
5. Is the source path or remote archive path recorded somewhere durable?

If the answer is uncertain, keep the artifact out of Git and add a manifest or
index entry instead.

## Current Local Roots

The following top-level roots are local artifact/package areas and are ignored
by Git:

- `result/`
- `experiment/`
- `fem_result/`

They may remain on disk for local analysis.  Important contents should be
summarised in `docs/` and indexed in `docs/artifact_index.md`.
