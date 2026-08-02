# Agent Rules for `upload code/`

This file is the cross-agent entry point for the shared GitHub repo. It applies to Codex, Claude, and any other agent working from this repository.

## Non-Negotiable Machine Roles

- **Mac-PIDL is Dev only.** Edit code, docs, runners, and analysis here. Run only lightweight import/unit sanity on Mac.
- **Do not run PIDL training on Mac.** Any command that enters the training loop, even a 1-cycle smoke, must run on Taobo GPU, CSD3, or Windows-PIDL after checking compute availability.
- **Taobo GPU / CSD3 / Windows-PIDL are Producers.** They run training smoke, baselines, sweeps, and production jobs from code prepared by Mac.
- **GitHub is the shared source of code truth.** Commit code/rule/runner/doc changes on Mac and push when cross-machine sync is needed. Do not rely on a Taobo-local commit as shared state.

## Taobo GPU Submission

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
- Before telling another machine to use a Git path, case id, runner, or registry
  row, fetch the named remote and verify the object against the exact remote
  ref. Local working-tree or local-`HEAD` existence is not evidence of remote
  availability. Record the remote commit and required blob hash in the handoff;
  see the remote-visibility gate in `docs/git_workflow.md`.

## Where Details Live

- `CLAUDE.md` — project session protocol and red lines.
- `docs/git_workflow.md` — Mac/Windows/Taobo producer split.
- `docs/taobo_gpu_submission_protocol.md` — exact Taobo submission, sync, launch, and tracking checklist.
- `docs/research_frontier.md` — current research frontier.
- `docs/handovers/` — cross-machine task inbox/outbox.
