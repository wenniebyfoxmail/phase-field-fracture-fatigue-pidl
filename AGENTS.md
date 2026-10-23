# Agent Rules for `upload code/`

## Third-Party Email And Form Approval

- Only emails sent to third parties and forms filled in or submitted to third
  parties require the user's explicit approval of the final account,
  recipient/object, full body/fields, attachments and commitments.
- A change to any of those details requires fresh approval. Verify the actual
  state after sending or submission; investigate an unknown result before
  retrying.
- Submitting research designs, code or evidence to ChatGPT Pro for review is
  not a third-party email or form submission. It may proceed directly, followed
  by verification of the returned review.
- Local work, SSH operations, code and document handling, ordinary tool calls
  and other work that is neither email nor form submission do not trigger this
  approval rule.
- Before approval, third-party emails and forms must still be checked for the
  author's style, audience-appropriate wording, attachments and visible
  metadata, with unnecessary internal notes and templated AI phrasing removed.

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
- Code delivery reports task branch, source commit and actual push status/link.
  Local commit is not GitHub publication; a pushed task branch need not be merged
  into main. Preserve completed source on its task branch without changing an
  active producer's pinned checkout or adding another pre-push test/review round.
- Before removing a worktree, verify that its branch is pushed or otherwise
  recoverably archived, record the exact HEAD, and require a clean status.
- Follow `docs/task_worktree_archive_protocol.md` for task naming, commit units,
  producer handoff, integration, and archive rules.

## Research Result Snapshots

The installed `research-decision-core` owns the research workflow and visual
interpretation. This entry keeps only the cross-machine result policy.

- At a route decision or interpretable computed/measured result, make one fast
  decision visual from already evaluated or retrieved output. It adds no new
  computation, review, or full analysis package. Copy the rendered PNG to
  `attachments/<storyline>/<date>/`, embed it below the result in the existing
  Obsidian task note, and add a short source/Run caption plus a plain-language
  `See` and `Therefore` interpretation. Keep raw output in the repository or
  producer archive.
- A second visual is useful only when it answers another necessary decision.
  Pure documentation/configuration work or an uninterpretable output does not
  require a figure.
- A complete figure set, CSV package, `README_analysis.md`, or standalone
  sidecar is required only for strict-alignment evidence, a claim-bearing
  result, citation/submission/handoff/independent reading, or an explicit user
  request. Daily or exploratory snapshots may stop at the visual, concise note,
  compact Run receipt, and raw-output pointer.
- When a figure is made, inspect it for blank panels, wrong state mapping,
  flipped coordinates, misleading colour limits, and unreadable labels. This
  check must not create a new computation or review round.

## Research Track Documentation

- The core owns local reuse, the Decision Ladder, first-principles route design,
  stage-appropriate criteria, progress summaries, and concise Obsidian
  milestones. Run that shared workflow once; domain adapters add only
  claim-specific scientific semantics.
- Formal, claim-bearing work uses `Storyline -> Experiment -> Run -> Evidence`
  under `docs/research/INDEX.md`. It keeps a frozen protocol revision and a
  dated amendment for changed hypotheses, data boundaries, comparators, primary
  criteria, or gates. Diagnostic exploration may use a task note without being
  relabelled as confirmation.
- Every actual producer execution has a fresh Run ID and compact receipt:
  producer, code identity, command/config, output/log/archive locations,
  retrieval route, and start/terminal status. Git tracks source, small receipts
  and evidence pointers; raw payloads stay in a local archive or producer store.
- Legacy registries remain evidence, not mandatory entrypoints. Migrate an
  active record only when it is next touched.

## Research Updates And Obsidian

For substantive progress, follow the core's short `目的 / 本轮 / 结论` update.
At a chosen route or interpretable attempt result, append one 2–4 line
milestone to the existing Obsidian task note: result/decision, evidence pointer,
active D step, and next action. Update its single Roadmap link and embed the
fast result visual when one exists. Do not create one note per turn or copy a
chat transcript. Obsidian is the decision index; formal evidence records remain
the scientific source of truth.

## Research Modes And Boundaries

The core is the only generic research workflow. Select one mode in the existing
task record; the modes are alternatives, not a compulsory ladder.

- **Daily iteration:** implement, repair, or make an exploratory comparison
  within the current route. Run the fixed task benchmark and report actual
  engineering/research progress; it is not a new scientific claim by default.
- **Scientific validation:** answer the current research decision with the
  core's exploration or formal-test contract. A formal test freezes its claim,
  comparator, criterion, evidence, budget, and stop rule; formal status does
  not create a review by default.
- **Formal review:** answer a user-requested, submission-facing, or explicitly
  contracted review question. It reviews defined material and does not itself
  require a new run.

