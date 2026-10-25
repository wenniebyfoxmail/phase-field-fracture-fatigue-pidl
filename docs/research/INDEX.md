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

Until a Storyline is migrated, its canonical detail remains in the legacy
`docs/research_storylines.md` and linked track documents. This governance
commit records their locator only; it does not bulk-copy legacy scientific
records from the mixed checkout.

| ID | Storyline | Status | Current source |
|---|---|---|---|
| S01 | Real longitudinal road evidence | active | legacy `research_storylines.md` |
| S02 | Observation-conditioned road-fracture world model | active | legacy `research_storylines.md`; `S02/S02-E001/experiment.md`; `S02/S02-E002/experiment.md` |
| S03 | Physics-to-reality observation bridge | paused | legacy `research_storylines.md` |
| S04 | PIDL/FEM mechanism closure | paused | legacy `research_storylines.md` |
| S05 | FEM teacher numerical and physical qualification | active | legacy `research_storylines.md` |
| S06 | LTPP 2-D spatial registration | paused | legacy `research_storylines.md` |
| S07 | LTPP current-map crack recognition | closed | legacy S07 (`killed` under its frozen protocol) |
| S08 | LTPP scalar/enriched/load forecasting | closed | legacy S08 (`killed` under its frozen protocol) |
| S09 | Synthetic FEM transition-surrogate qualification | active | `docs/experiments/at1_fatigue_mesh_pino_track.md`; `S09/S09-E001/experiment.md` (draft prototype; Pro design review and adopted revisions, no training) |

Storyline statuses are `active | paused | closed | merged`. Dependencies belong
in Storyline metadata (`depends_on`, `feeds`, `merged_into`), not in a separate
relationship document.

## Active implementation owners

This is a live operational map, not a second scientific ledger. A Storyline
being `active` or `paused` does not imply that it has an active writer. Rows
appear only while an owner is active or a checkout/branch prevents safe archive;
history omitted from this table is `historical` by default. Base SHAs are the
verified merge-base with `origin/main` for this 2026-10-25 audit.
Worktree paths are relative to the repository root (`.`); `../` paths are
sibling worktrees outside that checkout.

