# Agent Rules for `upload code/`

This file is the cross-agent entry point for the shared GitHub repo. It applies to Codex, Claude, and any other agent working from this repository.

## Non-Negotiable Machine Roles

- **Mac-PIDL is Dev only.** Edit code, docs, runners, and analysis here. Run only lightweight import/unit sanity on Mac.
- **Do not run PIDL training on Mac.** Any command that enters the training loop, even a 1-cycle smoke, must run on the explicitly authorised producer after checking compute availability.
- **Current authorised producers are task-specific.** Taobo GPU and `gpu-server`
  (`D-26-09`) may run authorised GPU/PIDL/surrogate work. `citpc12-ssh`
  (`CITPC12`) is the directly controllable Windows-FEM/GRIPHFiTH producer.
  Both Windows aliases support public-key SSH from this Mac, so agents may
  launch, monitor, retrieve, and analyse in-scope work directly without a human
  relay. Do not use CSD3 or silently fall back to another machine unless the
  user explicitly authorises it for the named task.
- **GitHub is the shared source of code truth.** Commit code/rule/runner/doc changes on Mac and push when cross-machine sync is needed. Do not rely on a Taobo-local commit as shared state.

## Taobo GPU Submission

### Canonical Taobo storage path

When an agent says “Taobo `/mnt/data`”, treat it as the large-data mount
family, not a literal directory. On the current Taobo host the canonical
primary mount is `/mnt/data2` (not `/mnt/data`); `/mnt/data3` is the secondary
large-disk/backup mount. New Wennie project runs and caches must use:

```text
/mnt/data2/drtao/wennie/<fresh_run_id>/
/mnt/data2/drtao/pidl_archives/<fresh_run_id>/
```

Never write large outputs, JIT caches, temporary compiler files, or archives
to `/`, `/tmp`, or `/home/drtao`. Put task-owned `TMPDIR`, `.jitcache`, and
`XDG_CACHE_HOME` under the fresh `/mnt/data2/drtao/wennie/<run_id>/` root.
Do not create or assume a literal `/mnt/data` symlink. Before launch, check
`df -h / /mnt/data2 /mnt/data3`; if `/mnt/data2` is unavailable, stop and
report rather than silently falling back to the root filesystem.

Before sending any job to Taobo, read:

- `docs/taobo_gpu_submission_protocol.md`
- `docs/git_workflow.md`
- Claude shared-account protocol, if available locally: `/Users/wenxiaofang/.claude/projects/-Users-wenxiaofang-phase-field-fracture-with-pidl-upload-code/memory/reference_drtao_shared_account_protocol.md`

Required Taobo principles:

- Use fresh, attributable remote run directories, preferably under `/mnt/data2/drtao/wennie/`.
- Never write large outputs to `/` or home. Set `PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/...` or another `/mnt/data2/drtao/...` output root.
- Always launch Python GPU jobs with `CUDA_VISIBLE_DEVICES=N`.
- Always record commit SHA, remote run dir, GPU id, PID, command, log path, archive path, and dirty status.
- Use detached execution (`nohup`, `setsid`, or `tmux pf_*`) so SSH/VPN drops do not stop jobs.
- Treat SSH drops as loss of visibility, not proof that the job stopped.

## Shared `drtao` Account Safety

Taobo user `drtao` is shared by Wennie and Haofan. Process ownership cannot be inferred from username alone.

- Never run `pkill python3` or `pkill -u drtao`.
- Before killing any PID, verify all three: `cmdline`, elapsed time, and cwd.
- Do not attach to tmux sessions you did not create; inspect with `tmux capture-pane -p -t <session>`.
- Reboot, global sudo config edits, root-service/docker changes, and heavy disk IO require coordination with the other human users / Tao哥 first.

## Git And Working Tree Hygiene

- Do not force-push, reset hard, rebase interactive, or amend pushed commits unless explicitly authorized.
- Do not overwrite existing shared log/handover entries. Append or add update subsections.
- The parent repo is local scratch. The child repo `upload code/` is the GitHub-synced project.
- If the working tree is dirty, preserve unrelated changes. Do not revert files you did not intentionally modify.
- The shared checkout is an integration and recovery surface, not a development
  workspace. New tasks must use a dedicated branch and clean worktree. Reuse an
  existing matching worktree when one exists; otherwise branch from an explicit
  remote commit. Never branch from an uncommitted mixed checkout.
- One task has one primary owner: a Storyline/Experiment for claim-changing
  research, or one named infrastructure/writing scope. Do not mix unrelated
  owners in one commit or worktree.
- Stage explicit paths only. Do not use `git add -A` or `git add .` from a mixed
  checkout.
- Before removing a worktree, verify that its branch is pushed or otherwise
  recoverably archived, record the exact HEAD, and require a clean status.
- Follow `docs/task_worktree_archive_protocol.md` for task naming, commit units,
  producer handoff, integration, and archive rules.

## Research Figure Documentation

- Every claim-bearing figure set must have one `README_analysis.md` that states
  the scientific question, evidence source, intended reading order, what each
  figure shows, the cross-figure interpretation, the allowed conclusion, the
  blocked conclusion, and the storyline impact. Use
  `docs/templates/research_analysis_readme.md`.
