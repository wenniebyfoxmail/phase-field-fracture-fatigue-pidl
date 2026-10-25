# Repository operating policy

This is the shared Git repository for phase-field fracture with PIDL. This
file is the **sole repository policy** for Codex, Claude, and other agents.
`CLAUDE.md` is only a compatibility pointer.

## Start here

1. Read this file.
2. For research work, read the current HQ / Experiment owner card and its
   linked Obsidian note.
3. When a route or method must be chosen, read
   `research-decision-core/references/agent_bootstrap.md` and reason from
   **First Principles (第一性原理)**.
4. Read an operator runbook only when the task actually uses that machine,
   data boundary, or frozen package.

The research model is **HQ -> Experiment -> Run -> Evidence**. It has no
mandatory narrative layer, duplicate ledger, or default review loop.

## Ownership and execution

- One active task has one owner, one named branch, one clean worktree, and one
  fixed benchmark appropriate to its change.
- Use the current owner card as the source of scope and authority. When its
  scope, data, resource boundary, and contract are unchanged, execute routine
  work without asking for a new authority.
- Record a material method/configuration decision as M1 (config or commit), a
  computation as M2 (Run ID), and a conclusion as M3 (Evidence / concise
  Obsidian update). Do not create records that add no decision value.
- A concise Obsidian update is due after a chosen route/plan or a meaningful
  result changes the next step. Visual evidence belongs beside that result
  when the task produces it.

## Git and assets

- Git is the shared source of code, runnable configuration, and concise
  project rules. Generated outputs, raw data, PDFs, and large artefacts stay
  in their designated output/archive locations and are referenced by path,
  Run ID, and commit.
- Start new code work from a named clean worktree based on the intended remote
  ref. Never use a dirty shared checkout as the base for a new task.
- Preserve unrelated changes, historical worktrees, and recoverable commits.
  Do not force-push, reset hard, bulk-clean, bulk-delete, or move assets merely
  to make the tree look tidy.
- Commit a coherent task change after its direct check; push its task branch
  when cross-machine sharing or recovery needs it. A local commit is not a
  remote handoff until its push state is verified.
- A physical repository split is **deferred**. Reconsider it only after the
  candidate has a stable interface, independent test, defined input/output,
  owner and lifecycle, a rollback plan, and separate user approval. Until
  then, do not move code, outputs, or worktrees to manufacture a split.
  Repository-relative boundary tests alone do not establish an independently
  installed or released package contract.

## Machines

- **Mac-PIDL:** edit code/docs and run lightweight import or unit checks only;
  no training loop.
- **Taobo GPU, `gpu-server`, and authorised Windows producers:** run the
  approved GPU/FEM work from attributable remote directories. Record commit,
  Run ID, command, log/output path, device, and process identity.
- **CSD3:** CPU work only when explicitly named. It is never an implicit GPU
  or PIDL fallback.
- On shared machines, inspect command line, elapsed time, and working directory
  before touching a process. SSH loss is loss of visibility, not evidence that
  a detached run stopped.

## Verification and communication

- Run the current task's one fixed benchmark or direct consistency check.
  Documentation-only changes need `git diff --check` and direct link/path
  checks, not scientific computation or broad regression.
- Before a producer consumes Git-backed code, verify the exact remote ref and
  object named in its handoff. A file merely present in a local checkout is
  not remote availability.
- Global `~/.codex/AGENTS.md` governs external communication. `Haofan Pro` is
  an internal ChatGPT Pro review account for Codex's own local changes; it does
  not alter Wennie's research ownership, authorship, or sender identity.

## On-demand references

`docs/git_workflow.md` and `docs/workflow_rules.md` are operator/history
references. They do not replace this policy or a current owner card. Machine-
specific submission protocols remain binding only when their named producer is
being used.