| Owner / Experiment | Branch | Worktree | Base SHA | In-scope paths | Status |
|---|---|---|---|---|---|
| Shared integration and recovery | `codex/m2s-framework-validation` | `.` | `5c9c0e561f8b` | governance, skills, handovers, untracked docs/assets | needs-resolution — dirty; ahead of upstream; quarantined and not a new-task base |
| S04-E016 Request28 storage block | `codex/s04-e016-request31-storage-block-20261009` | `.codex/worktrees/s04-e016-request31-storage-block-20261009` | `5c9c0e561f8b` | S04 documents and `local_archive/` | needs-resolution — unique untracked docs/raw archive need ownership check |
| S04-E017 D1 diagnostic | `codex/s04-e017-d1-diagnostic-20261015` | `.codex/worktrees/s04-e017-d1-diagnostic-20261015` | `5c9c0e561f8b` | `local_archive/` | needs-resolution — local-only HEAD and archive ownership unresolved |
| S04-E018 runtime snapshot | detached `c883bfd8` | `.codex/worktrees/s04-e018-runtime-c883bfd` | `5c9c0e561f8b` | `local_archive/` | needs-resolution — detached HEAD and archive ownership unresolved |
| S04-E021 physical raw | `codex/s04-e021-physical-raw-20261015` | `.codex/worktrees/s04-e021-physical-raw-20261015` | `5c9c0e561f8b` | `local_archive/` | needs-resolution — local-only HEAD and archive ownership unresolved |
| S04 frozen replay preparation | `codex/s04-raw-replay-preparation-20261015` | `.codex/worktrees/s04-raw-replay-preparation-20261015` | `5c9c0e561f8b` | `local_archive/` | needs-resolution — local-only HEAD and archive ownership unresolved |
| S09-E007 fixed-damage holdout | `codex/s09-e007-fixed-damage-holdout-20261012` | `.codex/worktrees/s09-e007-fixed-damage-holdout-20261012` | `5c9c0e561f8b` | `local_archive/` | needs-resolution — upstream-ahead branch requires push or explicit archive record |
| f(p) learnability | `worktree-exp+f-shape-p-learnable` | `.claude/worktrees/exp+f-shape-p-learnable` | `e162acd4e7d3` | `SENS_tensile/config.py`, `source/fatigue_history.py`, `source/model_train.py` | needs-resolution — dirty shared-core changes; do not integrate beside another core owner |
| Tip-local net | `codex/exp/tip-local-net` | `.claude/worktrees/exp/tip-local-net` | `8134163dc597` | config, SENS runners, `source/model_train.py`, frontier note | needs-resolution — dirty shared-core/runner changes |
| Hard crack-tip enrichment | `claude/hard-crack-tip-enrichment` | `.claude/worktrees/hard-crack-tip-enrichment` | `b2d843253710` | untracked branch/report documents | needs-resolution — unique handoff status unknown |
| Local-patch domain decomposition | `worktree-local-patch-domain-decomp` | `.claude/worktrees/local-patch-domain-decomp` | `b2d843253710` | untracked executive summary | needs-resolution — summary may be the only handoff |
| Local spectral tip patch | `claude/local-spectral-tip-patch` | `.claude/worktrees/local-spectral-tip-patch` | `b2d843253710` | untracked branch document | needs-resolution — archive/owner unknown |
| PIDL state-timing diagnostic | `codex/pidl-state-timing-diagnostic` | `.codex/worktrees/pidl-state-timing-diagnostic` | `5c9c0e561f8b` | result-check protocol | needs-resolution — dirty and upstream-behind |
| S04 cyclic alignment | `codex/s04-cyclic-alignment-20261021` | `../worktrees/s04-cyclic-alignment-20261021` | `5c9c0e561f8b` | S04-E036 tools, tests, MATLAB and PowerShell | needs-resolution — substantial local-only implementation |
| S04-E039 RPROP state | `codex/s04-e039-rprop-state-20261022` | `../worktrees/s04-e039-rprop-state-20261022` | `9c9c30fda38b` | `local_archive/` | needs-resolution — raw archive and current writer status unconfirmed |
| PIDL core package boundary | `codex/pidl-core-boundary-20261025` | branch-only alias | `5c9c0e561f8b` | reusable package boundary and compatibility bridges | needs-resolution — local-only branch currently shares the mixed integration HEAD |
| Repository governance | `codex/infra-repository-governance-20261025` | `../worktrees/repository-governance-20261025` | `389f618b7a04` | INDEX, worktree protocol, `.gitignore` | active — isolated governance scope and clean integration entry |

Every `needs-resolution` row is retained. A clean status alone never promotes a
row to removable: it must also satisfy the archive protocol's recoverability,
owner-closure, raw-asset and no-writer conditions.

## Incubator

- **PINO physics-residual branch:** deferred. Promote only after residual
  computability, temporal-corpus qualification, and an independent frozen gate.
- Temporary ideas, bugs, one-off plotting changes, and agent tasks do not become
  Storylines or Experiments.

## Experiment Contract

Create one `experiment.md` in the Experiment folder. An Experiment enters
`ready` only after its protocol revision, validity checks,
smallest decisive primary gate, reuse decision, and fixed task benchmark are
frozen. Code review is added only when explicitly requested.
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

Use one `README_analysis.md` only for a frozen protocol that explicitly requires
it or a standalone claim-bearing figure set.
It guides the reading order, explains each figure's role, reconciles
cross-figure evidence, and states allowed and blocked conclusions. Ordinary
result snapshots instead retain a source pointer and short interpretation.
Standalone paper, submission, or handoff figures additionally require a
same-stem sidecar.

### Legacy tracked PNGs — preservation status

The 2026-10-25 audit found 15 legacy PNGs tracked under
`SENS_tensile/figfiles/` in the quarantined
`codex/m2s-framework-validation` checkout. This governance branch does not
move, delete, or untrack them. Their paper/canonical status is not yet
established, so they remain `needs-resolution` rather than silently promoted
or discarded.

- The 11 files under `pidl_fem/`, `sn_full/`, and `summary/` have named
  generators and are retained as reproducible historical comparison figures.
- `Kt_baseline_vs_williams_comparison.png`, `degradation_FEM_vs_PIDL.png`,
  `degradation_comparison.png`, and `paradox_mechanism.png` lack a confirmed
  current owner and are the first figure assets needing classification.

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