A changed commit, completed run, benchmark pass, or desire for more confidence
never upgrades a mode automatically. A result may recommend another mode, but
only the user or an already-authorised task contract may select it. Do not
relabel seen exploratory data as prospective confirmation.

Use one fixed task benchmark by default: pass -> deliver; fail -> repair and
rerun only the failed item; reuse unaffected passing evidence. Documentation,
wording, path, or metadata changes need only a direct consistency check. Do not
add full regression, history reruns, smoke ladders, stress tests, ablations, or
independent review unless the user explicitly asks. The core's bounded-task
authority covers mechanical checks within the approved envelope; it never
changes scientific, data, budget, producer, or stop/retry boundaries.

Estimate GPU cost as GPU count times wall-clock hours. A planned single run of
at least 8 GPU-hours needs a brief capacity/storage/budget check; at least 24
GPU-hours cumulative for one exploratory question needs a direction check before
further runs. Neither is an extra scientific review. Shared-GPU conflicts,
insufficient storage, or protected data retain their own checks regardless of
GPU-hours.

## Where Details Live

- `CLAUDE.md` — project session protocol and red lines.
- `docs/git_workflow.md` — Mac/Windows/Taobo producer split.
- `docs/task_worktree_archive_protocol.md` — mandatory task/worktree/commit/archive lifecycle.
- `docs/taobo_gpu_submission_protocol.md` — exact Taobo submission, sync, launch, and tracking checklist.
- `docs/research/INDEX.md` — current research Storylines and the v2 documentation contract.
- `docs/research_frontier.md` and `docs/research_storylines.md` — legacy/read-only research maps during migrate-on-touch transition.
- `docs/handovers/` — cross-machine task inbox/outbox.

## Project-Local Skills

- **Research workflow in any field:** read
  `docs/skills/research-decision-core/SKILL.md` when choosing or advancing a
  research route. It owns local reuse, the Decision Ladder, stage-appropriate
  criteria, visual explanations, progress summaries and milestone records.
  Add only the domain requirements below; run the shared workflow once.
- **Deep Research and paper archival:** at topic intake or a bottleneck that
  needs external evidence, use `docs/skills/deep-research-obsidian/SKILL.md`.
  Archive the report and supporting papers in Obsidian and link the next D step.
  HQs include these current skill paths and the active D step in executor briefs.
- **Independent review routing:** only for a user-requested
  design, Code Ready, or evidence review, read
  `docs/skills/research-review-channels/SKILL.md`. Present the channel choices
  to the user before dispatch unless the user has already chosen and authorized
  the material. A transport failure is not permission to switch channels.
- **Mandatory experiment routing:** before choosing exploratory versus formal
  work, or proposing, launching, reviewing, or interpreting a road-fracture
  research Run or Experiment, read
  `docs/skills/road-fracture-experiment-gate/SKILL.md` and only the adapter(s)
  relevant to the target claim. For PIDL/FEM, teacher, residual, GNO/PINO, or
  Hard-5-specific work, also read
  `docs/skills/pidl-experiment-gate/SKILL.md`. Literature-only review and routine
  non-claim-changing edits do not invoke the experiment gate.
- `docs/skills/road-fracture-experiment-gate/SKILL.md` — project-wide gate for
  road-fracture observation, measurement/inverse, prediction, decision, and
  physics/surrogate domain requirements on top of the shared research core.
- `docs/skills/research-review-channels/SKILL.md` — select a capable independent
  design, code, or evidence reviewer without changing the scientific gate.
- `docs/skills/pidl-experiment-gate/SKILL.md` — compatibility entry for
  PIDL/FEM, teacher, residual, neural-operator, and Hard-5-specific semantics;
  it delegates the common decision contract to the road-fracture gate.
- `docs/skills/research-figure-workflow/SKILL.md` — planning, visual QA,
  captions, and the compact user-facing interpretation of research figures.
- `docs/skills/pidl-run-analysis-workflow/SKILL.md` — strict-alignment or
  explicitly requested full PIDL/FEM evidence packages. Ordinary PIDL runs use
  the core, relevant domain adapter, producer protocol, compact Run receipt,
  and fast result snapshot instead.
- `docs/skills/project_skill_inventory_2026-07-06.md` — current map from
  project skills/workflows to code entrypoints and producer machines.
- `docs/skills/paper-ledger-to-paper/SKILL.md` — use for evolving mechanism
  result sections before compressing them into paper prose.
- `docs/aligned_result_registry_2026-07-06.md` — daily curated evidence
  registry after strict-setting cleanup; use the large
  `docs/pidl_experiment_inventory.md` only as the full audit ledger.
