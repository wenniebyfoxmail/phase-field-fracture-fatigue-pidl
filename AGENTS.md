# Agent Rules for `upload code/`

This file is the cross-agent entry point for the shared GitHub repo. It applies to Codex, Claude, and any other agent working from this repository.

## Non-Negotiable Machine Roles

- **Mac-PIDL is Dev only.** Edit code, docs, runners, and analysis here. Run only lightweight import/unit sanity on Mac.
- **Do not run PIDL training on Mac.** Any command that enters the training loop, even a 1-cycle smoke, must run on Taobo GPU, CSD3, or Windows-PIDL after checking compute availability.
- **Taobo GPU / CSD3 / Windows-PIDL are Producers.** They run training smoke, baselines, sweeps, and production jobs from code prepared by Mac.
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

## Research Figure Documentation

- Every newly generated research figure (`.png`, `.pdf`, `.svg`, `.jpg`, or
  `.jpeg`) must have a same-stem `.md` sidecar in the same directory. Multiple
  render formats of the same figure may share that one sidecar.
- The sidecar must explain the figure question, exact data provenance, how to
  read axes/colours/lines, every panel, the main numerical takeaway, limitations,
  and the claim boundary. Use `docs/templates/research_figure_sidecar.md`.
- Prefer generating the sidecar from the plotting script so values cannot drift
  from the rendered figure. Before handoff, run
  `python source/validate_figure_sidecars.py <figure-directory>`.

## Research Track Documentation

- Every research track must have one stable canonical document under
  `docs/experiments/`, normally `<track>_track.md`. It owns the full mechanism
  question, claim boundary, experiment states, evidence links, active gate, and
  next action.
- Every claim-changing experiment within that track must have its own dated
  preregistration/decision document and, when applicable, attempt ledger. Do
  not use `docs/research_frontier.md` as the experiment record.
- Update order is mandatory: first update the track/experiment document and its
  receipts; only then update `docs/research_frontier.md` with a concise status
  and link to the canonical track document.
- Keep raw/generated payloads in `local_archive/` or an external producer
  store. Git tracks compact summaries, manifests, hashes, code, and decision
  notes.
- A frontier entry should state only current status, claim boundary, and next
  discriminator. Detailed history, tables, commands, and alternative designs
  belong in the canonical track document.

## Where Details Live

- `CLAUDE.md` — project session protocol and red lines.
- `docs/git_workflow.md` — Mac/Windows/Taobo producer split.
- `docs/taobo_gpu_submission_protocol.md` — exact Taobo submission, sync, launch, and tracking checklist.
- `docs/research_frontier.md` — current research frontier.
- `docs/handovers/` — cross-machine task inbox/outbox.

## Project-Local Skills

- `docs/skills/pidl-experiment-gate/SKILL.md` — use before proposing,
  launching, reviewing, cleaning, or registering any PIDL/FEM/surrogate
  experiment. It enforces the five-question experiment gate and prevents orphan
  runs.
- `docs/skills/project_skill_inventory_2026-07-06.md` — current map from
  project skills/workflows to code entrypoints and producer machines.
- `docs/skills/paper-ledger-to-paper/SKILL.md` — use for evolving mechanism
  result sections before compressing them into paper prose.
- `docs/aligned_result_registry_2026-07-06.md` — daily curated evidence
  registry after strict-setting cleanup; use the large
  `docs/pidl_experiment_inventory.md` only as the full audit ledger.