- A same-stem `.md` sidecar is required only when a figure will be cited,
  submitted, handed off, or read independently of its figure set. Multiple
  render formats of the same figure may share that sidecar. Intermediate
  diagnostic figures may be covered by the figure-set `README_analysis.md`.
- Prefer generating tables and provenance fields from the analysis script so
  values cannot drift. Inspect rendered figures for blank panels, wrong state
  mapping, flipped coordinates, misleading colour limits, and unreadable labels.

## Research Track Documentation

- New and actively touched research uses the four-level structure defined in
  `docs/research/INDEX.md`: `Storyline -> Experiment -> Run -> Evidence`.
- Each claim-changing Experiment must have one primary Storyline, an immutable
  ID, a folder, a frozen protocol revision, and one `experiment.md`. A change to
  the hypothesis, data semantics, holdout, comparator, primary metric, threshold,
  or gate requires a dated amendment and renewed review; do not rewrite a used
  protocol silently.
- Each actual producer execution has a fresh Run ID and a compact tracked run
  receipt. Seeds, arms, retries, failed launches, and hardware reruns are Runs;
  a changed scientific design is a new Experiment.
- Raw data, checkpoints, logs, and generated payloads live under
  `local_archive/experiments/<experiment_id>/` or an external producer store.
  Git tracks code, experiment records, compact receipts, small claim-critical
  evidence, and pointers to raw assets.
- `docs/research_frontier.md`, `docs/research_storylines.md`, existing track
  documents, and registries are legacy evidence. Do not bulk-move, rewrite, or
  delete them. Migrate an active item only when it is next touched.

## Research Readiness Gates

- **Code Ready:** before claim-changing code is used, search the repository for
  reusable runners, parsers, plotters, validators, and tests; run relevant local
  sanity tests; then obtain a read-only independent code review bound to the
  exact commit, runner, config, data lock, and protocol revision. Any material
  change invalidates the prior PASS.
- **Run Ready:** every producer execution uses a fresh Run ID and records the
  producer alias/hostname, commit or immutable snapshot, dirty status, command,
  runtime, GPU or scheduler identity, PID/session/job, output/archive/log paths,
  retrieval route, and start time. Starting successfully is execution evidence,
  not scientific evidence.
- **Evidence Ready:** an Experiment closes only after retrieval status is
  explicit, its predeclared minimum evidence exists, an independent evidence
  review is complete when required, the scientific verdict is separated from
  execution status, and the Storyline receives one dated claim-impact entry.
  Require `README_analysis.md` only when a claim-bearing figure set exists.
- **Gate design:** include only validity failures that make the result
  uninterpretable. Use one smallest decisive primary criterion for the target
  claim; a conjunction is allowed only when each clause is independently
  necessary. Secondary diagnostics explain but never vote, rescue a failure, or
  overturn a pass. Thresholds need an ex-ante physical/decision, uncertainty,
  or meaningful-baseline rationale. A gate may be revised before results with a
  reviewed amendment. After results are seen, preserve the old verdict and use
  a new revision or Experiment.
- **Hashing:** hashes are not routine paperwork. Git-tracked content uses its
  commit identity. Ordinary runs use paths, receipts, file counts/sizes, and
  retrieval verification. Freeze one hash only when an external dataset/holdout
  needs an identity lock or when a genuinely breakthrough result is promoted to
  a durable canonical evidence package.

## Where Details Live

- `CLAUDE.md` — project session protocol and red lines.
- `docs/git_workflow.md` — Mac/Windows/Taobo producer split.
- `docs/task_worktree_archive_protocol.md` — mandatory task/worktree/commit/archive lifecycle.
- `docs/taobo_gpu_submission_protocol.md` — exact Taobo submission, sync, launch, and tracking checklist.
- `docs/research/INDEX.md` — current research Storylines and the v2 documentation contract.
- `docs/research_frontier.md` and `docs/research_storylines.md` — legacy/read-only research maps during migrate-on-touch transition.
- `docs/handovers/` — cross-machine task inbox/outbox.

## Project-Local Skills

- **Mandatory experiment routing:** before proposing, launching, reviewing, or
  interpreting any claim-changing road-fracture Experiment, read
  `docs/skills/road-fracture-experiment-gate/SKILL.md` and only the adapter(s)
  relevant to the target claim. For PIDL/FEM, teacher, residual, GNO/PINO, or
  Hard-5-specific work, also read
  `docs/skills/pidl-experiment-gate/SKILL.md`. Literature-only review and routine
  non-claim-changing edits do not invoke the experiment gate.
- `docs/skills/road-fracture-experiment-gate/SKILL.md` — project-wide gate for
  claim-changing observation, measurement/inverse, prediction, decision, and
  physics/surrogate experiments. Route by claim rather than model family.
- `docs/skills/pidl-experiment-gate/SKILL.md` — compatibility entry for
  PIDL/FEM, teacher, residual, neural-operator, and Hard-5-specific semantics;
  it delegates the common decision contract to the road-fracture gate.
- `docs/skills/project_skill_inventory_2026-07-06.md` — current map from
  project skills/workflows to code entrypoints and producer machines.
- `docs/skills/paper-ledger-to-paper/SKILL.md` — use for evolving mechanism
  result sections before compressing them into paper prose.
- `docs/aligned_result_registry_2026-07-06.md` — daily curated evidence
  registry after strict-setting cleanup; use the large
  `docs/pidl_experiment_inventory.md` only as the full audit ledger.
