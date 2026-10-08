# Research Index

**Status:** v2 documentation contract active for new or next-touched work  
**Adopted:** 2026-08-26  
**Migration:** migrate on touch; do not bulk-move or delete legacy evidence

This file is navigation, not a second scientific ledger. Current claims,
numbers, gates, and decisions belong to each Storyline and Experiment.

## Structure

```text
INDEX -> Storyline -> Experiment -> Run -> Evidence
```

- **Storyline:** one long-lived scientific question that spans experiments or
  preserves a claim-changing negative result.
- **Experiment:** one frozen scientific design. It has one primary Storyline.
- **Run:** one actual producer execution. Seeds, arms, retries, failed starts,
  and hardware reruns receive distinct Run IDs.
- **Evidence:** raw assets, analysis tables/figures, and the figure-set reading
  guide supporting the Experiment verdict.

Stable IDs do not include dates, machine names, model names, or verdicts:

```text
Storyline: S04
Experiment: S04-E007
Run: S04-E007-R001
```

## Storylines

Until a Storyline is migrated, its canonical detail remains in
[`../research_storylines.md`](../research_storylines.md) and its linked track
documents.

| ID | Storyline | Status | Current source |
|---|---|---|---|
| S01 | Real longitudinal road evidence | active | legacy `research_storylines.md` |
| S02 | Observation-conditioned road-fracture world model | active | legacy `research_storylines.md`; [S02-E001](S02/S02-E001/experiment.md); [S02-E002](S02/S02-E002/experiment.md) |
| S03 | Physics-to-reality observation bridge | paused | legacy `research_storylines.md` |
| S04 | PIDL/FEM mechanism closure | paused | legacy `research_storylines.md` |
| S05 | FEM teacher numerical and physical qualification | active | legacy `research_storylines.md` |
| S06 | LTPP 2-D spatial registration | paused | legacy `research_storylines.md` |
| S07 | LTPP current-map crack recognition | closed | legacy S07 (`killed` under its frozen protocol) |
| S08 | LTPP scalar/enriched/load forecasting | closed | legacy S08 (`killed` under its frozen protocol) |
| S09 | Synthetic FEM transition-surrogate qualification | active | `../experiments/at1_fatigue_mesh_pino_track.md`; [S09-E001](S09/S09-E001/experiment.md) (draft prototype; Pro design review and adopted revisions, no training) |

Storyline statuses are `active | paused | closed | merged`. Dependencies belong
in Storyline metadata (`depends_on`, `feeds`, `merged_into`), not in a separate
relationship document.

## Incubator

- **PINO physics-residual branch:** deferred. Promote only after residual
  computability, temporal-corpus qualification, and an independent frozen gate.
- Temporary ideas, bugs, one-off plotting changes, and agent tasks do not become
  Storylines or Experiments.

## Experiment Contract

Use [`../templates/research_experiment.md`](../templates/research_experiment.md).
An Experiment enters `ready` only after its protocol revision, validity checks,
smallest decisive primary gate, reuse decision, and code review are frozen.
Secondary diagnostics do not vote or rescue a failed primary gate. Post-result
gate relaxation cannot rescue the old verdict.

Experiment states are:

```text
draft -> ready -> running -> analysis -> closed
                              \-> quarantined
```

Run state has two independent dimensions:

```text
execution_status: prepared | running | succeeded | failed | cancelled | unknown
retrieval_status: pending | partial | verified
```

Scientific verdict belongs to the Experiment, not the Run:

```text
supports | mixed | negative | inconclusive | inadmissible
```

## Evidence And Figure Sets

Store heavy assets under:

```text
local_archive/experiments/<experiment_id>/
  runs/<run_id>/
  analysis/figures/
  analysis/tables/
  analysis/cache/
```

Every claim-bearing figure set requires one `README_analysis.md` using
[`../templates/research_analysis_readme.md`](../templates/research_analysis_readme.md).
It must guide the reading order, explain each figure's role, reconcile
cross-figure evidence, and state both allowed and blocked conclusions.
Standalone paper, submission, or handoff figures additionally require a
same-stem sidecar.

## Minimal Hash Policy

Do not hash ordinary figures, logs, CSVs, checkpoints, or every file in an
archive. Git-tracked content uses its commit identity. Ordinary runs use paths,
file counts/sizes, receipts, and retrieval verification.

Use a hash only for:

1. an external dataset or holdout whose frozen identity is necessary to
   interpret the experiment; or
2. one promoted evidence package when a result is genuinely breakthrough and
   will become a durable canonical reference.

One package hash is enough. Do not create a forest of per-file hashes.

## Legacy Transition

- Do not delete or bulk-move `research_frontier.md`,
  `research_storylines.md`, registries, existing track documents, or archives.
- Stop adding new duplicate state to `research_frontier.md`.
- Migrate only active, awaiting-analysis, claim-changing, or future-reused work
  when it is next touched.
- Preserve old paths and link them from the migrated Experiment or Storyline.
